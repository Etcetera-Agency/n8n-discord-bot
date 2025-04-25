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
        logger.info(f"Register command used in channel: {ctx.channel.name} (ID: {ctx.channel.id})") # Log channel info
        # await ctx.defer() # Defer only if proceeding to webhook

        if not text:
            logger.info(f"Text argument is empty for register command from {ctx.author}. Sending usage message.")
            # Use ctx.send for immediate error feedback, no defer needed here.
            await ctx.send("Потрібний формат !register Name Surname as in Team Directory")
            logger.warning(f"Register command failed: text argument missing from {ctx.author}")
            return

        # Defer *after* validation, before webhook call
        # Send placeholder message before webhook call
        placeholder_message = await ctx.send(f"Registering {ctx.author.mention}...")

        """
        Register a user with the given text.

        Args:
            ctx: Command context
            text: Registration text (extracted manually)
        """
        logger.info(f"Register command from {ctx.author}: {text}. Attempting to send webhook...")
        try:
            success, data = await webhook_service.send_webhook(
                ctx, # Pass context for user/channel info extraction
                command="register",
                message=full_command_text,
                result={"text": text}
            )
            logger.info(f"Webhook send_webhook returned success: {success}, data: {data}")
            # Check if data is a dictionary and contains 'output'
            # Check if data is a dictionary with 'output' or a list containing one
            output_message = None
            if success and data:
                if isinstance(data, dict) and "output" in data:
                    output_message = str(data["output"])
                    logger.info(f"Webhook for register command succeeded for {ctx.author} with dictionary response.")
                elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "output" in data[0]:
                    output_message = str(data[0]["output"])
                    logger.info(f"Webhook for register command succeeded for {ctx.author} with list response.")

            # Determine final content and edit placeholder
            final_content = None
            if output_message:
               final_content = output_message
            elif success:
               logger.info(f"Webhook succeeded but no valid output found in response from {ctx.author}")
               final_content = f"Registration attempt for '{text}' processed, {ctx.author.mention}."
            else:
               logger.warning(f"Webhook for register command failed for {ctx.author}. Success: {success}, Data: {data}")
               error_detail = f" (Error: {data})" if data else ""
               final_content = f"Registration attempt for '{text}' failed, {ctx.author.mention}.{error_detail}"

            # Edit the placeholder message with the final content
            await placeholder_message.edit(content=final_content)

        except Exception as e:
            logger.error(f"Error sending webhook for register command for {ctx.author}: {e}", exc_info=True)
            # Edit placeholder with error message if possible
            if placeholder_message:
                 await placeholder_message.edit(content=f"An error occurred during registration for '{text}', {ctx.author.mention}.")
            else: # Fallback if placeholder wasn't sent (shouldn't happen in this flow)
                 await ctx.send(f"An error occurred during registration for '{text}', {ctx.author.mention}.")
    async def unregister_cmd(self, ctx: commands.Context, full_command_text: str):
        logger.info(f"Attempting to execute unregister_cmd for message: {ctx.message.content}, full_command_text: '{full_command_text}'")
        # Send placeholder message before webhook call
        placeholder_message = await ctx.send(f"Processing unregistration for {ctx.author.mention}...")
        """
        Unregister a user.

        Args:
            ctx: Command context
        """
        logger.info(f"Unregister command from {ctx.author}. Attempting to send webhook...")
        try:
            success, data = await webhook_service.send_webhook(
                ctx, # Pass context for user/channel info extraction
                command="unregister",
                message=full_command_text,
                result={}
            )
            logger.info(f"Webhook send_webhook returned success: {success}, data: {data} for unregister command")
            
            # Check if data is a dictionary and contains 'output'
            # Check if data is a dictionary with 'output' or a list containing one
            output_message = None
            if success and data:
                if isinstance(data, dict) and "output" in data:
                    output_message = str(data["output"])
                    logger.info(f"Webhook for unregister command succeeded for {ctx.author} with dictionary response.")
                elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "output" in data[0]:
                    output_message = str(data[0]["output"])
                    logger.info(f"Webhook for unregister command succeeded for {ctx.author} with list response.")

            # Edit the placeholder message with the final content
            await placeholder_message.edit(content=final_content)

        except Exception as e:
            logger.error(f"Error sending webhook for unregister command for {ctx.author}: {e}", exc_info=True)
            # Edit placeholder with error message if possible
            if placeholder_message:
                 await placeholder_message.edit(content=f"An error occurred during unregistration, {ctx.author.mention}.")
            else: # Fallback if placeholder wasn't sent
                 await ctx.send(f"An error occurred during unregistration, {ctx.author.mention}.")