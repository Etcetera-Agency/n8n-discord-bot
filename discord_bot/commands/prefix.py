from discord.ext import commands
from services import webhook_service
from config import logger
from typing import Optional # Import Optional

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
        # Removed self.register_commands() as commands are now methods

    async def register_cmd(self, ctx: commands.Context, full_command_text: str, text: str = ""):
        logger.info(f"register_cmd function entered with full_command_text: '{full_command_text}', text: '{text}' for message: {ctx.message.content}")

        if not text:
            logger.info(f"Text argument is empty for register command from {ctx.author}. Sending usage message.")
            await ctx.send("Потрібний формат !register Name Surname as in Team Directory")
            logger.warning(f"Register command failed: text argument missing from {ctx.author}")
            return
        """
        Register a user with the given text.

        Args:
            ctx: Command context
            text: Registration text (extracted manually)
        """
        logger.info(f"Register command from {ctx.author}: {text}. Attempting to send webhook...")
        try:
            channel = ctx.channel
            success, data = await webhook_service.send_webhook(
                ctx,
                command="register",
                message=full_command_text,
                result={"text": text}
            )
            logger.info(f"Webhook send_webhook returned success: {success}, data: {data}")
            # Check if data is a dictionary and contains 'output'
            if success and data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "output" in data[0]:
               logger.info(f"Webhook for register command succeeded for {ctx.author}")
               await channel.send(str(data[0]["output"]))
            elif success:
               logger.info(f"Webhook succeeded but unexpected response format from {ctx.author}")
               await channel.send(f"Registration attempt for '{text}' was processed")
            else:
               logger.warning(f"Webhook for register command failed for {ctx.author}. Success: {success}, Data: {data}")
               await channel.send(f"Registration attempt for '{text}' failed. Webhook call was not successful.")
        except Exception as e:
            logger.error(f"Error sending webhook for register command for {ctx.author}: {e}", exc_info=True)
            await channel.send(f"An error occurred during registration for '{text}'. Please contact admin.")

    async def unregister_cmd(self, ctx: commands.Context, full_command_text: str):
        logger.info(f"Attempting to execute unregister_cmd for message: {ctx.message.content}, full_command_text: '{full_command_text}'")
        """
        Unregister a user.
        
        Args:
            ctx: Command context
        """
        logger.info(f"Unregister command from {ctx.author}. Attempting to send webhook...")
        channel = ctx.channel
        try:
            success, data = await webhook_service.send_webhook(
                ctx,
                command="unregister",
                message=full_command_text,
                result={}
            )
            logger.info(f"Webhook send_webhook returned success: {success}, data: {data} for unregister command")
            
            # Check if data is a dictionary and contains 'output'
            if success and data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "output" in data[0]:
               logger.info(f"Webhook for unregister command succeeded for {ctx.author}")
               await channel.send(str(data[0]["output"]))
            elif success:
               logger.info(f"Webhook succeeded but unexpected response format from {ctx.author} for unregister command")
               await channel.send(f"Unregistration attempt was processed.")
            else:
               logger.warning(f"Webhook for unregister command failed for {ctx.author}. Success: {success}, Data: {data}")
               await channel.send(f"Unregistration attempt failed. Webhook call was not successful.")
        except Exception as e:
            logger.error(f"Error sending webhook for unregister command for {ctx.author}: {e}", exc_info=True)
            await channel.send(f"An error occurred during unregistration. Please contact admin.")