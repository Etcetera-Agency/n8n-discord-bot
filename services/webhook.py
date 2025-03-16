import uuid
import asyncio
import aiohttp
import discord
from typing import Dict, Any, Tuple, Optional, Union
from discord.ext import commands
from config import Config, logger
from services.session import session_manager
from services.survey import survey_manager

# Import survey-related globals and functions
# These will be imported at runtime to avoid circular imports
SURVEYS = None
ask_dynamic_step = None
finish_survey = None

def initialize_survey_functions(surveys_dict, ask_step_func, finish_survey_func):
    """Initialize survey-related globals and functions to avoid circular imports."""
    global SURVEYS, ask_dynamic_step, finish_survey
    SURVEYS = surveys_dict
    ask_dynamic_step = ask_step_func
    finish_survey = finish_survey_func

class WebhookError(Exception):
    """Exception raised for webhook-related errors."""
    pass

class HttpSession:
    """
    Context manager for HTTP sessions.
    Ensures proper cleanup of resources.
    """
    def __init__(self):
        """Initialize the HTTP session."""
        self.session = None
        
    async def __aenter__(self) -> aiohttp.ClientSession:
        """
        Create and return a new aiohttp ClientSession.
        
        Returns:
            An aiohttp ClientSession instance
        """
        connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
        self.session = aiohttp.ClientSession(connector=connector)
        return self.session
        
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Close the aiohttp ClientSession.
        
        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        if self.session and not self.session.closed:
            await self.session.close()


