import os
import ssl
from aiohttp import web
from config import Config, logger, Strings
from services.webhook import WebhookService

class WebServer:
    def __init__(self, bot):
        """Initialize the web server."""
        self.bot = bot
        self.active_surveys = {}  # Track active surveys

    async def start_survey_http(self, request):
        """Handle HTTP requests to start surveys"""
        auth_header = request.headers.get("Authorization")
        expected_header = f"Bearer {Config.WEBHOOK_AUTH_TOKEN}"
        if not auth_header or auth_header != expected_header:
            return web.json_response({"error": "Unauthorized"}, status=401)
        
        try:
            data = await request.json()
            user_id = data.get("userId")
            channel_id = data.get("channelId")
            
            if not user_id or not channel_id:
                return web.json_response({"error": "Missing parameters"}, status=400)

            logger.info(f"Attempting to find channel {channel_id}")
            try:
                channel = await self.bot.fetch_channel(int(channel_id))
                if not channel:
                    logger.error(f"Channel {channel_id} not found")
                    return web.json_response({"error": "Channel not found"}, status=404)
                logger.info(f"Found channel: {channel.name} ({channel.id})")
            except ValueError:
                logger.error(f"Invalid channel ID format: {channel_id}")
                return web.json_response({"error": "Invalid channel ID format"}, status=400)
            except Exception as e:
                logger.error(f"Failed to fetch channel {channel_id}: {str(e)}", exc_info=True)
                return web.json_response(
                    {"error": "Error accessing channel"},
                    status=500
                )
                
            # Verify we can send messages to this channel
            try:
                test_msg = await channel.send("Verifying channel access...")
                await test_msg.delete()
            except discord.Forbidden:
                logger.error(f"Bot lacks permissions in channel {channel.id}")
                return web.json_response(
                    {"error": "Bot lacks required permissions in channel"},
                    status=403
                )
            except Exception as e:
                logger.error(f"Channel verification failed: {str(e)}")
                return web.json_response(
                    {"error": "Channel communication failed"},
                    status=500
                )
                # Send greeting message with survey start button
                class StartSurveyButton(discord.ui.Button):
                    def __init__(self, user_id: str, channel_id: str):
                        super().__init__(
                            style=discord.ButtonStyle.success,
                            label=Strings.START_SURVEY_BUTTON,
                            custom_id=f"survey_start_{user_id}"
                        )
                        self.user_id = user_id
                        self.channel_id = channel_id
                        
                    async def callback(self, interaction: discord.Interaction):
                        await interaction.response.defer()
                        try:
                            # Simply trigger survey start - let survey manager handle steps
                            from bot.commands.survey import handle_start_daily_survey
                            await handle_start_daily_survey(interaction.client, self.user_id, self.channel_id)
                        except Exception as e:
                            logger.error(f"Error starting survey: {e}", exc_info=True)
                            await interaction.followup.send(f"<@{self.user_id}> {Strings.SURVEY_START_ERROR}: {str(e)}")

                try:
                    view = discord.ui.View(timeout=None)
                    view.add_item(StartSurveyButton(user_id, str(channel_id)))
                    await channel.send(f"<@{user_id}> {Strings.SURVEY_GREETING}", view=view)
                except Exception as e:
                    logger.error(f"Failed to send survey message: {str(e)}", exc_info=True)
                    return web.json_response(
                        {"error": "Failed to initialize survey"},
                        status=500
                    )
            
            return web.json_response({"status": "Greeting message sent"})
        
        except Exception as e:
            logger.error(f"Error in start_survey_http: {e}")
            return web.json_response({"error": str(e)}, status=500)

    @staticmethod
    async def run_server(bot):
        """Run the HTTP/HTTPS server"""
        app = web.Application()
        app['bot'] = bot
        app.router.add_post('/start_survey', WebServer.start_survey_http)
        
        port = int(Config.PORT or "3000")
        host = "0.0.0.0"
        ssl_context = None
        
        if Config.SSL_CERT_PATH and Config.SSL_KEY_PATH:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(
                certfile=Config.SSL_CERT_PATH,
                keyfile=Config.SSL_KEY_PATH
            )
            logger.info(f"Starting HTTPS server on {host}:{port}")
        else:
            logger.info(f"Starting HTTP server on {host}:{port}")
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port, ssl_context=ssl_context)
        await site.start()

async def create_and_start_server(bot):
    """Wrapper function to maintain backward compatibility"""
    await WebServer.run_server(bot)