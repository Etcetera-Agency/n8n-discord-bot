import discord
from discord.ui import Modal, TextInput
from config import logger, Strings
from services import webhook_service, survey_manager
from discord_bot.commands.survey import continue_survey # Import continue_survey

class ConnectsModal(Modal, title="Введіть кількість контактів"):
    connects_input = TextInput(
        label="Кількість connects",
        placeholder="Введіть число (наприклад: 5)",
        min_length=1,
        max_length=3
    )

    def __init__(self, cmd_or_step: str, user_id: str, continue_survey_func):
        super().__init__(timeout=300)
        self.cmd_or_step = cmd_or_step
        self.user_id = user_id
        self.continue_survey_func = continue_survey_func
        logger.debug(f"[{user_id}] ConnectsModal initialized for {cmd_or_step}")

    async def on_submit(self, interaction: discord.Interaction):
        logger.info(f"[{self.user_id}] ConnectsModal submission started")

        try:
            connects = int(self.connects_input.value)
            if connects < 0:
                raise ValueError("Negative value")
            logger.debug(f"[{self.user_id}] Valid connects input: {connects}")
        except ValueError:
            logger.warning(f"[{self.user_id}] Invalid connects input: {self.connects_input.value}")
            await interaction.response.send_message(Strings.INVALID_NUMBER_INPUT, ephemeral=True)
            return

        state = survey_manager.get_survey(self.user_id)
        if not state:
            logger.error(f"[{self.user_id}] No survey state found")
            await interaction.response.send_message(Strings.SURVEY_EXPIRED_OR_NOT_FOUND, ephemeral=True)
            return

        result_payload = {"stepName": self.cmd_or_step, "value": connects}

        success, data = await webhook_service.send_webhook(
            interaction,
            command="survey",
            status="step",
            result=result_payload
        )

        if success:
            state.results[self.cmd_or_step] = connects
            state.next_step()
            logger.info(f"[{self.user_id}] Connects submitted: {connects}")
            await interaction.response.send_message(
                Strings.CONNECTS_SUBMISSION_SUCCESS.format(connects=connects),
                ephemeral=True
            )
            # Call the continue_survey function to proceed to the next step
            await continue_survey(interaction.channel, state)
        else:
            logger.error(f"[{self.user_id}] Webhook failed")
            await interaction.response.send_message(Strings.GENERAL_ERROR, ephemeral=True)