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
        self.register_commands()
        
    def register_commands(self) -> None:
        """Register all prefix commands."""
        
        @self.bot.command(name="register", help="Використання: !register <будь-який текст>")
        # Remove text argument from signature to handle manually
        async def register_cmd(ctx: commands.Context):
            logger.info(f"register_cmd function entered for message: {ctx.message.content}") # Added log at function start
            # Manually extract text after the command name, considering mentions
            prefix = self.bot.command_prefix
            command_name = "register"
            message_content = ctx.message.content

            # Find the index of the command name after the prefix
            prefix_command_index = message_content.lower().find(f"{prefix}{command_name}")
            if prefix_command_index == -1:
                # This should not happen if the command was triggered, but as a fallback
                text = ""
            else:
                # Extract text after the command name and any trailing whitespace
                text_start_index = prefix_command_index + len(prefix) + len(command_name)
                text = message_content[text_start_index:].strip()

            logger.info(f"Attempting to execute register_cmd with extracted text: '{text}' from {ctx.author}") # Updated log

            if not text: # This check now correctly handles empty extracted text
                logger.info(f"Extracted text argument is empty for register command from {ctx.author}. Sending usage message.")
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
                # Assuming send_webhook returns a boolean or status indicator
                success, data = await webhook_service.send_webhook( # Modified to capture data
                    ctx,
                    command="register",
                    result={"text": text}
                )
                logger.info(f"Webhook send_webhook returned success: {success}, data type: {type(data)}, data: {data}") # Added log to inspect data type and content
                if success and data: # Simplified check
                   logger.info(f"Simplified send condition met for {ctx.author}. Attempting to send data: {data}") # Added log for simplified check
                   # Attempt to send the data received, regardless of its exact structure
                   # This might need further refinement based on the actual data structure
                   if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "output" in data[0]:
                        await ctx.send(data[0]["output"])
                   else:
                        await ctx.send(f"Received data from n8n but could not extract output: {data}") # Send raw data if structure is unexpected
                elif success:
                   logger.info(f"Webhook for register command sent successfully for {ctx.author}. No data received from n8n.") # Updated log message
                   await ctx.send(f"Registration attempt for '{text}' sent successfully, but no specific response from n8n.") # Default success message if no output
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