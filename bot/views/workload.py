import discord
from typing import Optional
from config import ViewType, logger
from services import survey_manager
from config.constants import WORKLOAD_OPTIONS
import asyncio

class WorkloadButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, cmd_or_step: str):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=label,
            custom_id=custom_id
        )
        self.cmd_or_step = cmd_or_step
        
    async def callback(self, interaction: discord.Interaction):
        # Comprehensive interaction validation
        if (not interaction or
            not isinstance(interaction, discord.Interaction) or
            not hasattr(interaction, 'response') or
            not hasattr(interaction, 'user')):
            logger.error(f"Invalid interaction object: {type(interaction)}")
            return
            
        from services import webhook_service
        view = self.view
        if isinstance(view, WorkloadView):
            # First, acknowledge the interaction to prevent timeout
            try:
                if not interaction.response.is_done():
                    await interaction.response.defer(ephemeral=False)
            except Exception as e:
                logger.error(f"Interaction response error: {e}")
                return
            
            logger.info(f"Workload button clicked: {self.label} by user {view.user_id} for step {view.cmd_or_step}")
            
            # Add processing reaction to command message
            if view.command_msg:
                await view.command_msg.add_reaction("⏳")
                logger.info(f"Added processing reaction to command message {view.command_msg.id}")
            
            try:
                # Set value based on button label and convert to integer
                value = 0 if self.label == "Нічого немає" else int(self.label)
                logger.info(f"Parsed value: {value} from label: {self.label}")
                
                if view.has_survey:
                    logger.info(f"Processing as survey step for user {view.user_id}")
                    # Dynamic survey flow
                    state = survey_manager.get_survey(view.user_id)
                    if not state:
                        logger.error(f"Survey not found for user {view.user_id}")
                        if view.command_msg:
                            await view.command_msg.remove_reaction("⏳", interaction.client.user)
                            error_msg = "Ваш запит: Вибір навантаження\nПомилка: Опитування не знайдено."
                            await view.command_msg.edit(content=error_msg)
                            await view.command_msg.add_reaction("❌")
                        if view.buttons_msg:
                            await view.buttons_msg.delete()
                        return
                    
                    logger.info(f"Found survey for user {view.user_id}, current step: {state.current_step()}")
                    
                    # Send webhook for survey step
                    success, data = await webhook_service.send_webhook(
                        interaction,
                        command="survey",
                        status="step",
                        result={
                            "stepName": view.cmd_or_step,
                            "value": value
                        }
                    )
                    
                    logger.info(f"Webhook response for survey step: success={success}, data={data}")
                    
                    if not success:
                        logger.error(f"Failed to send webhook for survey step: {view.cmd_or_step}")
                        if view.command_msg:
                            await view.command_msg.remove_reaction("⏳", interaction.client.user)
                            error_msg = f"Ваш запит: Навантаження = {value}\nПомилка: Не вдалося виконати крок опитування."
                            await view.command_msg.edit(content=error_msg)
                            await view.command_msg.add_reaction("❌")
                        if view.buttons_msg:
                            await view.buttons_msg.delete()
                        return
                    
                    # Update survey state
                    state.results[view.cmd_or_step] = value
                    logger.info(f"Updated survey results: {state.results}")
                    
                    # Update command message with success
                    if view.command_msg:
                        await view.command_msg.remove_reaction("⏳", interaction.client.user)
                        await view.command_msg.edit(content=f"Дякую! Навантаження: {value} годин записано.")
                        logger.info(f"Updated command message with success")
                    
                    # Delete buttons message
                    if view.buttons_msg:
                        await view.buttons_msg.delete()
                        logger.info(f"Deleted buttons message")
                    
                    # Log survey state before continuation
                    logger.info(f"Survey state before continuation - current step: {state.current_step()}, results: {state.results}")
                    
                    # Let n8n handle the survey continuation through webhook response
                    # Don't advance the step here, as it will be handled by the webhook service
                    # But verify we have a valid state for continuation
                    if not state or not state.user_id:
                        logger.error("Invalid survey state for continuation")
                        return
                    
                else:
                    logger.info(f"Processing as regular command: {view.cmd_or_step}")
                    # Regular slash command
                    success, data = await webhook_service.send_webhook(
                        interaction,
                        command=view.cmd_or_step,
                        status="ok",
                        result={"workload": value}
                    )
                    
                    logger.info(f"Webhook response for command: success={success}, data={data}")
                    
                    if success and data and "output" in data:
                        # Update command message with success
                        if view.command_msg:
                            await view.command_msg.remove_reaction("⏳", interaction.client.user)
                            await view.command_msg.edit(content=data["output"])
                            logger.info(f"Updated command message with success: {data['output']}")
                        
                        # Delete buttons message
                        if view.buttons_msg:
                            await view.buttons_msg.delete()
                            logger.info(f"Deleted buttons message")
                    else:
                        logger.error(f"Failed to send webhook for command: {view.cmd_or_step}")
                        if view.command_msg:
                            await view.command_msg.remove_reaction("⏳", interaction.client.user)
                            error_msg = f"Ваш запит: Навантаження = {value}\nПомилка: Не вдалося виконати команду."
                            await view.command_msg.edit(content=error_msg)
                            await view.command_msg.add_reaction("❌")
                        if view.buttons_msg:
                            await view.buttons_msg.delete()
                        
            except Exception as e:
                logger.error(f"Error in workload button: {e}")
                if view.command_msg:
                    await view.command_msg.remove_reaction("⏳", interaction.client.user)
                    error_msg = f"Ваш запит: Навантаження = {self.label}\nПомилка: Сталася неочікувана помилка."
                    await view.command_msg.edit(content=error_msg)
                    await view.command_msg.add_reaction("❌")
                if view.buttons_msg:
                    await view.buttons_msg.delete()

class WorkloadView(discord.ui.View):
    def __init__(self, cmd_or_step: str, user_id: str, has_survey: bool = False):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cmd_or_step = cmd_or_step
        self.user_id = user_id
        self.has_survey = has_survey
        self.command_msg = None  # Reference to the command message
        self.buttons_msg = None  # Reference to the buttons message
        
    async def on_timeout(self):
        logger.warning(f"WorkloadView timed out for user {self.user_id}")
        if self.buttons_msg:
            try:
                await self.buttons_msg.delete()
            except Exception as e:
                logger.error(f"Error deleting buttons message on timeout: {e}")

def create_workload_view(
    cmd_or_step: str,
    user_id: str,
    timeout: Optional[float] = None,
    has_survey: bool = False
) -> WorkloadView:
    """Create a workload view with buttons."""
    view = WorkloadView(cmd_or_step, user_id, has_survey=has_survey)
    
    # Add workload buttons
    for hour in WORKLOAD_OPTIONS:
        custom_id = f"workload_button_{hour}_{cmd_or_step}_{user_id}"
        button = WorkloadButton(label=hour, custom_id=custom_id, cmd_or_step=cmd_or_step)
        view.add_item(button)
    
    return view 