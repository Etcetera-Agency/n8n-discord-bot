import discord
from discord.ext import commands
from services import webhook_service
from services.logging_utils import get_logger

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
        get_logger("cmd.prefix").info("init")
        self.bot = bot
        # Removed self.register_commands() as commands are now methods

    async def register_cmd(self, ctx: commands.Context, full_command_text: str, text: str = ""):
        payload = {"userId": str(ctx.author.id), "channelId": str(ctx.channel.id), "sessionId": f"{ctx.channel.id}_{ctx.author.id}"}
        log = get_logger("cmd.prefix.register", payload)
        log.info("entered", extra={"full_text": full_command_text, "text": text})
        log.info("channel", extra={"channel_name": ctx.channel.name})
        # await ctx.defer() # Defer only if proceeding to webhook

        if not text:
            log.info("empty text arg")
            # Use ctx.send for immediate error feedback, no defer needed here.
            await ctx.send("Потрібний формат !register Name Surname as in Team Directory")
            log.warning("missing text argument")
            return

        # Grant channel permissions before webhook call
        try:
            log.info("attempting to set permissions")
            # Set all permissions to True by default, then explicitly set excluded ones to False
            log.info("creating PermissionOverwrite")
            overwrite = discord.PermissionOverwrite()
            log.info("setting permissions on overwrite")

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

            log.info("calling set_permissions")
            await ctx.channel.set_permissions(ctx.author, overwrite=overwrite)
            log.info("granted permissions", extra={"channel": ctx.channel.name})

            # Make the channel private by denying read_messages for @everyone
            try:
                log.info("making channel private", extra={"channel": ctx.channel.name})
                await ctx.channel.set_permissions(ctx.guild.default_role, read_messages=False)
                log.info("made channel private")
            except discord.Forbidden:
                log.error("no permission to set @everyone perms")
            except discord.HTTPException as e:
                log.exception("http error setting @everyone perms")

        except discord.Forbidden:
            log.error("no permission to set perms for author")
            # permission_granted remains False
        except discord.HTTPException as e:
            log.exception("http error setting perms for author")
            # permission_granted remains False
        except Exception as e:
            log.exception("unexpected error setting perms for author")
            # permission_granted remains False

        # Send placeholder message before webhook call
        placeholder_message = await ctx.send(f"Registering {ctx.author.mention}...")

        """
        Register a user with the given text.

        Args:
            ctx: Command context
            text: Registration text (extracted manually)
        """
        log.info("sending webhook", extra={"author": str(ctx.author), "text": text})
        try:
            success, data = await webhook_service.send_webhook(
                ctx, # Pass context for user/channel info extraction
                command="register",
                message=full_command_text,
                result={"text": text}
            )
            log.info("webhook returned", extra={"success": success})
            # Check if data is a dictionary and contains 'output'
            # Check if data is a dictionary with 'output' or a list containing one
            output_message = None
            if success and data:
                if isinstance(data, dict) and "output" in data:
                    output_message = str(data["output"])
                    log.info("webhook success: dict response")
                elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "output" in data[0]:
                    output_message = str(data[0]["output"])
                    log.info("webhook success: list response")

            # Determine final content based on webhook result
            webhook_status_message = None
            if output_message:
               webhook_status_message = output_message
            elif success:
               log.info("webhook success but no output")
               webhook_status_message = f"Registration attempt for '{text}' processed, {ctx.author.mention}."
            else:
               log.warning("webhook failed", extra={"success": success})
               error_detail = f" (Error: {data})" if data else ""
               webhook_status_message = f"Registration attempt for '{text}' failed, {ctx.author.mention}.{error_detail}"

            # Set final content to webhook status message
            final_content = webhook_status_message
            await placeholder_message.edit(content=final_content)

        except Exception as e:
            log.exception("error sending webhook")
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
