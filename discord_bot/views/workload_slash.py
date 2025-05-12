import discord
from typing import Optional
from config import logger, Strings, constants # Added Strings, constants
from services import webhook_service # Removed survey_manager

class WorkloadView_slash(discord.ui.View):
    """View for workload selection - only used for non-survey commands"""
    def __init__(self, cmd_or_step: str, user_id: str): # Removed has_survey parameter
        logger.debug(f"[{user_id}] - WorkloadView_slash.__init__ called for cmd_or_step: {cmd_or_step}") # Removed has_survey from log
        super().__init__(timeout=300)  # 5 minute timeout
        self.cmd_or_step = cmd_or_step
        self.user_id = user_id
        # Removed self.has_survey = has_survey
        self.command_msg = None  # Reference to the command message
        self.buttons_msg = None  # Reference to the buttons message
        
    async def on_timeout(self):
        logger.warning(f"WorkloadView_slash timed out for user {self.user_id}")
        if self.buttons_msg:
            try:
                await self.buttons_msg.delete()
            except:
                pass # Ignore if already deleted
        self.stop() # Stop the view since it timed out

class WorkloadButton_slash(discord.ui.Button):
    def __init__(self, *, label: str, custom_id: str, cmd_or_step: str):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=label,
            custom_id=custom_id
        )
        self.cmd_or_step = cmd_or_step

    async def callback(self, interaction: discord.Interaction):
        # Reverted: Removed entry log
        from config import Strings # Import Strings locally
        """Handle button press with complete validation"""
        # Detailed interaction validation
        if not interaction:
            logger.error("Null interaction received in callback")
            return

        required_attrs = ['response', 'user', 'channel', 'client']
        missing_attrs = [attr for attr in required_attrs
                        if not hasattr(interaction, attr)]

        if missing_attrs:
            logger.error(f"Invalid interaction - missing: {missing_attrs}")
            return

        try:
            # Validate view
            if not hasattr(self, 'view') or not isinstance(self.view, WorkloadView_slash):
                logger.error("Invalid view in button callback")
                return

            view = self.view
            if not hasattr(view, 'user_id') or not view.user_id:
                logger.error("Invalid view - missing user_id")
                return

            # Defer response to prevent timeout
            logger.debug(f"[{view.user_id}] - Attempting to defer interaction response")
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)
            logger.debug(f"[{view.user_id}] - Interaction response deferred")

            # Delete buttons message immediately after user input
            if view.buttons_msg:
                logger.debug(f"[{view.user_id}] - Attempting to delete buttons message ID: {getattr(view.buttons_msg, 'id', 'N/A')} immediately after input.")
                try:
                    await view.buttons_msg.delete()
                    logger.info(f"[{view.user_id}] - Successfully deleted buttons message ID: {getattr(view.buttons_msg, 'id', 'N/A')} immediately after input.")
                    view.buttons_msg = None # Clear reference after deletion
                    view.stop() # Stop the view since buttons are gone
                except discord.NotFound:
                    logger.warning(f"[{view.user_id}] - Buttons message {getattr(view.buttons_msg, 'id', 'N/A')} already deleted or not found immediately after input.")
                    view.buttons_msg = None # Clear reference if not found
                except Exception as delete_error:
                    logger.error(f"[{view.user_id}] - Error deleting buttons message {getattr(view.buttons_msg, 'id', 'N/A')} immediately after input: {delete_error}", exc_info=True)


            logger.info(f"Processing workload selection for user {view.user_id}")

        except Exception as e:
            logger.error(f"Error in WorkloadButton_slash callback: {str(e)}")
            return

        try:
            # Ensure we have a valid view
            if not hasattr(self, 'view') or not isinstance(self.view, WorkloadView_slash):
                return

            view = self.view
            # No need to defer again, already done at the beginning
            # if not interaction.response.is_done():
            #     await interaction.response.defer(ephemeral=False)

        except Exception as e:
            logger.error(f"Interaction handling failed: {e}")
            return

        if not hasattr(self, 'view') or not isinstance(self.view, WorkloadView_slash):
            logger.error(f"Invalid view in callback: {getattr(self, 'view', None)}")
            return

        view = self.view
        logger.info(f"Processing WorkloadView_slash callback - view user: {view.user_id}, interaction user: {interaction.user.id}")

        if isinstance(view, WorkloadView_slash):
            # First, acknowledge the interaction to prevent timeout - already done at the beginning
            # try:
            #     logger.debug(f"[{view.user_id}] - Attempting to defer interaction response (second check)")
            #     if not interaction.response.is_done():
            #         await interaction.response.defer(ephemeral=False)
            #     logger.debug(f"[{view.user_id}] - Interaction response deferred (second check)")
            # except Exception as e:
            #     logger.error(f"[{view.user_id}] - Interaction response error: {e}")
            #     return

            logger.info(f"Workload button clicked: {self.label} by user {view.user_id} for step {view.cmd_or_step}")

            # Add processing reaction to command message
            if view.command_msg:
                try:
                    logger.debug(f"[{view.user_id}] - Attempting to add processing reaction to command message {view.command_msg.id}")
                    await view.command_msg.add_reaction(Strings.PROCESSING)
                    logger.info(f"[{view.user_id}] - Added processing reaction to command message {view.command_msg.id}")
                except Exception as e:
                    logger.error(f"[{view.user_id}] - Error adding processing reaction to command message {view.command_msg.id}: {e}")

            try:
                # Set value based on button label and convert to integer
                # Handle "Нічого немає" button specifically
                if self.label == "Нічого немає":
                    if not interaction or not interaction.channel:
                        logger.error("Missing interaction data for Нічого немає button")
                        return
                    value = 0
                    logger.info(f"Нічого немає selected in channel {interaction.channel.id}")
                else:
                    value = int(self.label)
                logger.info(f"Parsed value: {value} from label: {self.label}")

                # Removed if view.has_survey: block and its content

                logger.info(f"[{view.user_id}] - Processing as regular command: {view.cmd_or_step}")
                # Regular slash command
                webhook_payload = {
                    "command": view.cmd_or_step,
                    "status": "ok",
                    "result": {"workload": value}
                }
                logger.debug(f"[{view.user_id}] - Preparing to send webhook for regular command. Payload: {webhook_payload}")
                logger.debug(f"[{view.user_id}] - Attempting to send webhook for command: {view.cmd_or_step}")
                success, data = await webhook_service.send_webhook(
                    interaction,
                    command=webhook_payload["command"],
                    status=webhook_payload["status"],
                    result=webhook_payload["result"]
                )
                logger.info(f"[{view.user_id}] - Webhook response for command: success={success}, data={data}")
                logger.info(f"[{view.user_id}] - Webhook response for command: success={success}, data={data}")

                if success and data and "output" in data:
                    # Update command message with success
                    if view.command_msg:
                        logger.debug(f"[{view.user_id}] - Attempting to remove processing reaction from command message")
                        await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                        logger.debug(f"[{view.user_id}] - Attempting to edit command message with success output: {data['output']}")
                        await view.command_msg.edit(content=data["output"])
                        logger.info(f"[{view.user_id}] - Updated command message with success: {data['output']}")

                    # Deletion handled at the beginning
                else:
                    logger.error(f"Failed to send webhook for command: {view.cmd_or_step}")
                    if view.command_msg:
                        await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                        error_msg = Strings.WORKLOAD_ERROR.format(
                            hours=value,
                            error=Strings.GENERAL_ERROR
                        )
                        await view.command_msg.edit(content=error_msg)
                        await view.command_msg.add_reaction(Strings.ERROR)
                    # Deletion handled at the beginning

            except Exception as e:
                logger.error(f"Error in workload button: {e}", exc_info=True) # Added exc_info=True
                if view.command_msg:
                    try: # Added try-except for reaction removal
                        await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                    except Exception as remove_e:
                        logger.error(f"[{view.user_id}] - Error removing processing reaction in error handler: {remove_e}")

                    value = 0 if self.label == "Нічого немає" else self.label
                    error_msg = Strings.WORKLOAD_ERROR.format(
                        hours=value,
                        error=Strings.UNEXPECTED_ERROR
                    )
                    try: # Added try-except for message edit
                        await view.command_msg.edit(content=error_msg)
                    except Exception as edit_e:
                        logger.error(f"[{view.user_id}] - Error editing message with error message in error handler: {edit_e}")

                    try: # Added try-except for reaction add
                        await view.command_msg.add_reaction(Strings.ERROR)
                    except Exception as add_e:
                        logger.error(f"[{view.user_id}] - Error adding error reaction in error handler: {add_e}")
                else: # Added else block for error handling when command_msg is not available
                   logger.debug(f"[{getattr(view, 'user_id', 'N/A')}] - No command message available to update in error handler.")

                # Deletion handled at the beginning


