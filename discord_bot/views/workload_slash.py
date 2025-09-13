import discord
from typing import Optional
from config import constants, Strings
from services import webhook_service
from services.logging_utils import get_logger


def _log(step: str, *, user_id: str | None = None, channel_id: str | int | None = None, session_id: str | None = None):
    payload = {}
    if user_id is not None:
        payload["userId"] = str(user_id)
    if channel_id is not None:
        payload["channelId"] = str(channel_id)
    if session_id is not None:
        payload["sessionId"] = str(session_id)
    return get_logger(step, payload)

class WorkloadView_slash(discord.ui.View):
    """View for workload selection - only used for non-survey commands"""
    def __init__(self, cmd_or_step: str, user_id: str): # Removed has_survey parameter
        super().__init__(timeout=constants.VIEW_CONFIGS[constants.ViewType.DYNAMIC]["timeout"])  # Use configured timeout
        self.cmd_or_step = cmd_or_step
        self.user_id = user_id
        # Removed self.has_survey = has_survey
        self.command_msg: Optional[discord.Message] = None  # Reference to the command message
        self.buttons_msg: Optional[discord.Message] = None  # Reference to the buttons message
        
    async def on_timeout(self):
        channel_id = self.command_msg.channel.id if self.command_msg else "unknown"
        _log("view.workload_slash", user_id=self.user_id, channel_id=channel_id).warning("timeout")
        
        # Update original command message with timeout notification
        if self.command_msg:
            try:
                # Get first 13 characters of timeout message
                timeout_msg = Strings.TIMEOUT_MESSAGE[:13]
                await self.command_msg.edit(
                    content=f"{self.command_msg.content}\n{timeout_msg}"
                )
            except Exception as e:
                _log("view.workload_slash", user_id=self.user_id, channel_id=channel_id).exception("failed to update message on timeout")
        
        # Clean up buttons message
        if self.buttons_msg:
            try:
                await self.buttons_msg.delete()
            except Exception:
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
        ch_id = getattr(getattr(interaction, "channel", None), "id", None)
        u_id = getattr(getattr(interaction, "user", None), "id", None)
        log = _log("view.workload_slash", user_id=str(u_id) if u_id else None, channel_id=ch_id)
        log.debug("callback entered", extra={"interaction_id": getattr(interaction, "id", None), "custom_id": self.custom_id})
        log.debug("button callback", extra={"step": self.cmd_or_step, "is_done": getattr(getattr(interaction, "response", None), "is_done", lambda: None)() if getattr(interaction, "response", None) else None})

        """Handle button press with complete validation"""
        log.info("callback started", extra={"interaction_id": getattr(interaction, "id", None)})

        if not interaction:
            log.error("null interaction")
            return

        view = None # Initialize view to None
        try:
            if getattr(interaction.user, 'bot', False) and str(interaction.user.id) == str(interaction.client.user.id):
                log.info("bot self interaction; skip strict validation")
                view = self.view
                if not view or not isinstance(view, WorkloadView_slash):
                    log.error("invalid view for bot interaction")
                    return
            else:
                required_attrs = ['response', 'user', 'channel', 'client']
                missing_attrs = [attr for attr in required_attrs
                                if not hasattr(interaction, attr)]

                if missing_attrs:
                    log.error("invalid interaction: missing attrs", extra={"missing": missing_attrs})
                    return

                if not hasattr(self, 'view') or not isinstance(self.view, WorkloadView_slash):
                    log.error("invalid view in button callback")
                    return

                view = self.view
                if not hasattr(view, 'user_id') or not view.user_id:
                    log.error("invalid view: missing user_id")
                    return

        except Exception as e:
            log.exception("validation error in callback")
            return

        log.info("processing workload selection")

        try:
            if not hasattr(self, 'view') or not isinstance(self.view, WorkloadView_slash):
                return

            view = self.view
            log.info("processing view", extra={"view_user": getattr(view, 'user_id', None), "interaction_user": getattr(getattr(interaction, 'user', None), 'id', None)})

            if isinstance(view, WorkloadView_slash):
                log.info("button clicked", extra={"label": self.label, "user": getattr(view, 'user_id', None), "step": view.cmd_or_step})
                if view.command_msg:
                    try:
                        log.debug("add processing reaction", extra={"command_msg_id": getattr(view.command_msg, 'id', None)})
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
                    logger.debug(f"[Channel {interaction.channel.id}] Нічого немає selected")
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

            logger.info(f"[Channel {interaction.channel.id}] [{view.user_id}] - Processing as regular command: {view.cmd_or_step}")
            webhook_payload = {
                "command": view.cmd_or_step,
                "status": "ok",
                "result": {"workload": value}
            }
            logger.debug(f"[Channel {interaction.channel.id}] [{view.user_id}] - Preparing to send webhook for regular command. Payload: {webhook_payload}")
            logger.debug(f"[Channel {interaction.channel.id}] [{view.user_id}] - Attempting to send webhook for command: {view.cmd_or_step}")
            success, data = await webhook_service.send_webhook(
                interaction,
                command=webhook_payload["command"],
                status=webhook_payload["status"],
                result=webhook_payload["result"]
            )
            logger.info(f"[Channel {interaction.channel.id}] [{view.user_id}] - Webhook response for command: success={success}, data={data}")

            if success and data and "output" in data:
                if view.command_msg:
                    try:
                        await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                        output_content = data.get("output", f"Дякую! Робоче навантаження {value} годин записано.") if data else f"Дякую! Робоче навантаження {value} годин записано."
                        await view.command_msg.edit(content=output_content, view=None, attachments=[])
                        log.info("updated command message (success)")
                    except Exception as edit_error:
                        log.exception("error editing command message (success)")
            else:
                log.error("failed to send webhook", extra={"cmd": view.cmd_or_step})
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
            _log("view.workload_slash", user_id=getattr(view, 'user_id', None), channel_id=ch_id, session_id=session_id_for_log).exception("error in workload button callback")
            if view and view.command_msg:
                await view.command_msg.remove_reaction(Strings.PROCESSING, interaction.client.user)
                value = 0 if self.label == "Нічого немає" else self.label
                error_msg = Strings.WORKLOAD_ERROR.format(
                    hours=value,
                    error=Strings.UNEXPECTED_ERROR
                )
                await view.command_msg.edit(content=error_msg)
                await view.command_msg.add_reaction(Strings.ERROR)
            _log("view.workload_slash", user_id=getattr(view, 'user_id', None), channel_id=ch_id, session_id=session_id_for_log).error("failed to send error response")
        finally:
            if view and view.buttons_msg:
                try:
                    await view.buttons_msg.delete()
                    session_id_for_log = getattr(view, 'session_id', 'N/A').split('_')[0] if view and hasattr(view, 'session_id') else 'N/A'
                    _log("view.workload_slash", user_id=getattr(view, 'user_id', None), channel_id=ch_id, session_id=session_id_for_log).info("deleted buttons message (finally)")
                    view.stop()
                except discord.NotFound:
                    session_id_for_log = getattr(view, 'session_id', 'N/A').split('_')[0] if view and hasattr(view, 'session_id') else 'N/A'
                    _log("view.workload_slash", user_id=getattr(view, 'user_id', None), channel_id=ch_id, session_id=session_id_for_log).warning("buttons already deleted or not found")
                except Exception as e:
                    session_id_for_log = getattr(view, 'session_id', 'N/A').split('_')[0] if view and hasattr(view, 'session_id') else 'N/A'
                    _log("view.workload_slash", user_id=getattr(view, 'user_id', None), channel_id=ch_id, session_id=session_id_for_log).exception("error deleting buttons (finally)")

