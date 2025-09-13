import discord
from discord.ext import commands
from services.webhook import WebhookService
from discord_bot.commands.survey import handle_start_daily_survey as _start_daily_survey
from discord_bot.commands.prefix import PrefixCommands
from discord_bot.commands.slash import setup_slash_cogs
from discord_bot.commands.events import EventHandlers  # Assuming EventHandlers setup is needed
from discord_bot.views.start_survey import StartSurveyView  # Import the new persistent view

###############################################################################
# Logging configuration
###############################################################################
from services.logging_utils import get_logger
logger = get_logger("bot")

###############################################################################
# Load environment variables handled in config/config.py
###############################################################################

###############################################################################
# Global Constants
###############################################################################
###############################################################################
# Response Handler Class
###############################################################################

###############################################################################
# Session and Webhook Helper Functions
###############################################################################

###############################################################################
# Discord Bot Setup
###############################################################################
# --- MOVED FROM bot/client.py START ---
# Set up intents
intents = discord.Intents.default()
intents.message_content = True

# Create bot instance
async def get_custom_prefix(bot, message):
    """Determines the command prefix based on message content."""
    prefixes = ["!"]
    if bot.user in message.mentions:
        prefixes.append(f"<@{bot.user.id}> ") # Add mention as a prefix (with space)
        prefixes.append(f"<@!{bot.user.id}> ") # Add mention with nickname as a prefix (with space)
    return commands.when_mentioned_or(*prefixes)(bot, message) # Use when_mentioned_or to handle mentions and other prefixes

# Create bot instance
bot = commands.Bot(command_prefix=get_custom_prefix, intents=intents)

# Initialize webhook service; no async init required
bot.webhook_service = WebhookService()

# Import command handlers

# Register commands and event handlers
prefix_commands = PrefixCommands(bot)
event_handlers = EventHandlers(bot)
# event_handlers.setup() # Call setup if EventHandlers class requires it

# Removed registration of SurveyButtonView as it seems unused/incorrectly referenced
# Register the persistent view for the start survey button

logger.info("Bot instance created and handlers initialized in bot.py")
# --- MOVED FROM bot/client.py END ---

###############################################################################
# Survey Management
##############################################################################


# Removed old ask_dynamic_step and finish_survey definitions here
# They are now imported from discord_bot.commands.survey

###############################################################################
# UI Component Factory
##############################################################################

###############################################################################
###############################################################################
# Discord Events
#############################################################################
@bot.event
async def on_ready():
    get_logger("bot.on_ready").info("connected", extra={"bot_user": str(bot.user)})
    get_logger("bot.on_ready").info("prefix commands registered")
    bot.add_view(StartSurveyView())
    get_logger("bot.on_ready").info("persistent views added")
    # Note: Slash commands are synced separately, usually in on_ready or a setup cog
    # Load slash command cogs
    try:
        await setup_slash_cogs(bot)
        await bot.tree.sync()
        get_logger("bot.on_ready").info("slash cogs loaded and tree synced")
    except Exception:
        get_logger("bot.on_ready").exception("failed to load slash cogs")

    # Survey continuation handled in Discord handlers; no initializer required

@bot.event
async def on_close():
    get_logger("bot.on_close").info("shutting down, cleaning up resources")
    # Add any necessary cleanup here

