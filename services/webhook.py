import uuid
import asyncio
import aiohttp
import discord
import os
from typing import Dict, Any, Tuple, Optional, Union
from discord.ext import commands
from config import Config, logger, Strings # Added Strings
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
        connector = aiohttp.TCPConnector(
            limit=50,
            ttl_dns_cache=60,
            force_close=False,
            enable_cleanup_closed=True
        )
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
        logger.info("Initializing WebhookService")
        self.url = Config.N8N_WEBHOOK_URL
        self.auth_token = Config.WEBHOOK_AUTH_TOKEN
        logger.info(f"Webhook URL configured: {bool(self.url)}")
        logger.info(f"Auth token configured: {bool(self.auth_token)}")
        self.http_session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self) -> None:
        """Initialize the HTTP session."""
        try:
            logger.info("Initializing HTTP session...")
            connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
            self.http_session = aiohttp.ClientSession(connector=connector)
            logger.info("Successfully initialized webhook service HTTP session")
            # Test connectivity
            try:
                async with self.http_session.get("https://httpbin.org/get") as resp:
                    logger.info(f"HTTP test request status: {resp.status}")
            except Exception as e:
                logger.error(f"HTTP connectivity test failed: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize HTTP session: {e}")
            raise
        
    async def close(self) -> None:
        """Close the HTTP session."""
        if self.http_session and not self.http_session.closed:
            try:
                logger.info("Closing HTTP session...")
                await self.http_session.close()
                logger.info("Successfully closed webhook service HTTP session")
            except Exception as e:
                logger.error(f"Error closing HTTP session: {e}")
    
    def build_payload(
        self,
        command: str,
        user_id: str,
        channel_id: str,
        status: str = "ok",
        message: str = "",
        result: Optional[Dict[str, Any]] = None,
        is_system: bool = False
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
        logger.debug(f"send_webhook called with command: {command}, status: {status}, result: {result}") # Added log
        # Determine if we're dealing with a Context or Interaction
        is_interaction = isinstance(target, discord.Interaction)
        
        if is_interaction:
            user = target.user
            channel = target.channel
        else:
            user = target.author
            channel = target.channel
            
        # Build the payload using the unified builder
        payload = self.build_payload(
            command=command,
            user_id=str(user.id),
            channel_id=str(channel.id),
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
            
        logger.debug(f"Calling send_webhook_with_retry with payload: {payload}") # Added log
        # Send webhook and get response
        success, data = await self.send_webhook_with_retry(target, payload, headers)
        logger.debug(f"send_webhook_with_retry returned: success={success}, data={data}") # Added log
        
        # Check if n8n wants to continue the survey
        if success and data and "survey" in data and data["survey"] == "continue":
            user_id = payload['userId']
            logger.info(f"[SurveyContinuation] n8n requested survey continuation for user {user_id}")
            try:
                # Add a small delay to ensure the current interaction is complete
                await asyncio.sleep(1)
                
                logger.info(f"[SurveyContinuation] Checking for survey state for user {user_id}")
                if user_id in SURVEYS:
                    state = SURVEYS[user_id]
                    logger.info(f"[SurveyContinuation] Found survey state for user {user_id}. Current step before next_step(): {state.current_step()}, Results: {state.results}")
                    
                    logger.info(f"[SurveyContinuation] Calling state.next_step() for user {user_id}")
                    state.next_step()
                    next_step = state.current_step()
                    logger.info(f"[SurveyContinuation] Next step determined for user {user_id}: {next_step}")
                    
                    if next_step:
                        logger.info(f"[SurveyContinuation] Calling ask_dynamic_step for user {user_id}, step: {next_step}")
                        await ask_dynamic_step(channel, state, next_step)
                        logger.info(f"[SurveyContinuation] ask_dynamic_step completed for user {user_id}, step: {next_step}")
                    else:
                        logger.info(f"[SurveyContinuation] No next step found. Calling finish_survey for user {user_id}")
                        await finish_survey(channel, state)
                        logger.info(f"[SurveyContinuation] finish_survey completed for user {user_id}")
                else:
                    logger.warning(f"[SurveyContinuation] Survey state not found for user {user_id} when trying to continue.")
                    # Optionally inform the user
                    # await channel.send(f"<@{user_id}> Не вдалося знайти ваше активне опитування для продовження.")

                logger.info(f"[SurveyContinuation] Survey continuation processing completed for user {user_id}")
            except Exception as e:
                logger.error(f"[SurveyContinuation] Error handling survey continuation for user {user_id}: {e}", exc_info=True) # Added exc_info=True
                # Ensure channel is valid before sending
                if channel and hasattr(channel, 'send'):
                     await channel.send(f"<@{user_id}> Помилка при продовженні опитування: код 500") # Keep generic error for user
                else:
                     logger.error(f"[SurveyContinuation] Invalid channel object for user {user_id}, cannot send error message.")

        logger.debug(f"send_webhook returning: success={success}, data={data}") # Added log
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
        max_retries: int = 3,
        retry_delay: int = 20
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
        # Get the appropriate channel for error messages regardless of target type
        error_channel = None
        if hasattr(target_channel, 'channel'):
            error_channel = target_channel.channel
        elif isinstance(target_channel, discord.TextChannel):
            error_channel = target_channel
        elif hasattr(target_channel, 'followup'):
            error_channel = target_channel.channel

        if not self.http_session:
            # Try to initialize if session is missing
            try:
                await self.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize HTTP session: {e}")
                if error_channel:
                    await error_channel.send("Failed to initialize webhook session")
                raise WebhookError("Failed to initialize HTTP session")
            
        logger.info(f"Attempting to send webhook to URL: {self.url}") # Modified log
        logger.debug(f"Webhook Payload: {payload}") # Modified log
        logger.debug(f"Webhook Headers: {headers}") # Modified log
        
        for attempt in range(max_retries):
            request_id = str(uuid.uuid4())[:8] # Add unique ID for tracking
            logger.info(f"[{request_id}] Sending webhook attempt {attempt+1}/{max_retries}") # Added log + request_id
            try:
                logger.debug(f"[{request_id}] Preparing POST request to {self.url}") # Added log
                async with self.http_session.post(
                    self.url,
                    json=payload,
                    headers=headers,
                    timeout=15
                ) as response:
                    response_text = await response.text() # Keep reading text first
                    logger.info(f"[{request_id}] Received response status: {response.status}") # Added log + request_id
                    logger.debug(f"[{request_id}] Raw response text: {response_text}") # Added log + request_id
                    
                    if response.status == 200:
                        try:
                            data = await response.json() # Now parse JSON
                            logger.info(f"[{request_id}] Successfully received and parsed 200 OK response.") # Added log
                            logger.debug(f"[{request_id}] Parsed JSON response: {data}") # Added log
                            return True, data
                        except Exception as e:
                            logger.error(f"[{request_id}] JSON parse error: {e}. Response text was: {response_text}", exc_info=True) # Added log + request_id + exc_info
                            if error_channel:
                                await error_channel.send("Received invalid response from n8n")
                            fallback = response_text.strip()
                            return True, {"output": fallback or "No valid JSON from n8n."}
                    elif response.status >= 500: # Server errors might be retryable
                         logger.warning(f"[{request_id}] Received server error status: {response.status}. Will retry if possible.")
                         # Let retry logic handle it
                    else: # Client errors (4xx) are usually not retryable
                        logger.error(f"[{request_id}] Received client error status: {response.status}. Aborting retries.") # Added log
                        if attempt == max_retries - 1: # Log final attempt error
                            if hasattr(target_channel, "channel"):
                                await target_channel.channel.send(f"Error calling n8n: code {response.status}")
                            else:
                                await self.send_error_message(target_channel, f"Error calling n8n: code {response.status}")
            except aiohttp.ClientConnectorError as e:
                logger.error(f"[{request_id}] Attempt {attempt+1} failed: Connection Error - {e}. Will retry if possible.", exc_info=True) # Specific error + exc_info
                # Let retry logic handle it
            except asyncio.TimeoutError:
                 logger.error(f"[{request_id}] Attempt {attempt+1} failed: Request Timeout. Will retry if possible.", exc_info=True) # Specific error + exc_info
                 # Let retry logic handle it
            except Exception as e:
                logger.error(f"[{request_id}] Attempt {attempt+1} failed with unexpected error: {e}. Aborting retries.", exc_info=True) # Added log + request_id + exc_info
                if attempt == max_retries - 1: # Log final attempt error
                    if hasattr(target_channel, "channel"):
                        await target_channel.channel.send(f"An error occurred: {e}")
                    else:
                        await self.send_error_message(target_channel, f"An error occurred: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1)) # Exponential backoff might be better, but simple delay for now
        
        logger.error(f"[{request_id}] Webhook failed after {max_retries} attempts.") # Added log
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