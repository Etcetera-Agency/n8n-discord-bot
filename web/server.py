import os
import ssl
from aiohttp import web
from config import Config, logger
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
                logger.info(f"Found channel: {channel.name} ({channel.id})")
            except Exception as e:
                logger.error(f"Failed to fetch channel {channel_id}: {str(e)}")
                return web.json_response({"error": "Channel not found or bot doesn't have access"}, status=404)
                
            # Send greeting message with start button
            class StartSurveyButton(discord.ui.Button):
                def __init__(self, user_id: str, channel_id: str):
                    super().__init__(
                        style=discord.ButtonStyle.success,
                        label="Start Survey",
                        custom_id=f"start_survey_{user_id}"
                    )
                    self.user_id = user_id
                    self.channel_id = channel_id
                    
                async def callback(self, interaction):
                    await interaction.response.defer()
                    
                    # Verify channel access when button is clicked
                    try:
                        channel = await self.bot.fetch_channel(self.channel_id)
                        if not channel:
                            await interaction.followup.send("Channel not found", ephemeral=True)
                            return
                    except Exception as e:
                        logger.error(f"Failed to fetch channel {self.channel_id}: {str(e)}")
                        await interaction.followup.send("Channel access error", ephemeral=True)
                        return
                    
                    # Get steps from n8n or use defaults
                    payload = {
                        "command": "get_survey_steps",
                        "userId": self.user_id,
                        "channelId": self.channel_id
                    }
                    headers = {"Authorization": f"Bearer {Config.WEBHOOK_AUTH_TOKEN}"}
                    success, data = await WebhookService.send_webhook_with_retry(None, payload, headers)
                    
                    if success and data.get("steps"):
                        steps = data["steps"]
                    else:
                        steps = ["workload_today", "workload_nextweek", "connects", "dayoff_nextweek"]
                    
                    # Create new survey only when button is clicked
                    survey = survey_manager.create_survey(self.user_id, self.channel_id, steps)
                    logger.info(f"Created survey for user {self.user_id} with steps: {steps}")

                    # Start first step
                    step = survey.current_step()
                    if step:
                        await ask_dynamic_step(interaction.channel, survey, step)
                    else:
                        await interaction.followup.send(f"<@{self.user_id}> No survey steps available")

            view = discord.ui.View(timeout=None)
            view.add_item(StartSurveyButton(user_id, channel_id))
            await channel.send(f"<@{user_id}> Ready to start your daily survey?", view=view)
            
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