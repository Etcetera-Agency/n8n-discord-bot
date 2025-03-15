import ssl
import asyncio
from aiohttp import web
from typing import Optional, Dict, Any
from config import Config, logger
from services import webhook_service, survey_manager, session_manager
from bot.commands.survey import handle_start_daily_survey
import os

class WebServer:
    """
    HTTP/HTTPS server for external integrations.
    Provides endpoints for survey activation and other features.
    """
    
    def __init__(self, bot):
        """
        Initialize the web server.
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.app = web.Application()
        self.setup_routes()
        
    def setup_routes(self) -> None:
        """Set up the server routes."""
        self.app.router.add_post('/start_survey', self.start_survey_http)
        
    async def start_survey_http(self, request: web.Request) -> web.Response:
        """
        Handle HTTP request to start a survey.
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response
        """
        auth_header = request.headers.get("Authorization")
        expected_header = f"Bearer {Config.WEBHOOK_AUTH_TOKEN}"
        if not auth_header or auth_header != expected_header:
            return web.json_response({"error": "Unauthorized"}, status=401)
        
        try:
            data = await request.json()
            user_id = data.get("userId")
            channel_id = data.get("channelId")
            steps = data.get("steps", [])
            
            if not user_id or not channel_id or not steps:
                return web.json_response({"error": "Missing parameters"}, status=400)

            logger.info(f"Attempting to find channel {channel_id}")
            try:
                channel = await self.bot.fetch_channel(int(channel_id))
                logger.info(f"Found channel: {channel.name} ({channel.id})")
            except Exception as e:
                logger.error(f"Failed to fetch channel {channel_id}: {str(e)}")
                return web.json_response({"error": "Channel not found or bot doesn't have access"}, status=404)
                
            # Check if channel is registered
            payload = webhook_service.build_payload(
                command="check_channel",
                user_id=user_id,
                channel_id=channel_id,
                channel=channel,
                is_system=True,
                result={}  # Empty result for check_channel
            )
            
            headers = {}
            if Config.WEBHOOK_AUTH_TOKEN:
                headers["Authorization"] = f"Bearer {Config.WEBHOOK_AUTH_TOKEN}"
            
            logger.info(f"Sending check_channel webhook to n8n with payload: {payload}")
            success_check, data_check = await webhook_service.send_webhook_with_retry(None, payload, headers)
            logger.info(f"n8n webhook response - success: {success_check}, data: {data_check}")
            
            if not success_check or str(data_check.get("output", "false")).lower() != "true":
                logger.error(f"Channel registration check failed - success: {success_check}, data: {data_check}")
                return web.json_response({"error": "Channel is not registered"}, status=403)

            await handle_start_daily_survey(self.bot, user_id, channel_id, steps)
            return web.json_response({"status": "Survey started"})
        
        except Exception as e:
            logger.error(f"Error in start_survey_http: {e}")
            return web.json_response({"error": str(e)}, status=500)
            
    async def start(self) -> None:
        """Start the web server."""
        # Use CAPTAIN_PORT if available (for CapRover deployment)
        port = int(os.getenv("PORT", os.getenv("CAPTAIN_PORT", Config.PORT)))
        host = Config.HOST
        ssl_context = None
        
        if Config.SSL_CERT_PATH and Config.SSL_KEY_PATH:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(certfile=Config.SSL_CERT_PATH, keyfile=Config.SSL_KEY_PATH)
            logger.info(f"Starting HTTPS server on {host}:{port}")
        else:
            logger.info(f"Starting HTTP server on {host}:{port}")
            
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port, ssl_context=ssl_context)
        await site.start()
        
        logger.info(f"Web server started on {host}:{port}")

async def create_and_start_server(bot) -> WebServer:
    """
    Create and start the web server.
    
    Args:
        bot: Discord bot instance
        
    Returns:
        The WebServer instance
    """
    server = WebServer(bot)
    await server.start()
    return server 