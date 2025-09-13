import discord
from config import Strings
from services.logging_utils import get_logger
from services.survey import survey_manager
from discord_bot.commands.survey import handle_start_daily_survey # Import the survey start handler

class StartSurveyView(discord.ui.View):
    """
    A persistent view for the initial greeting message with the "Гайда" button.
    """
    def __init__(self):
        # Set a timeout of None to make the view persistent
        super().__init__(timeout=None)
        get_logger("view.start_survey").info("initialized (persistent)")

    @discord.ui.button(label=Strings.START_SURVEY_BUTTON, style=discord.ButtonStyle.success, custom_id="start_survey_button")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Callback for the "Гайда" button.
        Initiates the survey flow for the channel if no survey is in progress.
        """
        log = get_logger(
            "view.start_survey",
            {"userId": str(getattr(interaction.user, "id", "")), "channelId": str(getattr(interaction.channel, "id", ""))},
        )
        log.info("button clicked")

        # Defer the interaction immediately
        try:
            await interaction.response.defer(ephemeral=False)
            log.info("interaction deferred")
        except discord.errors.InteractionResponded:
            log.warning("interaction already responded")
            return # Exit if already responded

        channel_id = str(interaction.channel.id)
        user_id = str(interaction.user.id)

        # Check if a survey is already in progress for this channel
        existing_survey = survey_manager.get_survey(channel_id)

        if existing_survey:
            log.info("survey already in progress")
            # Inform the user that a survey is already active
            try:
                await interaction.followup.send(Strings.SURVEY_ALREADY_IN_PROGRESS, ephemeral=True)
            except Exception:
                log.exception("failed to send in-progress notice")
        else:
            log.info("starting new survey")
            # Initiate a new survey flow
            # The session_id can be a combination of channel and user ID for uniqueness per user per channel
            session_id = f"{channel_id}_{user_id}"
            try:
                # Call the handler function to start the survey
                # This function will handle checking channel registration and fetching steps
                await handle_start_daily_survey(interaction.client, user_id, channel_id, session_id) # Pass bot instance, user_id, channel_id, session_id
                get_logger("view.start_survey", {"userId": user_id, "channelId": channel_id, "sessionId": session_id}).info(
                    "start handler invoked"
                )
            except Exception:
                get_logger("view.start_survey", {"userId": user_id, "channelId": channel_id, "sessionId": session_id}).exception(
                    "failed to start survey"
                )
                try:
                    await interaction.followup.send(Strings.SURVEY_START_ERROR, ephemeral=False)
                except Exception:
                    get_logger("view.start_survey", {"userId": user_id, "channelId": channel_id, "sessionId": session_id}).exception(
                        "failed to send error message"
                    )
