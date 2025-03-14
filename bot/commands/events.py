import discord
from discord.ext import commands
from config import logger
from services import webhook_service
from bot.commands.survey import handle_start_daily_survey

class EventHandlers:
    """
    Event handlers for the bot.
    These handle Discord events like messages, reactions, etc.
    """
    
    def __init__(self, bot: commands.Bot):
        """
        Initialize event handlers.
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.register_handlers()
        
    def register_handlers(self) -> None:
        """Register all event handlers."""
        
        @self.bot.event
        async def on_ready():
            """Handle bot ready event."""
            logger.info(f"Bot connected as {self.bot.user}")
            await webhook_service.initialize()
            try:
                await self.bot.tree.sync()
                logger.info("Slash commands synced!")
            except Exception as e:
                logger.error(f"Error syncing slash commands: {e}")

        @self.bot.event
        async def on_close():
            """Handle bot close event."""
            logger.info("Bot shutting down, cleaning up resources")
            await webhook_service.close()

        @self.bot.event
        async def on_message(message: discord.Message):
            """
            Handle message events.
            
            Args:
                message: Discord message
            """
            if message.author == self.bot.user:
                return

            if self.bot.user in message.mentions:
                # Add processing reaction
                await message.add_reaction("⏳")
                
                # Process the message
                success, _ = await webhook_service.send_webhook(
                    message,
                    command="mention",
                    message=message.content,
                    result={}
                )
                
                # Remove processing reaction
                await message.remove_reaction("⏳", self.bot.user)
                
                # Add success or error reaction
                await message.add_reaction("✅" if success else "❌")

            if message.content.startswith("start_daily_survey"):
                parts = message.content.split()
                if len(parts) >= 4:
                    user_id = parts[1]
                    channel_id = parts[2]
                    steps = parts[3:]
                    await handle_start_daily_survey(user_id, channel_id, steps)

            await self.bot.process_commands(message) 