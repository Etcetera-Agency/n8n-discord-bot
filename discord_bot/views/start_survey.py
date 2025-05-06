import discord
from discord.ext import commands
from config import logger, Strings
from services.survey import survey_manager
from discord_bot.commands.survey import handle_start_daily_survey # Import the survey start handler

class StartSurveyView(discord.ui.View):
    """
    A persistent view for the initial greeting message with the "Гайда" button.
    """
    def __init__(self):
        # Set a timeout of None to make the view persistent
        super().__init__(timeout=None)
        logger.info("StartSurveyView initialized (persistent)")

    @discord.ui.button(label=Strings.START_SURVEY_BUTTON, style=discord.ButtonStyle.success, custom_id="start_survey_button")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Callback for the "Гайда" button.
        Initiates the survey flow for the channel if no survey is in progress.
        """
        logger.info(f"Start survey button clicked by {interaction.user} in channel {interaction.channel.id}")

        # Defer the interaction immediately
        try:
            await interaction.response.defer(ephemeral=False)
            logger.info("Interaction deferred.")
        except discord.errors.InteractionResponded:
            logger.warning("Interaction was already responded to.")
            return # Exit if already responded

        channel_id = str(interaction.channel.id)
        user_id = str(interaction.user.id)

        # Check if a survey is already in progress for this channel
        existing_survey = survey_manager.get_survey(channel_id)

        if existing_survey:
            logger.info(f"Survey already in progress for channel {channel_id}. User: {user_id}")
            # Inform the user that a survey is already active
            try:
                await interaction.followup.send(Strings.SURVEY_ALREADY_IN_PROGRESS, ephemeral=True)
            except Exception as e:
                logger.error(f"Failed to send followup message about existing survey: {e}")
        else:
            logger.info(f"No active survey found for channel {channel_id}. Initiating new survey for user {user_id}.")
            # Initiate a new survey flow
            # The session_id can be a combination of channel and user ID for uniqueness per user per channel
            session_id = f"{channel_id}_{user_id}"
            try:
                # Call the handler function to start the survey
                # This function will handle checking channel registration and fetching steps
                await handle_start_daily_survey(interaction.client, user_id, channel_id, session_id) # Pass bot instance, user_id, channel_id, session_id
                logger.info(f"handle_start_daily_survey called for channel {channel_id}, user {user_id}")
            except Exception as e:
                logger.error(f"Error initiating survey for channel {channel_id}, user {user_id}: {e}", exc_info=True)
                try:
                    await interaction.followup.send(Strings.SURVEY_START_ERROR, ephemeral=False)
                except Exception as send_error:
                    logger.error(f"Failed to send error message after survey initiation failure: {send_error}")