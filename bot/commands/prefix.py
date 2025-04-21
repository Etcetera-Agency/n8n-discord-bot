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
        logger.info("Initializing PrefixCommands...") # Added log for initialization check
        self.bot = bot
        self.register_commands()
        
    def register_commands(self) -> None:
        """Register all prefix commands."""
        
        @self.bot.command(name="register", help="Використання: !register <будь-який текст>")
        # Make text argument optional
        async def register_cmd(ctx: commands.Context, *, text: Optional[str] = None):
            # Removed debug webhook and associated logs

            # Added strip to handle potential whitespace if text is not None
            if text is not None:
                text = text.strip()

            logger.info(f"Attempting to execute register_cmd with text: '{text}' from {ctx.author}") # Updated log

            if not text: # This check now correctly handles None or empty string after stripping
                logger.info(f"Text argument is empty for register command from {ctx.author}. Sending usage message.")
                await ctx.send("Потрібний формат !register Name Surname as in Team Directory")
                logger.warning(f"Register command failed: text argument missing from {ctx.author}")
                return
            """
            Register a user with the given text.

            Args:
                ctx: Command context
                text: Registration text
            """
            logger.info(f"Register command from {ctx.author}: {text}. Attempting to send webhook...")
            try:
                # Assuming send_webhook returns a boolean or status indicator
                success = await webhook_service.send_webhook(
                    ctx,
                    command="register",
                    result={"text": text}
                )
                if success: # Check if the webhook call was successful (adjust condition if needed)
                    logger.info(f"Webhook for register command sent successfully for {ctx.author}.")
                    await ctx.send(f"Registration attempt for '{text}' sent successfully.") # Confirmation message
                else:
                    logger.warning(f"Webhook for register command failed for {ctx.author}. No explicit error, but indication of failure.")
                    await ctx.send(f"Registration attempt for '{text}' failed. Please check logs or contact admin.") # Failure message
            except Exception as e:
                logger.error(f"Error sending webhook for register command for {ctx.author}: {e}", exc_info=True)
                await ctx.send(f"An error occurred during registration for '{text}'. Please contact admin.") # Error message

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