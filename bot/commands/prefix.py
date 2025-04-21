from discord.ext import commands
from services import webhook_service
from config import logger

class PrefixCommands:
    """
    Prefix commands for the bot.
    These are commands that start with a prefix (e.g., !).
    """
    
    def __init__(self, bot: commands.Bot):
        """
        Initialize prefix commands.
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.register_commands()
        
    def register_commands(self) -> None:
        """Register all prefix commands."""
        
        @self.bot.command(name="register", help="Використання: !register <будь-який текст>")
        async def register_cmd(ctx: commands.Context, *, text: str):
            logger.info(f"Attempting to execute register_cmd with text: {text}") # Added log
            if not text:
                await ctx.send("Потрібний формат !register Name Surname as in Team Directory")
                logger.warning(f"Register command failed: text argument missing from {ctx.author}")
                return
            """
            Register a user with the given text.
            
            Args:
                ctx: Command context
                text: Registration text
            """
            logger.info(f"Register command from {ctx.author}: {text}")
            await webhook_service.send_webhook(
                ctx,
                command="register",
                result={"text": text}
            )

        @self.bot.command(name="unregister", help="Використання: !unregister")
        async def unregister_cmd(ctx: commands.Context):
            logger.info(f"Attempting to execute unregister_cmd") # Added log
            """
            Unregister a user.
            
            Args:
                ctx: Command context
            """
            logger.info(f"Unregister command from {ctx.author}")
            await webhook_service.send_webhook(
                ctx,
                command="unregister",
                result={}
            )