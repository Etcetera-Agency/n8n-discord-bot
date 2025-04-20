import discord
from discord.ext import commands
import aiohttp
from services import survey_manager # Import survey_manager
from services.webhook import WebhookService
from config import logger, Strings # Import Strings
from bot.commands.survey import ask_dynamic_step, handle_start_daily_survey # Import survey functions

class EventHandlers:
    def __init__(self, bot):
        """Initialize event handlers with the bot instance"""
        logger.debug("EventHandlers.__init__ called.") # ADDED LOG
        self.bot = bot
        self.http_session = None
        logger.debug("EventHandlers instance created.") # ADDED LOG

    async def setup(self):
        """Register all event handlers with the bot"""
        logger.debug("EventHandlers.setup called.") # ADDED LOG
        self.bot.add_listener(self.on_ready)
        logger.debug("Registered on_ready listener.") # ADDED LOG
        self.bot.add_listener(self.on_close)
        logger.debug("Registered on_close listener.") # ADDED LOG
        self.bot.add_listener(self.on_message)
        logger.debug("Registered on_message listener.") # ADDED LOG
        self.bot.add_listener(self.on_interaction) # Register the new listener
        logger.debug("Registered on_interaction listener.") # ADDED LOG
        logger.debug("EventHandlers.setup completed.") # ADDED LOG

    async def on_ready(self):
        logger.info(f"Bot connected as {self.bot.user}")
        connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
        self.http_session = aiohttp.ClientSession(connector=connector)

        # Initialize WebhookService and assign to bot
        self.bot.webhook_service = WebhookService()
        await self.bot.webhook_service.initialize()
        
        try:
            await self.bot.tree.sync()
            logger.info("Slash commands synced!")
        except Exception as e:
            logger.error(f"Error syncing slash commands: {e}")

    async def on_close(self):
        logger.info("Bot shutting down, cleaning up resources")
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()

    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return

        if self.bot.user in message.mentions:
            await message.add_reaction("⏳")
            success, _ = await self.bot.webhook_service.send_webhook(
                message,
                command="mention",
                message=message.content,
                result={}
            )
            await message.remove_reaction("⏳", self.bot.user)
            await message.add_reaction("✅" if success else "❌")

        if message.content.startswith("start_daily_survey"):
            parts = message.content.split()
            if len(parts) >= 4:
                user_id = parts[1]
                channel_id = parts[2]
                steps = parts[3:]
                await self.handle_start_daily_survey(user_id, channel_id, steps)

        await self.bot.process_commands(message)

    async def on_interaction(self, interaction: discord.Interaction):
        """Handles interactions, including persistent buttons."""
        
        # Process component interactions (buttons, selects, etc.)
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id")

            # --- Handle Persistent Survey Start Button ---
            if custom_id and custom_id.startswith("survey_start_"):
                logger.info(f"Handling persistent survey start button click: {custom_id}")
                logger.debug(f"Attempting to defer interaction {interaction.id} for survey_start...")
                await interaction.response.defer(ephemeral=True) # Acknowledge interaction privately
                logger.debug(f"Successfully deferred interaction {interaction.id} for survey_start.")

                try:
                    logger.debug(f"Entering try block for survey_start interaction {interaction.id}")
                    # Extract IDs from custom_id: survey_start_{channel_id}_{user_id}
                    parts = custom_id.split("_")
                    if len(parts) < 4:
                        logger.error(f"Invalid survey_start custom_id format: {custom_id}")
                        await interaction.followup.send("Invalid button ID format.", ephemeral=True)
                        return
                        
                    channel_id = parts[2]
                    user_id = parts[3] # Assuming user_id is the last part
                    session_id = f"{channel_id}_{user_id}" # Reconstruct session_id

                    existing_survey = survey_manager.get_survey(user_id)
                    
                    if existing_survey:
                        # Survey exists, try to repeat the current step
                        logger.info(f"Existing survey found for user {user_id} via persistent button. Repeating current step.")
                        logger.debug(f"Attempting to find channel {channel_id} for resuming survey (interaction {interaction.id}).")
                        # Use interaction.channel if available and matches, otherwise fetch
                        channel = None
                        if interaction.channel and str(interaction.channel.id) == channel_id:
                             channel = interaction.channel
                        else:
                            try:
                                channel = await interaction.client.fetch_channel(int(channel_id))
                            except discord.NotFound:
                                logger.error(f"Channel {channel_id} not found for resuming survey via persistent button.")
                                await interaction.followup.send(f"<@{user_id}> {Strings.CHANNEL_NOT_FOUND_ERROR}", ephemeral=True)
                                return
                            except discord.Forbidden:
                                 logger.error(f"Bot lacks permissions for channel {channel_id} for persistent button.")
                                 await interaction.followup.send(f"<@{user_id}> {Strings.CHANNEL_PERMISSION_ERROR}", ephemeral=True)
                                 return
                            except ValueError:
                                logger.error(f"Invalid channel ID format in custom_id: {channel_id}")
                                await interaction.followup.send("Invalid channel ID in button.", ephemeral=True)
                                return

                        current_step = existing_survey.current_step()
                        if channel and current_step:
                            # Re-ask the step in the correct channel
                            logger.debug(f"Attempting to re-ask step '{current_step}' for existing survey (interaction {interaction.id}).")
                            await ask_dynamic_step(channel, existing_survey, current_step)
                            # Send an ephemeral message confirming action if needed
                            await interaction.followup.send("Repeating the current survey step.", ephemeral=True)
                            logger.debug(f"Successfully re-asked step '{current_step}' (interaction {interaction.id}).")
                        elif channel:
                            logger.warning(f"Existing survey for user {user_id} (persistent button) has no current step.")
                            await interaction.followup.send(f"<@{user_id}> Не вдалося знайти поточний крок опитування.", ephemeral=True)
                        # Error already handled if channel fetch failed
                            
                    else:
                        # No survey exists, start a new one
                        logger.info(f"No existing survey found for user {user_id} via persistent button. Starting new survey.")
                        logger.debug(f"Attempting to call handle_start_daily_survey for new survey (interaction {interaction.id}).")
                        await handle_start_daily_survey(
                            interaction.client,
                            user_id=user_id,
                            channel_id=channel_id,
                            session_id=session_id,
                            steps=[] # Fetched within handle_start_daily_survey
                        )
                        logger.debug(f"handle_start_daily_survey call completed for interaction {interaction.id}.")
                        await interaction.followup.send("Starting a new survey...", ephemeral=True)

                except Exception as e:
                    logger.error(f"Caught exception in persistent survey button interaction ({custom_id}): {str(e)}", exc_info=True) # Added 'Caught' for clarity
                    try:
                        # Ensure followup is used for deferred responses
                        await interaction.followup.send(f"<@{user_id}> {Strings.SURVEY_START_ERROR}", ephemeral=True)
                    except Exception as e_inner:
                         logger.error(f"Failed to send error followup for persistent button: {e_inner}")

            # --- Add other component interaction handlers here if needed ---
            # elif custom_id and custom_id.startswith("other_button_"):
            #     pass

        # --- Handle Slash Commands ---
        # (discord.py automatically routes slash commands if synced and defined in cogs/bot commands)
        # You might add specific pre/post invocation hooks here if needed.

        # --- Handle Modal Submissions ---
        elif interaction.type == discord.InteractionType.modal_submit:
            custom_id = interaction.data.get("custom_id")
            logger.debug(f"Modal submitted: {custom_id}")
            # Add specific modal handling logic here if modals are defined globally
            # Example:
            # if custom_id == "my_global_modal":
            #     await handle_my_global_modal(interaction)


        # IMPORTANT: If using cogs or bot.command for slash commands,
        # ensure this on_interaction doesn't prevent those from running.
        # Typically, discord.py handles command dispatching before on_interaction
        # for commands, but explicitly calling process_commands might be needed
        # in complex scenarios (less common now with interaction-based commands).
        # await self.bot.process_application_commands(interaction) # Usually not needed if commands are registered correctly