def create_workload_view(cmd: str, user_id: str, timeout: Optional[float] = None, has_survey: bool = False, continue_survey_func=None) -> WorkloadView_slash:
    """Create workload view for regular commands only"""
    _log("view.workload_slash", user_id=user_id).debug("create_workload_view entered", extra={"cmd": cmd, "has_survey": has_survey})
    try:
        view = WorkloadView_slash(cmd, user_id)
        _log("view.workload_slash", user_id=user_id).debug("WorkloadView_slash instantiated", extra={"cmd": cmd})
    except Exception as e:
        _log("view.workload_slash", user_id=user_id).exception("error instantiating view", extra={"cmd": cmd})
        raise

    _log("view.workload_slash", user_id=user_id).debug("accessing WORKLOAD_OPTIONS", extra={"cmd": cmd})

    _log("view.workload_slash", user_id=user_id).debug("adding workload buttons", extra={"cmd": cmd})
    try:
        # Add all workload options as buttons, including "Нічого немає"
        for hour in constants.WORKLOAD_OPTIONS:
            custom_id = f"workload_button_{hour}_{cmd}_{user_id}"
            button = WorkloadButton_slash(label=hour, custom_id=custom_id, cmd_or_step=cmd)
            _log("view.workload_slash", user_id=user_id).debug("add button", extra={"label": hour, "custom_id": custom_id, "cmd": cmd})
            view.add_item(button)
        _log("view.workload_slash", user_id=user_id).debug("finished adding buttons", extra={"cmd": cmd, "total": len(view.children)})
    except Exception as e:
        _log("view.workload_slash", user_id=user_id).exception("error adding buttons", extra={"cmd": cmd})
        raise

    _log("view.workload_slash", user_id=user_id).debug("returning view", extra={"cmd": cmd})
    return view