class WebhookService:
    """
    Service for handling webhook communications with n8n.
    """
    def __init__(self):
        """Initialize the webhook service."""
        self.url = Config.N8N_WEBHOOK_URL
        self.auth_token = Config.WEBHOOK_AUTH_TOKEN
        self.http_session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self) -> None:
        """Initialize the HTTP session."""
        connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
        self.http_session = aiohttp.ClientSession(connector=connector)
        logger.info("Initialized webhook service HTTP session")
        
    async def close(self) -> None:
        """Close the HTTP session."""
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()
            logger.info("Closed webhook service HTTP session")
    
    def build_payload(
        self,
        command: str,
        user_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        channel: Optional[discord.TextChannel] = None,
        user: Optional[Union[discord.User, discord.Member]] = None,
        status: str = "ok",
        message: str = "",
        result: Optional[Dict[str, Any]] = None,
        is_system: bool = False
    ) -> Dict[str, Any]:
        """
        Build a consistent payload for n8n webhooks.
        
        Args:
            command: Command name
            user_id: User ID (optional)
            channel_id: Channel ID (optional)
            channel: Discord channel object (optional)
            user: Discord user object (optional)
            status: Status string (default: "ok")
            message: Message string (default: "")
            result: Result dictionary (optional)
            is_system: Whether this is a system call (default: False)
            
        Returns:
            Dict containing the webhook payload
        """
        if result is None:
            result = {}
            
        # Get channel info if channel object is provided
        if channel and not channel_id:
            channel_id = str(channel.id)
            
        # Get user info if user object is provided
        if user and not user_id:
            user_id = str(user.id)
            
        # Build the payload
        payload = {
            "command": command,
            "status": status,
            "message": message,
            "result": result,
            "author": "system" if is_system else (str(user) if user else "unknown"),
            "userId": user_id if user_id else "system",
            "sessionId": session_manager.get_session_id(user_id) if user_id else "system",
            "channelId": channel_id if channel_id else "",
            "channelName": getattr(channel, 'name', 'DM') if channel else "",
            "timestamp": int(asyncio.get_event_loop().time())
        }
        
        return payload
    
    async def send_webhook(
        self,
        ctx_or_interaction: Union[commands.Context, discord.Interaction],
        command: str,
        status: str = "ok",
        message: str = "",
        result: Optional[Dict[str, Any]] = None,
        extra_headers: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Send a webhook request to n8n.
        
        Args:
            ctx_or_interaction: Discord context or interaction
            command: Command name
            status: Status string
            message: Message string
            result: Result dictionary
            extra_headers: Additional headers
            
        Returns:
            Tuple of (success, response_data)
        """
        # Determine if we're dealing with a Context or Interaction
        is_interaction = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_interaction:
            user = ctx_or_interaction.user
            channel = ctx_or_interaction.channel
        else:
            user = ctx_or_interaction.author
            channel = ctx_or_interaction.channel
            
        # Build the payload using the unified builder
        payload = self.build_payload(
            command=command,
            user=user,
            channel=channel,
            status=status,
            message=message,
            result=result
        )
        
        # Set up headers
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        if extra_headers:
            headers.update(extra_headers)
            
        # Send webhook and get response
        success, data = await self.send_webhook_with_retry(ctx_or_interaction, payload, headers)
        
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
            await response_message.add_reaction("⏳")  # Show processing
            
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
            await response_message.remove_reaction("⏳", interaction.client.user)
            
            # If webhook was successful and we got output, delete the original message
            if success and data and "output" in data:
                # Add success reaction before deleting
                await response_message.add_reaction("✅")  # Show success
                await asyncio.sleep(1)  # Give a moment to see the success reaction
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
                await response_message.add_reaction("❌")  # Show error
                
        except Exception as e:
            logger.error(f"Error in send_interaction_response: {e}")
            if not interaction.response.is_done():
                message = await interaction.response.send_message(
                    "Помилка: Не вдалося обробити команду.",
                    ephemeral=False
                )
                await message.add_reaction("⏳")  # Show that processing was attempted
                await message.remove_reaction("⏳", interaction.client.user)
                await message.add_reaction("❌")  # Show error
    
    async def send_webhook_with_retry(
        self,
        target_channel: Any,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        max_retries: int = 3,
        retry_delay: int = 30
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Send a webhook request to n8n with retry logic.
        
        Args:
            target_channel: Discord channel or interaction
            payload: Request payload
            headers: Request headers
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
            
        Returns:
            Tuple of (success, response_data)
        """
        if not self.http_session:
            raise WebhookError("HTTP session not initialized")
            
        request_id = str(uuid.uuid4())[:8]
        logger.info(f"[{request_id}] Sending webhook to URL: {self.url}")
        logger.info(f"[{request_id}] Payload: {payload}")
        logger.info(f"[{request_id}] Headers: {headers}")
        
        for attempt in range(max_retries):
            try:
                logger.info(f"[{request_id}] Sending to n8n (attempt {attempt+1}/{max_retries})")
                async with self.http_session.post(
                    self.url,
                    json=payload,
                    headers=headers,
                    timeout=15
                ) as response:
                    response_text = await response.text()
                    logger.info(f"[{request_id}] Response status: {response.status}")
                    logger.info(f"[{request_id}] Response text: {response_text}")
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            logger.info(f"[{request_id}] Parsed JSON response: {data}")
                            return True, data
                        except Exception as e:
                            logger.error(f"[{request_id}] JSON parse error: {e}")
                            fallback = response_text.strip()
                            return True, {"output": fallback or "No valid JSON from n8n."}
                    else:
                        logger.warning(f"[{request_id}] HTTP Error {response.status}")
                        if attempt == max_retries - 1:
                            if hasattr(target_channel, "channel"):
                                await target_channel.channel.send(f"Error calling n8n: code {response.status}")
                            else:
                                await self.send_error_message(target_channel, f"Error calling n8n: code {response.status}")
            except Exception as e:
                logger.error(f"[{request_id}] Attempt {attempt+1} failed: {e}")
                if attempt == max_retries - 1:
                    if hasattr(target_channel, "channel"):
                        await target_channel.channel.send(f"An error occurred: {e}")
                    else:
                        await self.send_error_message(target_channel, f"An error occurred: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1))
        return False, None
    
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
            
        # Handle survey control
        if data and "survey" in data:
            user_id = None
            # Try to find the user_id from the channel's members
            for member in channel.members:
                if str(member.id) in session_manager.sessions:
                    user_id = str(member.id)
                    break
                    
            if user_id and user_id in SURVEYS:
                if data["survey"] == "continue":
                    # Continue to the next step in the survey
                    state = SURVEYS[user_id]
                    state.next_step()
                    next_step = state.current_step()
                    if next_step:
                        await ask_dynamic_step(channel, state, next_step)
                    else:
                        await finish_survey(channel, state)
                elif data["survey"] == "cancel":
                    # Cancel the survey
                    if user_id in SURVEYS:
                        del SURVEYS[user_id]
                    await channel.send(f"<@{user_id}> Survey has been canceled.")
                elif data["survey"] == "end":
                    # End the survey and send results
                    state = SURVEYS[user_id]
                    if "stepName" in data and "value" in data:
                        state.add_result(data["stepName"], data["value"])
                    await finish_survey(channel, state)
    
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
                
        # Handle survey control
        if data and "survey" in data:
            user_id = str(interaction.user.id)
            channel = interaction.channel
            
            if user_id and user_id in SURVEYS:
                if data["survey"] == "continue":
                    # Continue to the next step in the survey
                    state = SURVEYS[user_id]
                    state.next_step()
                    next_step = state.current_step()
                    if next_step:
                        await ask_dynamic_step(channel, state, next_step)
                    else:
                        await finish_survey(channel, state)
                elif data["survey"] == "cancel":
                    # Cancel the survey
                    if user_id in SURVEYS:
                        del SURVEYS[user_id]
                    if interaction.response.is_done():
                        await interaction.followup.send(f"<@{user_id}> Survey has been canceled.", ephemeral=False)
                    else:
                        await interaction.response.send_message(f"<@{user_id}> Survey has been canceled.", ephemeral=False)
                elif data["survey"] == "end":
                    # End the survey and send results
                    state = SURVEYS[user_id]
                    # Check if result contains stepName and value
                    if "result" in data and isinstance(data["result"], dict):
                        if "stepName" in data["result"] and "value" in data["result"]:
                            state.add_result(data["result"]["stepName"], data["result"]["value"])
                    await finish_survey(channel, state)
    
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

        # Check if this is part of a survey
        survey = None
        if hasattr(interaction, 'user'):
            survey = survey_manager.get_survey(str(interaction.user.id))

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