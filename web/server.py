import ssl
import asyncio
import discord
from aiohttp import web
from typing import Optional, Dict, Any
from config import Config, logger
from services import webhook_service, survey_manager, session_manager
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
            
            if not user_id or not channel_id:
                return web.json_response({"error": "Missing parameters"}, status=400)

            logger.info(f"Attempting to find channel {channel_id}")
            try:
                channel = await self.bot.fetch_channel(int(channel_id))
                logger.info(f"Found channel: {channel.name} ({channel.id})")
            except Exception as e:
                logger.error(f"Failed to fetch channel {channel_id}: {str(e)}")
                return web.json_response({"error": "Channel not found or bot doesn't have access"}, status=404)
                
            # Instead of checking the channel now, just send a greeting message with a button
            class StartSurveyButton(discord.ui.Button):
                def __init__(self, user_id: str, channel_id: str):
                    super().__init__(
                        style=discord.ButtonStyle.success,
                        label="Так",
                        custom_id=f"start_survey_{channel_id}"
                    )
                    self.user_id = user_id
                    self.channel_id = channel_id
                    
                async def callback(self, interaction):
                    # First, acknowledge the interaction to prevent timeout
                    if not interaction.response.is_done():
                        await interaction.response.defer(ephemeral=False)
                    
                    logger.info(f"Start survey button clicked by user {self.user_id} in channel {self.channel_id}")
                    
                    try:
                        # Send a temporary message to show that the button was clicked
                        await interaction.followup.send("Запускаю опитування...", ephemeral=True)
                        
                        # Check if channel is registered
                        payload = webhook_service.build_payload(
                            command="check_channel",
                            user_id=self.user_id,
                            channel_id=self.channel_id,
                            channel=interaction.channel,
                            is_system=True,
                            result={}  # Empty result for check_channel
                        )
                        
                        headers = {}
                        if Config.WEBHOOK_AUTH_TOKEN:
                            headers["Authorization"] = f"Bearer {Config.WEBHOOK_AUTH_TOKEN}"
                        
                        logger.info(f"Sending check_channel webhook to n8n with payload: {payload}")
                        success_check, data_check = await webhook_service.send_webhook_with_retry(None, payload, headers)
                        logger.info(f"n8n webhook response - success: {success_check}, data: {data_check}")
                        
                        # Default steps to use if n8n fails or doesn't provide steps
                        default_steps = ["workload_today"]
                        
                        if not success_check:
                            logger.warning(f"Channel registration check failed with error. Using default steps: {default_steps}")
                            steps = default_steps
                        elif str(data_check.get("output", "false")).lower() != "true":
                            logger.error(f"Channel registration check returned false - success: {success_check}, data: {data_check}")
                            await interaction.followup.send("Канал не зареєстровано. Будь ласка, зареєструйте його перед початком спілкування з ботом.", ephemeral=True)
                            return
                        else:
                            # Get steps from n8n response
                            if "steps" in data_check:
                                # Filter out unknown steps
                                known_steps = ["workload_today", "workload_nextweek", 
                                              "day_off_nextweek", "connects_thisweek"]
                                filtered_steps = [step for step in data_check["steps"] if step in known_steps]
                                
                                if filtered_steps:
                                    logger.info(f"Using filtered steps from n8n response: {filtered_steps}")
                                    steps = filtered_steps
                                else:
                                    logger.warning(f"No known steps in n8n response: {data_check['steps']}. Using default steps: {default_steps}")
                                    steps = default_steps
                            else:
                                logger.warning(f"No steps provided in n8n response. Using default steps: {default_steps}")
                                steps = default_steps
                        
                        # Log the steps that will be used
                        logger.info(f"Starting survey for user {self.user_id} in channel {self.channel_id} with steps: {steps}")
                        
                        # Start the survey
                        from bot.commands.survey import handle_start_daily_survey
                        await handle_start_daily_survey(interaction.client, self.user_id, self.channel_id, steps)
                        
                        # Send a confirmation message
                        await interaction.followup.send("Опитування запущено! Будь ласка, дайте відповідь на питання вище.", ephemeral=True)
                        
                    except Exception as e:
                        logger.error(f"Error starting survey: {e}")
                        # Send an error message to the user
                        await interaction.followup.send(f"Помилка при запуску опитування: {str(e)}", ephemeral=True)

            class StartSurveyView(discord.ui.View):
                def __init__(self, user_id: str, channel_id: str):
                    super().__init__(timeout=None)  # No timeout - button stays forever
                    self.add_item(StartSurveyButton(user_id, channel_id))
            
            view = StartSurveyView(user_id, channel_id)
            await channel.send(f"Привіт <@{user_id}>! Готовий почати робочий день?", view=view)
            
            return web.json_response({"status": "Greeting message sent"})
        
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