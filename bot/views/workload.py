import discord
from typing import Optional
from config import ViewType, logger
from services import survey_manager
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
        from services import webhook_service
        view = self.view
        if isinstance(view, WorkloadView):
            # First, acknowledge the interaction to prevent timeout
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)
            
            # Add processing reaction to command message
            if view.command_msg:
                await view.command_msg.add_reaction("⏳")
            
            try:
                # Set value based on button label
                value = "0" if self.label == "Нічого немає" else self.label
                
                if view.has_survey:
                    # Dynamic survey flow
                    state = survey_manager.get_survey(view.user_id)
                    if not state:
                        if view.command_msg:
                            await view.command_msg.remove_reaction("⏳", interaction.client.user)
                            error_msg = "Ваш запит: Вибір навантаження\nПомилка: Опитування не знайдено."
                            await view.command_msg.edit(content=error_msg)
                            await view.command_msg.add_reaction("❌")
                        if view.buttons_msg:
                            await view.buttons_msg.delete()
                        return
                    
                    # Send webhook for survey step
                    success, data = await webhook_service.send_webhook(
                        interaction,
                        command="survey",
                        status="step",
                        result={
                            "stepName": view.cmd_or_step,
                            "workload": value
                        }
                    )
                    
                    if not success:
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
                    state.next_step()
                    next_step = state.current_step()
                    
                    # Update command message with success
                    if view.command_msg:
                        await view.command_msg.remove_reaction("⏳", interaction.client.user)
                        await view.command_msg.edit(content=f"Дякую! Навантаження: {value} годин записано.")
                        await view.command_msg.add_reaction("✅")
                    
                    # Delete buttons message
                    if view.buttons_msg:
                        await view.buttons_msg.delete()
                    
                    # Continue survey
                    if next_step:
                        from bot.commands.survey import ask_dynamic_step
                        await ask_dynamic_step(interaction.channel, state, next_step)
                    else:
                        from bot.commands.survey import finish_survey
                        await finish_survey(interaction.channel, state)
                        
                else:
                    # Regular slash command
                    success, data = await webhook_service.send_webhook(
                        interaction,
                        command=view.cmd_or_step,
                        status="ok",
                        result={"value": value}
                    )
                    
                    if success and data and "output" in data:
                        # Update command message with success
                        if view.command_msg:
                            await view.command_msg.remove_reaction("⏳", interaction.client.user)
                            await view.command_msg.edit(content=data["output"])
                            await view.command_msg.add_reaction("✅")
                        
                        # Delete buttons message
                        if view.buttons_msg:
                            await view.buttons_msg.delete()
                    else:
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
        super().__init__()
        self.cmd_or_step = cmd_or_step
        self.user_id = user_id
        self.has_survey = has_survey
        self.command_msg = None  # Reference to the command message
        self.buttons_msg = None  # Reference to the buttons message

def create_workload_view(
    cmd_or_step: str,
    user_id: str,
    timeout: Optional[float] = None,
    has_survey: bool = False
) -> WorkloadView:
    """Create a workload view with buttons."""
    view = WorkloadView(cmd_or_step, user_id, has_survey=has_survey)
    
    # Add workload buttons
    hours = ["Нічого немає", "20", "30", "40"]
    for hour in hours:
        custom_id = f"workload_button_{hour}_{cmd_or_step}_{user_id}"
        button = WorkloadButton(label=hour, custom_id=custom_id, cmd_or_step=cmd_or_step)
        view.add_item(button)
    
    return view 