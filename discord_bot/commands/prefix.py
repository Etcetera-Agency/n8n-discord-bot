import discord
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

        # Grant channel permissions before webhook call
        permission_granted = False # Initialize as False
        try:
            logger.info("Attempting to set permissions...")
            # Set all permissions to True by default, then explicitly set excluded ones to False
            logger.info("Creating PermissionOverwrite object...")
            overwrite = discord.PermissionOverwrite()
            logger.info("PermissionOverwrite object created. Setting permissions...")

            # Explicitly set excluded permissions to False
            overwrite.manage_channels = False
            overwrite.manage_roles = False
            overwrite.manage_permissions = False
            overwrite.manage_webhooks = False
            overwrite.manage_messages = False
            overwrite.create_public_threads = False
            overwrite.create_private_threads = False
            overwrite.send_messages_in_threads = False
            overwrite.manage_threads = False

            # Set desired permissions to True (all others not explicitly set to False)
            overwrite.read_messages = True
            overwrite.send_messages = True
            overwrite.send_tts_messages = True
            overwrite.embed_links = True
            overwrite.attach_files = True
            overwrite.read_message_history = True
            overwrite.mention_everyone = True
            overwrite.use_external_emojis = True
            overwrite.add_reactions = True
            # Add any other permissions that should be True here

            logger.info("Permissions set in overwrite object. Calling set_permissions...")
            await ctx.channel.set_permissions(ctx.author, overwrite=overwrite)
            logger.info(f"Successfully granted specific permissions to {ctx.author} in channel {ctx.channel.name}")
            permission_granted = True
        except discord.Forbidden:
            logger.error(f"Bot lacks permissions to set permissions for {ctx.author} in channel {ctx.channel.name}")
            # permission_granted remains False
        except discord.HTTPException as e:
            logger.error(f"HTTP error setting permissions for {ctx.author} in channel {ctx.channel.name}: {e}")
            # permission_granted remains False
        except Exception as e:
            logger.error(f"Unexpected error setting permissions for {ctx.author} in channel {ctx.channel.name}: {e}", exc_info=True)
            # permission_granted remains False

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

            # Determine final content based on webhook result
            webhook_status_message = None
            if output_message:
               webhook_status_message = output_message
            elif success:
               logger.info(f"Webhook succeeded but no valid output found in response from {ctx.author}")
               webhook_status_message = f"Registration attempt for '{text}' processed, {ctx.author.mention}."
            else:
               logger.warning(f"Webhook for register command failed for {ctx.author}. Success: {success}, Data: {data}")
               error_detail = f" (Error: {data})" if data else ""
               webhook_status_message = f"Registration attempt for '{text}' failed, {ctx.author.mention}.{error_detail}"

            # Determine permission status message
            permission_status_message = ""
            if permission_granted:
                permission_status_message = f" You have been granted access to this channel."
            else:
                permission_status_message = f" Failed to grant access to this channel (check bot permissions)."

            # Set final content to webhook status message
            final_content = webhook_status_message
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

            # Determine final content based on webhook result
            final_content = None
            if output_message:
               final_content = output_message
            elif success:
               logger.info(f"Webhook succeeded but no valid output found in response from {ctx.author}")
               final_content = f"Unregistration attempt processed, {ctx.author.mention}."
            else:
               logger.warning(f"Webhook for unregister command failed for {ctx.author}. Success: {success}, Data: {data}")
               error_detail = f" (Error: {data})" if data else ""
               final_content = f"Unregistration attempt failed, {ctx.author.mention}.{error_detail}"

            # Edit the placeholder message with the final content
            await placeholder_message.edit(content=final_content)

        except Exception as e:
            logger.error(f"Error sending webhook for unregister command for {ctx.author}: {e}", exc_info=True)
            # Edit placeholder with error message if possible
            if placeholder_message:
                 await placeholder_message.edit(content=f"An error occurred during unregistration, {ctx.author.mention}.")
            else: # Fallback if placeholder wasn't sent
                 await ctx.send(f"An error occurred during unregistration, {ctx.author.mention}.")