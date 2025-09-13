import discord
from typing import TYPE_CHECKING
from config import Strings
from services.logging_utils import get_logger
from services import survey_manager
from services.survey import SurveyFlow
from discord.ext import commands  # Import commands for bot type hint

if TYPE_CHECKING:  # only for type checking, avoids runtime import in tests
    from services.webhook import WebhookService

# ==================================
# Survey-Specific Modals
# ==================================

class ConnectsModal(discord.ui.Modal):
    """Modal specifically for handling the 'connects' step in the survey."""
    def __init__(
        self,
        survey: SurveyFlow,
        step_name: str,
        finish_survey_func, # Function to call to finish the survey
        webhook_service_instance: 'WebhookService', # Webhook service instance
        bot_instance: commands.Bot # Bot instance
    ):
        """Initializes the ConnectsModal with necessary dependencies."""
        try:
            self.log = get_logger(
                "view.connects_modal",
                {"userId": str(survey.user_id), "channelId": str(survey.channel_id), "sessionId": str(getattr(survey, 'session_id', ''))},
            )
            self.log.info("init")

            # Verify required survey properties
            if not survey.user_id or not survey.channel_id:
                raise ValueError("Survey missing required properties")

            # Initialize modal with title
            title = Strings.CONNECTS_MODAL
            super().__init__(title=title, timeout=300)
            # logger.debug("Modal base initialized")

            # Store survey data and dependencies
            self.survey = survey
            self.step_name = step_name
            self.finish_survey_func = finish_survey_func
            self.webhook_service_instance = webhook_service_instance
            self.bot_instance = bot_instance

            # Create and configure text input
            # logger.debug("Creating TextInput field")
            self.connects_input = discord.ui.TextInput(
                label=Strings.CONNECTS_MODAL,
                placeholder=Strings.CONNECTS_PLACEHOLDER,
                min_length=1,
                max_length=3,
                required=True,
                style=discord.TextStyle.short
            )

            # Add input to modal
            self.add_item(self.connects_input)

        except Exception:
            get_logger("view.connects_modal").exception("init failed")
            raise

    async def on_submit(self, interaction: discord.Interaction):
        """Handles the modal submission for the connects step."""
        self.log.info("submit start")

        async def send_error_response(interaction: discord.Interaction, message: str):
            """Helper to send error response"""
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(message, ephemeral=True)
                else:
                    await interaction.followup.send(message, ephemeral=True)
            except Exception:
                self.log.exception("failed to send error message")

        try:
            user_input = self.connects_input.value.strip()

            # Validate input is a number and in reasonable range
            if not user_input.isdigit():
                self.log.warning("invalid input: non-digit")
                await send_error_response(interaction, Strings.NUMBER_REQUIRED)
                return

            connects = int(user_input)
            if connects < 0 or connects > 999:
                self.log.warning("invalid range")
                await send_error_response(interaction, "{Strings.NUMBER_REQUIRED}. Кількість коннектів має бути від 0 до 999")
                return

            # Retrieve the survey using channel_id
            current_survey = survey_manager.get_survey(str(interaction.channel.id))
            if not current_survey or current_survey.session_id != self.survey.session_id:
                self.log.warning("survey not found or session mismatch")
                await send_error_response(interaction, Strings.GENERAL_ERROR)
                return

            # Verify user and channel
            if str(interaction.user.id) != str(current_survey.user_id):
                self.log.warning("wrong user")
                await send_error_response(interaction, Strings.NOT_YOUR_SURVEY)
                return

            if str(interaction.channel.id) != str(current_survey.channel_id):
                self.log.warning("wrong channel")
                await send_error_response(interaction, Strings.WRONG_CHANNEL)
                return

            # Handle interaction response
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True) # Defer ephemeral for modal submit
                # logger.debug("Deferred modal response")


            self.log.info("store result")
            # Store the validated result
            try:
                current_survey.add_result(self.step_name, str(connects))
                # logger.debug(f"After add_result, survey.results: {{current_survey.results}}")
            except Exception:
                self.log.exception("store result failed")
                await send_error_response(interaction, Strings.GENERAL_ERROR)
                return

            self.log.info("store result duplicate")
            # Store the validated result
            try:
                current_survey.add_result(self.step_name, str(connects))
                # logger.debug(f"After add_result, survey.results: {{current_survey.results}}")
            except Exception:
                self.log.exception("store result duplicate failed")
                await send_error_response(interaction, Strings.GENERAL_ERROR)
                return

            # Send step webhook for just this step
            try:
                result_payload = {
                    "stepName": self.step_name,
                    "value": str(connects)
                }
                self.log.info("send step webhook")
                success, response = await self.webhook_service_instance.send_webhook( # Use passed instance
                    interaction, # Pass interaction directly
                    command="survey", # Use command="survey"
                    status="step", # Use status="step"
                    result=result_payload # Pass result_payload dictionary
                )
                self.log.info("step webhook done", extra={"success": success})
                # Show n8n output to user if present
                # Update command message with n8n output instead of deleting it
                if success and response and "output" in response:
                    if current_survey.current_message:
                        try:
                            self.log.debug("remove processing reaction")
                            await current_survey.current_message.remove_reaction("⏳", self.bot_instance.user) # Use passed instance
                            output_content = response.get("output", f"Дякую! Кількість коннектів {connects} записано.") # Default success message
                            self.log.debug("edit command message")
                            await current_survey.current_message.edit(content=output_content, view=None, attachments=[]) # Update content and remove view/attachments
                            self.log.info("updated command message")
                        except Exception:
                            self.log.exception("edit command message failed")
                elif not success:
                    self.log.error("step webhook failed")
                    if current_survey.current_message:
                        try:
                            await current_survey.current_message.remove_reaction("⏳", self.bot_instance.user) # Use passed instance
                            error_msg = Strings.CONNECTS_ERROR.format( # Assuming a CONNECTS_ERROR string exists
                                connects=connects,
                                error=Strings.GENERAL_ERROR
                            )
                            await current_survey.current_message.edit(content=error_msg)
                            await current_survey.current_message.add_reaction(Strings.ERROR)
                        except Exception:
                            self.log.exception("edit after webhook failure")

            except Exception:
                self.log.exception("send step webhook failed")
                await send_error_response(interaction, Strings.GENERAL_ERROR)
                return # Exit if step webhook fails

            # Continue/end/cancel based on n8n response via helper
            try:
                from discord_bot.commands.survey import process_survey_flag, finish_survey as _finish, continue_survey as _cont
                flag = (response or {}).get("survey")
                await process_survey_flag(
                    interaction.channel,
                    current_survey,
                    flag,
                    lambda ch, s: _cont(self.bot_instance, ch, s),
                    lambda ch, s: _finish(self.bot_instance, ch, s),
                )
            except Exception:
                self.log.exception("advance/continue failed")
                await send_error_response(interaction, Strings.GENERAL_ERROR)

        except Exception:
            self.log.exception("unexpected error on submit")
            try:
                await send_error_response(interaction, Strings.GENERAL_ERROR)
                # Clean up previous message even on error to prevent stuck buttons
                # await cleanup_survey_message(interaction, self.survey) # Cleanup logic is now handled by updating the message
            except Exception:
                self.log.exception("error during error cleanup")
