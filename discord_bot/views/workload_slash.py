import discord
from typing import Optional
from config import logger, Strings, constants # Added Strings, constants
from services import webhook_service # Removed survey_manager

class WorkloadView_slash(discord.ui.View):
    """View for workload selection - only used for non-survey commands"""
    def __init__(self, cmd_or_step: str, user_id: str): # Removed has_survey parameter
        logger.debug(f"[{user_id}] - WorkloadView_slash.__init__ called for cmd_or_step: {cmd_or_step}") # Removed has_survey from log
        super().__init__(timeout=constants.VIEW_CONFIGS[constants.ViewType.DYNAMIC]["timeout"])  # Use configured timeout
        self.cmd_or_step = cmd_or_step
        self.user_id = user_id
        # Removed self.has_survey = has_survey
        self.command_msg: == None  # Reference to the command message
        self.buttons_msg: == None  # Reference to the buttons message
        
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
        logger.debug(f"WorkloadButton_slash.callback entered. Interaction ID: {interaction.id}, Custom ID: {self.custom_id}")
        logger.debug(f"Button callback for step: {self.cmd_or_step}, interaction.response.is_done(): {interaction.response.is_done()}")
        from config import Strings

        """Handle button press with complete validation"""
        logger.info(f"WorkloadButton_slash callback started - interaction: {interaction.id}, user: {getattr(interaction, 'user', None)}, bot: {getattr(interaction.client, 'user', None)}")

        if not interaction:
            logger.error("Null interaction received in callback")
            return

        view = None # Initialize view to None
        try:
            if getattr(interaction.user, 'bot', False) and str(interaction.user.id) == str(interaction.client.user.id):
                logger.info("Processing bot's own interaction - skipping strict validation")
                view = self.view
                if not view or not isinstance(view, WorkloadView_slash):
                    logger.error("Invalid view for bot interaction")
                    return
            else:
                required_attrs = ['response', 'user', 'channel', 'client']
                missing_attrs = [attr for attr in required_attrs
                                if not hasattr(interaction, attr)]

                if missing_attrs:
                    logger.error(f"Invalid interaction - missing: {missing_attrs}")
                    return

                if not hasattr(self, 'view') or not isinstance(self.view, WorkloadView_slash):
                    logger.error("Invalid view in button callback")
                    return

                view = self.view
                if not hasattr(view, 'user_id') or not view.user_id:
                    logger.error("Invalid view - missing user_id")
                    return

        except Exception as e:
            logger.error(f"Error in WorkloadButton_slash callback: {str(e)}")
            return

        logger.info(f"Processing workload selection for channel {getattr(interaction.channel, 'id', 'N/A')}")

        try:
            if not hasattr(self, 'view') or not isinstance(self.view, WorkloadView_slash):
                return

            view = self.view
            logger.info(f"Processing WorkloadView_slash callback - view user: {view.user_id}, interaction user: {interaction.user.id}")

            if isinstance(view, WorkloadView_slash):
                logger.info(f"Workload button clicked: {self.label} by user {view.user_id} for step {view.cmd_or_step}")
                if view.command_msg:
                    try:
                        logger.debug(f"[Channel {getattr(interaction.channel, 'id', 'N/A')}] - Attempting to add processing reaction to command message {view.command_msg.id}")
                        await view.command_msg.add_reaction(Strings.PROCESSING)
                        logger.debug(f"[Channel {getattr(interaction.channel, 'id', 'N/A')}] - Added processing reaction to command message {view.command_msg.id}")
                    except Exception as e:
                        logger.error(f"[Channel {getattr(interaction.channel, 'id', 'N/A')}] - Error adding processing reaction to command message {getattr(view.command_msg, 'id', 'N/A')}: {e}", exc_info=True)

            try:
                if self.label == "Нічого немає":
                    if not interaction or not interaction.channel:
                        logger.error("Missing interaction data for Нічого немає button")
                        return
                    value = 0
                    logger.debug(f"Нічого немає selected in channel {interaction.channel.id}")
                else:
                    value = int(self.label)
                logger.debug(f"Parsed value: {value} from label: {self.label}")
            except ValueError:
                logger.error(f"[Channel {getattr(interaction.channel, 'id', 'N/A')}] - Could not convert button label to integer: {self.label}", exc_info=True)
                if not interaction.response.is_done():
                     await interaction.followup.send("Invalid button value.", ephemeral=True)
                return
            except Exception as e:
                logger.error(f"[Channel {getattr(interaction.channel, 'id', 'N/A')}] - Unexpected error parsing button value: {e}", exc_info=True)
                if not interaction.response.is_done():
                     await interaction.followup.send("An unexpected error occurred.", ephemeral=True)
                return

            if view.buttons_msg:
                try:
                    await view.buttons_msg.delete()
                    logger.info(f"[Channel {getattr(interaction.channel, 'id', 'N/A')}] - Successfully deleted buttons message ID: {view.buttons_msg.id}")
                    view.buttons_msg = None
                    view.stop()
                except discord.NotFound:
                    logger.warning(f"[Channel {getattr(interaction.channel, 'id', 'N/A')}] - Buttons message {getattr(view.buttons_msg, 'id', 'N/A')} already deleted or not found.")
                    view.buttons_msg = None
                except Exception as delete_error:
                    logger.error(f"[Channel {getattr(interaction.channel, 'id', 'N/A')}] - Error deleting buttons message {getattr(view.buttons_msg, 'id', 'N/A')}: {delete_error}", exc_info=True)
            else:
                logger.warning(f"[Channel {getattr(interaction.channel, 'id', 'N/A')}] - view.buttons_msg is None or False, cannot delete.")

            logger.info(f"[{view.user_id}] - Processing as regular command: {view.cmd_or_step}")
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

            if success and data and "output" in data:
                if view.command_msg:
                    try:
                        await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                        output_content = data.get("output", f"Дякую! Робоче навантаження {value} годин записано.") if data else f"Дякую! Робоче навантаження {value} годин записано."
                        await view.command_msg.edit(content=output_content, view=None, attachments=[])
                        logger.info(f"[{view.user_id}] - Updated command message with success: {output_content}")
                    except Exception as edit_error:
                        logger.error(f"[{view.user_id}] - Error editing command message with success output: {edit_error}", exc_info=True)
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
        except Exception as e:
            session_id_for_log = getattr(view, 'session_id', 'N/A').split('_')[0] if view and hasattr(view, 'session_id') else 'N/A'
            logger.error(f"[Channel {session_id_for_log}] - Error in workload button callback: {e}", exc_info=True)
            if view and view.command_msg:
                await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                value = 0 if self.label == "Нічого немає" else self.label
                error_msg = Strings.WORKLOAD_ERROR.format(
                    hours=value,
                    error=Strings.UNEXPECTED_ERROR
                )
                await view.command_msg.edit(content=error_msg)
                await view.command_msg.add_reaction(Strings.ERROR)
            logger.error(f"[Channel {session_id_for_log}] - Failed to send error response in workload callback: {e}")
        finally:
            if view and view.buttons_msg:
                try:
                    await view.buttons_msg.delete()
                    session_id_for_log = getattr(view, 'session_id', 'N/A').split('_')[0] if view and hasattr(view, 'session_id') else 'N/A'
                    logger.info(f"[Channel {session_id_for_log}] - Successfully deleted buttons message in finally block.")
                    view.stop()
                except discord.NotFound:
                    session_id_for_log = getattr(view, 'session_id', 'N/A').split('_')[0] if view and hasattr(view, 'session_id') else 'N/A'
                    logger.warning(f"[Channel {session_id_for_log}] - Buttons message already deleted or not found in finally block.")
                except Exception as e:
                    session_id_for_log = getattr(view, 'session_id', 'N/A').split('_')[0] if view and hasattr(view, 'session_id') else 'N/A'
                    logger.error(f"[Channel {session_id_for_log}] - Error deleting buttons message in finally block: {e}", exc_info=True)

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