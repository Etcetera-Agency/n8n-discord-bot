import os
import ssl
import discord
from aiohttp import web
from config import Config, logger, Strings
from services.webhook import WebhookService

class WebServer:
    def __init__(self, bot):
        """Initialize the web server."""
        self.bot = bot

    async def start_survey_http(self, request):
        """Handle HTTP requests to start surveys"""
        try:
            # Verify authorization
            auth_header = request.headers.get("Authorization")
            expected_header = f"Bearer {Config.WEBHOOK_AUTH_TOKEN}"
            if not auth_header or auth_header != expected_header:
                logger.warning("Unauthorized request attempt")
                return web.json_response({"error": "Unauthorized"}, status=401)
            
            # Parse JSON payload
            data = await request.json()
            user_id = data.get("userId")
            channel_id = data.get("channelId")
            
            # Validate IDs are strings and not empty
            if not isinstance(user_id, str) or not user_id.strip():
                logger.error(f"Invalid user ID: {user_id}")
                return web.json_response({"error": "Invalid user ID"}, status=400)
                
            try:
                channel_id = str(int(channel_id))  # Ensure numeric string format
            except (ValueError, TypeError):
                logger.error(f"Invalid channel ID: {channel_id}")
                return web.json_response({"error": "Invalid channel ID"}, status=400)
                
            # Create consistent session ID format
            session_id = f"{channel_id}_{user_id}"

            # Removed the entire nested StartSurveyButton class definition (lines 42-103).
            # Button interaction is now handled by the on_interaction listener
            # in bot/commands/events.py based on the custom_id.

            try:
                # Ensure channel_id is int for fetch_channel
                try:
                    target_channel_id = int(channel_id)
                except ValueError:
                    logger.error(f"Invalid channel ID received in HTTP request: {channel_id}")
                    return web.json_response({"error": "Invalid channel ID format"}, status=400)

                channel = await self.bot.fetch_channel(target_channel_id)
                view = discord.ui.View(timeout=None) # Persistent view

                # Create a standard button with the specific custom_id
                # custom_id format: survey_start_{channel_id}_{user_id}
                start_button = discord.ui.Button(
                    style=discord.ButtonStyle.success,
                    label=Strings.START_SURVEY_BUTTON,
                    custom_id=f"survey_start_{session_id}" # Match the ID handled in on_interaction
                )
                
                view.add_item(start_button) # Add the standard button to the view
                
                await channel.send(f"<@{user_id}> {Strings.SURVEY_GREETING}", view=view)
                logger.info(f"Sent persistent survey start button to user {user_id} in channel {channel_id} with custom_id: survey_start_{session_id}")
                return web.json_response({"status": "Greeting message sent"})
            except discord.NotFound:
                 logger.error(f"Channel {channel_id} not found when trying to send persistent button.")
                 return web.json_response({"error": f"Channel {channel_id} not found"}, status=404)
            except discord.Forbidden:
                 logger.error(f"Bot lacks permissions for channel {channel_id} to send persistent button.")
                 return web.json_response({"error": f"Bot cannot access channel {channel_id}"}, status=403)
            except Exception as e:
                logger.error(f"Failed to send persistent button: {str(e)}", exc_info=True)
                return web.json_response({"error": "Failed to initialize survey"}, status=500)
            
        except Exception as e:
            logger.error(f"Server error: {str(e)}")
            return web.json_response({"error": "Internal server error"}, status=500)
    @staticmethod
    async def run_server(bot):
        """Run the HTTP/HTTPS server"""
        app = web.Application()
        app['bot'] = bot
        
        # Create instance and bind method
        server = WebServer(bot)
        app.router.add_post('/start_survey', server.start_survey_http)
        
        port = int(Config.PORT or "3000")
        host = "0.0.0.0"
        ssl_context = None
        
        if Config.SSL_CERT_PATH and Config.SSL_KEY_PATH:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(
                certfile=Config.SSL_CERT_PATH,
                keyfile=Config.SSL_KEY_PATH
            )
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port, ssl_context=ssl_context)
        await site.start()
        logger.info(f"Server started on {host}:{port}")

async def create_and_start_server(bot):
    """Wrapper function to maintain backward compatibility"""
    await WebServer.run_server(bot)