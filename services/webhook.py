import discord
from typing import Dict, Any, Tuple, Optional, Union
from discord.ext import commands
from config import logger, Strings
from services.survey import survey_manager
from . import router

# Legacy no-op initializer retained for compatibility.
# Continuation is handled inside Discord handlers using survey_manager.
def initialize_survey_functions(*_args, **_kwargs):
    logger.debug("initialize_survey_functions called (no-op); continuation handled in handlers")


class WebhookError(Exception):
    """Exception raised for webhook-related errors."""
    pass


class WebhookService:
    """Service for handling internal webhook dispatch."""

    def __init__(self):
        logger.info("Initializing WebhookService")

    def build_payload(
        self,
        command: str,
        user_id: str,
        channel_id: str,
        status: str = "ok",
        message: str = "",
        result: Optional[Dict[str, Any]] = None,
        is_system: bool = False,
        author: Optional[str] = None, # Added author
        channel_name: Optional[str] = None, # Added channel_name
        timestamp: Optional[int] = None # Added timestamp
    ) -> Dict[str, Any]:
        """
        Build a consistent payload for n8n webhooks.

        Args:
            command: Command name
            user_id: User ID (required)
            channel_id: Channel ID (required)
            status: Status string (default: "ok")
            message: Message string (default: "")
            result: Result dictionary (optional)
            is_system: Whether this is a system call (default: False)
            author: Author tag (optional)
            channel_name: Channel name (optional)
            timestamp: Message timestamp (optional)

        Returns:
            Dict containing the webhook payload with required structure:
            {
                "command": "...",
                "status": "...",
                "message": "...",
                "result": { ... },  # Direct result content
                "userId": "...",    # Required
                "channelId": "...", # Required
                "sessionId": "..."  # Required (channelId_userId)
                "author": "...",    # Optional
                "channelName": "...", # Optional
                "timestamp": ...    # Optional
            }
        """
        if result is None:
            result = {}

        if not user_id or not channel_id:
            raise ValueError("Both user_id and channel_id are required")

        # Generate session ID from channel+user IDs
        session_id = f"{channel_id}_{user_id}"

        # Build the payload with required structure
        payload = {
            "command": command,
            "status": status,
            "message": message,
            "result": result,
            "userId": user_id,
            "channelId": channel_id,
            "sessionId": session_id
        }

        # Add optional fields if provided
        if author is not None:
            payload["author"] = author
        if channel_name is not None:
            payload["channelName"] = channel_name
        if timestamp is not None:
            payload["timestamp"] = timestamp

        return payload

    async def send_webhook(
        self,
        target: Union[commands.Context, discord.Interaction, discord.TextChannel],
        command: str,
        status: str = "ok",
        message: str = "",
        result: Optional[Dict[str, Any]] = None,
        extra_headers: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Send a webhook request to n8n.

        Args:
            target: Discord Context, Interaction or TextChannel
            command: Command name
            status: Status string
            message: Message string
            result: Result dictionary
            extra_headers: Additional headers

        Returns:
            Tuple of (success, response_data)
        """
        logger.info(f"send_webhook called with command: {command}, status: {status}, result: {result}") # Changed to INFO

        user_id = None
        channel_id = None
        author = None # Initialize author
        channel_name = None
        timestamp = None
        channel = None # Initialize channel variable

        # Determine if we're dealing with a Context or Interaction
        if isinstance(target, commands.Context):
            user_id = str(target.author.id)
            channel_id = str(target.channel.id)
            author = str(target.author)
            channel_name = target.channel.name if hasattr(target.channel, 'name') else None
            timestamp = int(target.message.created_at.timestamp()) if hasattr(target.message, 'created_at') else None
            channel = target.channel
        elif isinstance(target, discord.Interaction):
            user_id = str(target.user.id)
            channel_id = str(target.channel.id)
            author = str(target.user)
            channel_name = target.channel.name if hasattr(target.channel, 'name') else None
            timestamp = int(target.created_at.timestamp()) if hasattr(target, 'created_at') else None
            channel = target.channel
        elif isinstance(target, discord.message.Message):
            user_id = str(target.author.id)
            channel_id = str(target.channel.id)
            author = str(target.author)
            channel_name = target.channel.name if hasattr(target.channel, 'name') else None
            timestamp = int(target.created_at.timestamp()) if hasattr(target, 'created_at') else None
            channel = target.channel
        elif isinstance(target, discord.TextChannel):
            # For TextChannel target, we might not have user/author/timestamp easily
            # Depending on use case, these might be passed as extra args or be None
            channel_id = str(target.id)
            channel_name = target.name if hasattr(target, 'name') else None
            channel = target
            # user_id, author, timestamp would be None unless explicitly passed

        if not user_id and not isinstance(target, discord.TextChannel):
             logger.warning(f"send_webhook called without user_id for target type {type(target)}. Target: {target}") # Added target to log
             # Proceed but log a warning. build_payload will raise error if user_id is required.

        if not channel_id:
             logger.warning(f"send_webhook called without channel_id for target type {type(target)}. Target: {target}") # Added target to log
             # Proceed but log a warning. build_payload will raise error if channel_id is required.

        # Build the payload using the unified builder
        payload = self.build_payload(
            command=command,
            user_id=user_id,
            channel_id=channel_id,
            status=status,
            message=message,
            result=result,
            author=author, # Pass author
            channel_name=channel_name, # Pass channel_name
            timestamp=timestamp # Pass timestamp
        )

        logger.info(f"Dispatching payload via router for command: {command}")
        data = await router.dispatch(payload)
        success = data is not None
        logger.info(f"router.dispatch returned: {data}")
        logger.info(f"send_webhook returning: success={success}, data={data}") # Log at INFO level
        return success, data

    async def send_interaction_response(
        self,
        interaction: discord.Interaction,
        initial_message: str = "Processing...",
        command: str = "",
        status: str = "ok",
        message: str = "",
        result: Optional[Dict[str, Any]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        view: Optional[discord.ui.View] = None
    ) -> None:
        """
        Send an interaction response with consistent reaction handling.

        Args:
            interaction: Discord interaction
            initial_message: Initial message to show while processing
            command: Command name
            status: Status string
            message: Message string
            result: Result dictionary
            extra_headers: Additional headers
            view: Optional Discord view to attach to the message
        """
        try:
            # First, acknowledge the interaction to prevent timeout
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)

            # Send the message with view if provided
            response_message = await interaction.followup.send(initial_message, view=view, wait=True)
            await response_message.add_reaction(Strings.PROCESSING)  # Show processing

            # Send the webhook
            success, data = await self.send_webhook(
                interaction,
                command=command,
                status=status,
                message=message,
                result=result,
                extra_headers=extra_headers
            )

            # Remove processing reaction
            await response_message.remove_reaction(Strings.PROCESSING, interaction.client.user)

            # If webhook was successful and we got output, delete the original message
            if success and data and "output" in data:
                # Add success reaction before deleting
                await response_message.delete()
                await interaction.followup.send(data["output"])
            elif not success:
                # Show user's selection if available in result
                user_input = ""
                if result and isinstance(result, dict):
                    if "connects" in result:
                        user_input = f"Connects: {result['connects']}"
                    elif "value" in result:
                        user_input = f"Вибрано: {result['value']}"

                error_msg = f"{user_input}\nПомилка: Не вдалося виконати команду." if user_input else f"{initial_message}\nПомилка: Не вдалося виконати команду."
                await response_message.edit(content=error_msg)
                await response_message.add_reaction(Strings.ERROR)  # Show error

        except Exception as e:
            logger.error(f"Error in send_interaction_response: {e}")
            if not interaction.response.is_done():
                message = await interaction.response.send_message(
                    "Помилка: Не вдалося обробити команду.",
                    ephemeral=False
                )
                await message.add_reaction(Strings.PROCESSING)  # Show that processing was attempted
                await message.remove_reaction(Strings.PROCESSING, interaction.client.user)
                await message.add_reaction(Strings.ERROR)  # Show error

    async def send_webhook_with_retry(
        self,
        target_channel: Any,
        payload: Dict[str, Any],
        headers: Dict[str, str],
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Compat shim that forwards payloads to the internal router."""
        data = await router.dispatch(payload)
        return data is not None, data

    async def send_error_message(self, target: Any, message: str) -> None:
        """
        Send an error message to the appropriate destination.

        Args:
            target: Discord channel or interaction
            message: Error message
        """
        if isinstance(target, discord.Interaction):
            if target.response.is_done():
                await target.followup.send(message, ephemeral=False)
            else:
                await target.response.send_message(message, ephemeral=False)
        else:
            await target.send(message)

    async def send_n8n_reply_channel(self, channel: discord.TextChannel, data: Dict[str, Any]) -> None:
        """
        Send n8n response to a text channel.
        Args:
            channel: Discord text channel
            data: Response data
        """
        if data and "output" in data:
            await channel.send(data["output"])

        # Continuation/cancel/end are handled by Discord handlers via survey_manager

    async def send_n8n_reply_interaction(self, interaction: discord.Interaction, data: Dict[str, Any]) -> None:
        """
        Send n8n response to an interaction.
        Args:
            interaction: Discord interaction
            data: Response data
        """
        if data and "output" in data:
            if interaction.response.is_done():
                await interaction.followup.send(data["output"], ephemeral=False)
            else:
                await interaction.response.send_message(data["output"], ephemeral=False)

        # Continuation/cancel/end are handled by Discord handlers via survey_manager

    async def send_button_pressed_info(
        self,
        interaction: discord.Interaction,
        button_or_select: Union[discord.ui.Button, discord.ui.Select]
    ) -> None:
        """
        Send information about which button/select was pressed.
        Args:
            interaction: Discord interaction
            button_or_select: Button or select UI element
        """
        # Get appropriate attributes for different UI elements
        if isinstance(button_or_select, discord.ui.Button):
            value = 0 if button_or_select.label == "Нічого немає" else button_or_select.label
            custom_id = button_or_select.custom_id
        elif isinstance(button_or_select, discord.ui.Select):
            value = button_or_select.values[0] if button_or_select.values else None
            custom_id = button_or_select.custom_id
        else:
            value = None
            custom_id = None

        # Check if this is part of a survey (by channel)
        survey = None
        try:
            channel_id = str(interaction.channel.id) if hasattr(interaction, 'channel') else None
            if channel_id:
                survey = survey_manager.get_survey(channel_id)
        except Exception:
            survey = None

        # Only use survey format if we're in an active survey AND the button is a workload button
        if survey and custom_id and custom_id.startswith('workload_button_'):
            # This is a survey step
            result = {
                "stepName": survey.current_step(),
                "value": value
            }
            await self.send_webhook(
                interaction,
                command="survey",
                status="step",
                result=result
            )
        else:
            # Regular button press (from n8n components or other interactions)
            item_info = {
                "label": getattr(button_or_select, 'label', None),
                "custom_id": custom_id,
                "value": value
            }
            if isinstance(button_or_select, discord.ui.Select):
                item_info.update({
                    "placeholder": button_or_select.placeholder,
                    "values": button_or_select.values
                })

            await self.send_webhook(
                interaction,
                command="button_pressed",
                result=item_info
            )

# Global webhook service instance
webhook_service = WebhookService()
