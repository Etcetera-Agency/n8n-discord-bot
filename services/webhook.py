import uuid
import asyncio
import aiohttp
import discord
from typing import Dict, Any, Tuple, Optional, Union
from discord.ext import commands
from config import Config, logger
from services.session import session_manager

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
        if result is None:
            result = {}
            
        # Determine if we're dealing with a Context or Interaction
        is_interaction = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_interaction:
            user = ctx_or_interaction.user
            channel = ctx_or_interaction.channel
            channel_id = str(ctx_or_interaction.channel_id)
        else:
            user = ctx_or_interaction.author
            channel = ctx_or_interaction.channel
            channel_id = str(ctx_or_interaction.channel.id)
            
        user_id = str(user.id)
        session_id = session_manager.get_session_id(user_id)
        
        # Build the payload
        payload = {
            "command": command,
            "status": status,
            "message": message,
            "result": result,
            "author": str(user),
            "userId": user_id,
            "sessionId": session_id,
            "channelId": channel_id,
            "channelName": getattr(channel, 'name', 'DM'),
            "timestamp": int(asyncio.get_event_loop().time())
        }
        
        # Set up headers
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        if extra_headers:
            headers.update(extra_headers)
            
        # Send webhook and get response
        success, data = await self.send_webhook_with_retry(ctx_or_interaction, payload, headers)
        
        # If successful, send the reply via the appropriate channel
        if success and data:
            if is_interaction:
                await self.send_n8n_reply_interaction(ctx_or_interaction, data)
            else:
                await self.send_n8n_reply_channel(channel, data)
                
        return success, data
    
    async def send_webhook_with_retry(
        self,
        target_channel: Any,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        max_retries: int = 3,
        retry_delay: int = 1
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
        for attempt in range(max_retries):
            try:
                logger.info(f"[{request_id}] Sending to n8n (attempt {attempt+1}/{max_retries})")
                async with self.http_session.post(
                    self.url,
                    json=payload,
                    headers=headers,
                    timeout=15
                ) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                            return True, data
                        except Exception as e:
                            logger.error(f"[{request_id}] JSON parse error: {e}")
                            fallback = (await response.text()).strip()
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
            item_info = {"label": button_or_select.label, "custom_id": button_or_select.custom_id}
        elif isinstance(button_or_select, discord.ui.Select):
            item_info = {
                "placeholder": button_or_select.placeholder,
                "custom_id": button_or_select.custom_id,
                "values": button_or_select.values
            }
        else:
            item_info = {"type": str(type(button_or_select))}
        
        await self.send_webhook(
            interaction,
            command="button_pressed",
            result=item_info
        )
        logger.info(f"UI element info sent: {item_info}, user: {interaction.user}")

# Global webhook service instance
webhook_service = WebhookService() 