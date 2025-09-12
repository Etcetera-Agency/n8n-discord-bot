import discord
from typing import TYPE_CHECKING
from config import logger, Strings
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
            logger.info("Initializing ConnectsModal for channel {survey.channel_id} step {step_name}")

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
            logger.error("Error initializing ConnectsModal: {e}", exc_info=True)
            raise

    async def on_submit(self, interaction: discord.Interaction):
        """Handles the modal submission for the connects step."""
        logger.info("Starting ConnectsModal submission handling")

        async def send_error_response(interaction: discord.Interaction, message: str):
            """Helper to send error response"""
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(message, ephemeral=True)
                else:
                    await interaction.followup.send(message, ephemeral=True)
            except Exception:
                logger.error("Failed to send error message: {e}")

        try:
            user_input = self.connects_input.value.strip()

            # Validate input is a number and in reasonable range
            if not user_input.isdigit():
                logger.warning("Invalid connects input (non-digit): {user_input}")
                await send_error_response(interaction, Strings.NUMBER_REQUIRED)
                return

            connects = int(user_input)
            if connects < 0 or connects > 999:
                logger.warning("Invalid connects range: {connects}")
                await send_error_response(interaction, "{Strings.NUMBER_REQUIRED}. Кількість коннектів має бути від 0 до 999")
                return

            # Retrieve the survey using channel_id
            current_survey = survey_manager.get_survey(str(interaction.channel.id))
            if not current_survey or current_survey.session_id != self.survey.session_id:
                logger.warning("Survey not found or session mismatch for channel {interaction.channel.id} in ConnectsModal submit.")
                await send_error_response(interaction, Strings.GENERAL_ERROR)
                return

            # Verify user and channel
            if str(interaction.user.id) != str(current_survey.user_id):
                logger.warning("Wrong user for connects modal: {interaction.user.id} vs {current_survey.user_id}")
                await send_error_response(interaction, Strings.NOT_YOUR_SURVEY)
                return

            if str(interaction.channel.id) != str(current_survey.channel_id):
                logger.warning("Wrong channel for connects modal: {interaction.channel.id} vs {current_survey.channel_id}")
                await send_error_response(interaction, Strings.WRONG_CHANNEL)
                return

            # Handle interaction response
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True) # Defer ephemeral for modal submit
                # logger.debug("Deferred modal response")


            logger.info("Storing connects result: {connects} for channel {current_survey.channel_id}")
            # Store the validated result
            try:
                current_survey.add_result(self.step_name, str(connects))
                # logger.debug(f"After add_result, survey.results: {{current_survey.results}}")
            except Exception:
                logger.error("Error storing connects result for channel {current_survey.channel_id}: {e}")
                await send_error_response(interaction, Strings.GENERAL_ERROR)
                return

            logger.info("Storing connects result: {connects} for channel {current_survey.channel_id}")
            # Store the validated result
            try:
                current_survey.add_result(self.step_name, str(connects))
                # logger.debug(f"After add_result, survey.results: {{current_survey.results}}")
            except Exception:
                logger.error("Error storing connects result for channel {current_survey.channel_id}: {e}")
                await send_error_response(interaction, Strings.GENERAL_ERROR)
                return

            # Send step webhook for just this step
            try:
                result_payload = {
                    "stepName": self.step_name,
                    "value": str(connects)
                }
                logger.info("Sending survey step webhook for step: {self.step_name} with value: {connects}")
                success, response = await self.webhook_service_instance.send_webhook( # Use passed instance
                    interaction, # Pass interaction directly
                    command="survey", # Use command="survey"
                    status="step", # Use status="step"
                    result=result_payload # Pass result_payload dictionary
                )
                logger.info("Step webhook response for channel {current_survey.channel_id}: success={success}, response={response}")
                # Show n8n output to user if present
                # Update command message with n8n output instead of deleting it
                if success and response and "output" in response:
                    if current_survey.current_message:
                        try:
                            logger.debug("Attempting to remove processing reaction from command message {current_survey.current_message.id}")
                            await current_survey.current_message.remove_reaction("⏳", self.bot_instance.user) # Use passed instance
                            output_content = response.get("output", f"Дякую! Кількість коннектів {connects} записано.") # Default success message
                            logger.debug("Attempting to edit command message {current_survey.current_message.id} with output: {output_content}")
                            await current_survey.current_message.edit(content=output_content, view=None, attachments=[]) # Update content and remove view/attachments
                            logger.info("Updated command message {current_survey.current_message.id} with response")
                        except Exception:
                            logger.error("Error editing command message {getattr(current_survey.current_message, 'id', 'N/A')}: {edit_error}", exc_info=True)
                elif not success:
                    logger.error("Failed to send webhook for survey step: {self.step_name}")
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
                            logger.error("Error editing command message on webhook failure {getattr(current_survey.current_message, 'id', 'N/A')}: {edit_error}", exc_info=True)

            except Exception:
                logger.error("Error sending step webhook or handling response: {e}", exc_info=True)
                await send_error_response(interaction, Strings.GENERAL_ERROR)
                return # Exit if step webhook fails

            # Continue/end/cancel based on n8n response
            try:
                flag = (response or {}).get("survey")
                if flag == "continue":
                    current_survey.next_step()
                    from discord_bot.commands.survey import continue_survey as _cont
                    await _cont(self.bot_instance, interaction.channel, current_survey)
                elif flag == "end":
                    current_survey.next_step()
                    from discord_bot.commands.survey import finish_survey as _finish
                    await _finish(self.bot_instance, interaction.channel, current_survey)
                elif flag == "cancel":
                    from services import survey_manager as _mgr
                    _mgr.remove_survey(str(interaction.channel.id))
                else:
                    # Default behavior
                    current_survey.next_step()
                    from discord_bot.commands.survey import continue_survey as _cont
                    await _cont(self.bot_instance, interaction.channel, current_survey)
            except Exception:
                logger.error("Error advancing/continuing survey: {e}")
                await send_error_response(interaction, Strings.GENERAL_ERROR)

        except Exception:
            logger.error("Unexpected error in connects modal submission: {e}", exc_info=True)
            try:
                await send_error_response(interaction, Strings.GENERAL_ERROR)
                # Clean up previous message even on error to prevent stuck buttons
                # await cleanup_survey_message(interaction, self.survey) # Cleanup logic is now handled by updating the message
            except Exception:
                logger.error("Error during error cleanup: {cleanup_error}")
                logger.error("Error during error cleanup: {cleanup_error}")
