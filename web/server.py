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
            
            if not user_id or not channel_id:
                logger.error("Missing required parameters")
                return web.json_response(
                    {"error": "Missing userId or channelId"}, 
                    status=400
                )

            # Just validate channel_id is an integer
            try:
                channel_id = int(channel_id)
            except ValueError:
                logger.error(f"Invalid channel ID: {channel_id}")
                return web.json_response({"error": "Invalid channel ID"}, status=400)

            class StartSurveyButton(discord.ui.Button):
                def __init__(self, user_id: str, channel_id: str):
                    # Encode both IDs in the custom ID using a separator
                    super().__init__(
                        style=discord.ButtonStyle.success,
                        label=Strings.START_SURVEY_BUTTON,
                        custom_id=f"survey_start_{channel_id}_{user_id}"  # Changed format
                    )
                    self.user_id = user_id
                    self.channel_id = channel_id
                    # Create session ID that combines both values
                    self.session_id = f"{channel_id}_{user_id}"
                    
                async def callback(self, interaction: discord.Interaction):
                    await interaction.response.defer()
                    try:
                        from bot.commands.survey import handle_start_daily_survey
                        # Pass both IDs explicitly
                        await handle_start_daily_survey(
                            interaction.client,
                            user_id=self.user_id,
                            channel_id=self.channel_id,
                            session_id=self.session_id,  # Pass combined session ID
                            steps=[]
                        )
                    except Exception as e:
                        logger.error(f"Survey start error: {str(e)}")
                        await interaction.followup.send(f"<@{self.user_id}> {Strings.SURVEY_START_ERROR}")

            try:
                channel = await self.bot.fetch_channel(channel_id)
                view = discord.ui.View(timeout=None)
                view.add_item(StartSurveyButton(user_id, str(channel_id)))
                await channel.send(f"<@{user_id}> {Strings.SURVEY_GREETING}", view=view)
                return web.json_response({"status": "Greeting message sent"})
            except Exception as e:
                logger.error(f"Failed to send button: {str(e)}")
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