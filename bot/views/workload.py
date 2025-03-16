import discord
from typing import Optional, List
from config import ViewType, logger
from services import survey_manager
import asyncio

class WorkloadButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, cmd_or_step: str):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=label,
            custom_id=custom_id
        )
        self.cmd_or_step = cmd_or_step
        
    async def callback(self, interaction: discord.Interaction):
        from services import webhook_service
        
        # First, acknowledge the interaction to prevent timeout
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=False)
        
        # Get the original message
        message = interaction.message
        if message:
            # Add processing reaction
            await message.add_reaction("⏳")
        
        try:
            # Determine the value based on the button label
            value = "0" if self.label == "Нічого немає" else self.label
            
            # Handle different command types
            if "workload_today" in self.cmd_or_step or "workload_nextweek" in self.cmd_or_step:
                # This is a slash command - send the actual command result
                success, data = await webhook_service.send_webhook(
                    interaction,
                    command=self.cmd_or_step,
                    status="ok",
                    result={"value": value}
                )
                
                if message:
                    # Remove processing reaction
                    await message.remove_reaction("⏳", interaction.client.user)
                
                if success and data and "output" in data:
                    if message:
                        # Add success reaction before deleting
                        await message.add_reaction("✅")
                        await asyncio.sleep(1)
                        await message.delete()
                    await interaction.followup.send(data["output"])
                else:
                    error_msg = f"Ваш запит: Навантаження = {self.label}\nПомилка: Не вдалося виконати команду."
                    if message:
                        await message.edit(content=error_msg)
                        await message.add_reaction("❌")
                    else:
                        await interaction.followup.send(error_msg)
                        
            elif not any(cmd in self.cmd_or_step for cmd in ["survey", "workload_today", "workload_nextweek"]):
                # This is a mention-based interaction - send button_pressed
                success, data = await webhook_service.send_webhook(
                    interaction,
                    command="button_pressed",
                    status="ok",
                    result={
                        "label": self.label,
                        "custom_id": self.custom_id,
                        "value": value
                    }
                )
                
                if message:
                    # Remove processing reaction
                    await message.remove_reaction("⏳", interaction.client.user)
                
                if success and data and "output" in data:
                    if message:
                        # Add success reaction before deleting
                        await message.add_reaction("✅")
                        await asyncio.sleep(1)
                        await message.delete()
                    await interaction.followup.send(data["output"])
                else:
                    error_msg = f"Ваш запит: Навантаження = {self.label}\nПомилка: Не вдалося виконати команду."
                    if message:
                        await message.edit(content=error_msg)
                        await message.add_reaction("❌")
                    else:
                        await interaction.followup.send(error_msg)
            
            # For survey steps
            else:
                # Get survey state
                state = survey_manager.get_survey(view.user_id)
                if not state:
                    if message:
                        await message.remove_reaction("⏳", interaction.client.user)
                        error_msg = f"Ваш запит: Навантаження = {self.label}\nПомилка: Опитування не знайдено."
                        await message.edit(content=error_msg)
                        await message.add_reaction("❌")
                    return
                
                # Send webhook for survey step
                success, data = await webhook_service.send_webhook(
                    interaction,
                    command="survey",
                    status="step",
                    result={
                        "stepName": self.cmd_or_step,
                        "workload": value
                    }
                )
                
                if message:
                    # Remove processing reaction
                    await message.remove_reaction("⏳", interaction.client.user)
                
                if not success:
                    error_msg = f"Ваш запит: Навантаження = {self.label}\nПомилка: Не вдалося виконати крок опитування."
                    if message:
                        await message.edit(content=error_msg)
                        await message.add_reaction("❌")
                    return
                
                # Update survey state
                state.results[self.cmd_or_step] = value
                state.next_step()
                next_step = state.current_step()
                
                if message:
                    # Show success reaction
                    await message.add_reaction("✅")
                
                # Continue survey
                if next_step:
                    from bot.commands.survey import ask_dynamic_step
                    await ask_dynamic_step(interaction.channel, state, next_step)
                else:
                    from bot.commands.survey import finish_survey
                    await finish_survey(interaction.channel, state)
                    
        except Exception as e:
            logger.error(f"Error in workload button: {e}")
            if message:
                await message.remove_reaction("⏳", interaction.client.user)
                error_msg = f"Ваш запит: Навантаження = {self.label}\nПомилка: Сталася неочікувана помилка."
                await message.edit(content=error_msg)
                await message.add_reaction("❌")

class WorkloadView(discord.ui.View):
    def __init__(self, timeout: Optional[float] = 180):
        super().__init__(timeout=timeout)

def create_workload_view(
    cmd_or_step: str,
    user_id: str,
    timeout: Optional[float] = None,
    has_survey: bool = False
) -> WorkloadView:
    """Create a workload view with buttons."""
    view = WorkloadView(timeout=timeout)
    
    # Add workload buttons
    buttons = [
        ("0", "Нічого немає"),
        ("1-10", "1-10"),
        ("11-20", "11-20"),
        ("21-30", "21-30"),
        ("31-40", "31-40"),
        ("40+", "40+")
    ]
    
    for value, label in buttons:
        custom_id = f"workload_button_{value}_{cmd_or_step}_{user_id}"
        button = WorkloadButton(label=label, custom_id=custom_id, cmd_or_step=cmd_or_step)
        view.add_item(button)
    
    return view 