def create_workload_view(cmd: str, user_id: str, timeout: Optional[float] = None, has_survey: bool = False, continue_survey_func=None) -> WorkloadView_slash:
    """Create workload view for regular commands only"""
    logger.debug(f"[{user_id}] - create_workload_view function entered with cmd: {cmd}, has_survey: {has_survey}")
    try:
        view = WorkloadView_slash(cmd, user_id)
        logger.debug(f"[{user_id}] - WorkloadView_slash instantiated successfully for cmd: {cmd}")
    except Exception as e:
        logger.error(f"[{user_id}] - Error instantiating WorkloadView_slash for cmd {cmd}: {e}", exc_info=True)
        raise

    logger.debug(f"[{user_id}] - Before importing WORKLOAD_OPTIONS for cmd: {cmd}")
    try:
        from config.constants import WORKLOAD_OPTIONS
        logger.debug(f"[{user_id}] - After importing WORKLOAD_OPTIONS for cmd: {cmd}. WORKLOAD_OPTIONS: {WORKLOAD_OPTIONS}")
    except Exception as e:
        logger.error(f"[{user_id}] - Error importing WORKLOAD_OPTIONS for cmd {cmd}: {e}", exc_info=True)
        raise

    logger.debug(f"[{user_id}] - Before adding workload buttons for cmd: {cmd}")
    try:
        # Add all workload options as buttons, including "Нічого немає"
        for hour in WORKLOAD_OPTIONS:
            custom_id = f"workload_button_{hour}_{cmd}_{user_id}"
            button = WorkloadButton_slash(label=hour, custom_id=custom_id, cmd_or_step=cmd)
            logger.debug(f"[{user_id}] - Adding button with label: {hour}, custom_id: {custom_id} for cmd: {cmd}")
            view.add_item(button)
        logger.debug(f"[{user_id}] - Finished adding workload buttons for cmd: {cmd}. Total buttons added: {len(view.children)}")
    except Exception as e:
        logger.error(f"[{user_id}] - Error adding workload buttons for cmd {cmd}: {e}", exc_info=True)
        raise

    logger.debug(f"[{user_id}] - Returning workload view for cmd: {cmd}")
    return view