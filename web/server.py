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
            logger.info("Received request to /start_survey")

            # Parse JSON payload
            data = await request.json()
            logger.info(f"Parsed JSON payload: {data}")
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
            try:
                channel = await self.bot.fetch_channel(channel_id)
                logger.info(f"Attempting to send greeting message to channel {channel_id} for user {user_id}")
                from discord_bot.views.start_survey import StartSurveyView
                await channel.send(f"<@{user_id}> {Strings.SURVEY_GREETING}", view=StartSurveyView())
                logger.info("Greeting message sent successfully")
                return web.json_response({"status": "Greeting message sent"})
            except Exception as e:
                logger.error(f"Failed to send button: {str(e)}")
                return web.json_response({"error": "Failed to initialize survey"}, status=500)

        except Exception as e:
            logger.error(f"Server error: {str(e)}")
            return web.json_response({"error": "Internal server error"}, status=500)

    async def debug_log_handler(self, request):
        """Handle requests to view the debug log file."""
        log_file_path = "/app/logs/register_debug.log" # Updated path
        try:
            with open(log_file_path, "r") as f:
                content = f.read()
            return web.Response(text=content, content_type="text/plain")
        except FileNotFoundError:
            return web.Response(text=f"Debug log file not found at {log_file_path}", status=404)
        except Exception as e:
            logger.error(f"Error reading debug log file: {e}")
            return web.Response(text=f"Error reading debug log file: {e}", status=500)

    @staticmethod
    async def run_server(bot):
        """Run the HTTP/HTTPS server"""
        app = web.Application()
        app['bot'] = bot

        # Create instance and bind method
        server = WebServer(bot)
        app.router.add_post('/start_survey', server.start_survey_http)
        # Add route to expose debug log file
        app.router.add_get('/debug_log', server.debug_log_handler)

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