###############################################################################
###############################################################################
###############################################################################
# Discord on_message Event
###########################################################################
@bot.event # Re-added @bot.event decorator
async def on_message(message: discord.Message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    # Handle messages where the bot is mentioned
    if bot.user in message.mentions:
        logger.info(f"Bot mentioned on_message: {message.content}")
        logger.info("Bot mentioned in message, attempting to parse command...")

        # Extract content after the mention
        # Find the position after the bot mention
        mention_index = message.content.find(f"<@{bot.user.id}>")
        if mention_index == -1:
             mention_index = message.content.find(f"<@!{bot.user.id}>")

        if mention_index != -1:
            # Adjust slice to account for the length of the mention string found
            mention_string_length = len(f"<@{bot.user.id}>") if message.content[mention_index:].startswith(f"<@{bot.user.id}>") else len(f"<@!{bot.user.id}>")
            content_after_mention = message.content[mention_index + mention_string_length:].strip()

            # Check for known commands after the mention
            if content_after_mention.startswith("!unregister"):
                logger.info(f"Identified !unregister command after mention. Full content after mention: '{content_after_mention}'")
                # Manually create a Context object
                ctx = await bot.get_context(message)
                logger.info("Calling prefix_commands.unregister_cmd(ctx)...")
                # Call the unregister command handler directly
                # Assuming prefix_commands instance is accessible in this scope
                await prefix_commands.unregister_cmd(ctx, full_command_text=content_after_mention)
                logger.info("unregister_cmd handler called.")
                return # Exit after handling the command

            elif content_after_mention.startswith("!register"):
                 logger.info(f"Identified !register command after mention. Full content after mention: '{content_after_mention}'")
                 # Extract text argument after "!register"
                 text_after_command = content_after_mention[len("!register"):].strip()
                 logger.info(f"Extracted text after !register: '{text_after_command}'")

                 # Manually create a Context object
                 ctx = await bot.get_context(message)
                 logger.info("Calling prefix_commands.register_cmd(ctx, text=text_after_command)...")
                 # Call the register command handler directly, passing the extracted text and full command text
                 await prefix_commands.register_cmd(ctx, full_command_text=content_after_mention, text=text_after_command) # Pass text and full_command_text as keyword arguments
                 logger.info("register_cmd handler called.")
                 return # Exit after handling the command

            else:
                # If mentioned but no known command follows, proceed with generic mention handling
                logger.info("Bot mentioned but no known command found, proceeding with generic mention handling using send-and-edit.")
                # Send initial placeholder message
                placeholder_message = await message.channel.send(f"Processing your mention, {message.author.mention}...")

                # Process the message (send webhook for mention)
                try:
                    # Note: Pass the original message or relevant parts to the webhook service
                    # Assuming webhook_service can handle the original message object or needs specific data extracted from it.
                    # If it specifically needs a Context object, this approach needs rethinking.
                    # Let's assume it can work with the message object for now.
                    success, data = await bot.webhook_service.send_webhook(
                        message, # Pass original message object
                        command="mention",
                        message=content_after_mention, # Use content after mention
                        result={}
                    )

                    # Determine the final response message content
                    final_content = None
                    if success and data:
                         if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "output" in data[0]:
                             final_content = str(data[0]["output"])
                         elif isinstance(data, dict) and "output" in data: # Handle direct dict response too
                             final_content = str(data["output"])
                         else:
                             # Fallback if structure is unexpected but success=True
                             logger.warning(f"Mention webhook succeeded but response format unexpected: {data}")
                             final_content = f"Processed mention, {message.author.mention}." # Generic success message

                    elif success: # Success but no specific output message
                         final_content = f"Processed mention, {message.author.mention}."
                    else: # Failure case
                         logger.warning(f"Webhook for mention failed. Success: {success}, Data: {data}")
                         # Include the 404 error detail if possible, assuming data might contain error info
                         error_detail = f" (Error: {data})" if data else ""
                         final_content = f"Sorry, {message.author.mention}, I couldn't process that mention.{error_detail}"

                    # Edit the placeholder message with the final content
                    await placeholder_message.edit(content=final_content)

                except Exception as e:
                     logger.error(f"Error handling generic mention for {message.author}: {e}", exc_info=True)
                     # Edit the placeholder message with an error message
                     await placeholder_message.edit(content=f"An error occurred while processing your mention, {message.author.mention}.")
        else:
             # This case should ideally not happen if bot.user in message.mentions is true,
             # but as a fallback
             logger.warning("Bot mentioned but mention string not found in message content.")
             # Optionally handle as generic mention or ignore

        # Handle other specific message types (if not a mention handled above)
        logger.info(f"Checking for specific message types (start_daily_survey, etc.) for message: {message.content}")
        if message.content.startswith("start_daily_survey"):
            logger.info(f"Identified start_daily_survey command for message: {message.content}")
            parts = message.content.split()
            if len(parts) >= 4:
                user_id = parts[1]
                channel_id = parts[2]
                # Build a session id and delegate to canonical starter
                session_id = f"{channel_id}_{user_id}"
                await _start_daily_survey(bot, user_id, channel_id, session_id)

        # Any other general message handling that should happen for non-mention messages would go here.
        # Currently, no other general message handling is needed based on the original code structure.
        pass
# Any other general message handling that should happen for non-command, non-mention messages would go here.



###############################################################################
# Note: Startup is centralized in main.py. bot.py now only defines the bot.
###############################################################################
