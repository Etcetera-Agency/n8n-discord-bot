import discord
from typing import Optional, List
import datetime
from config import ViewType, logger
from services import survey_manager
import asyncio

class DayOffButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, cmd_or_step: str):
        super().__init__(
            style=discord.ButtonStyle.secondary,  # Start with gray color
            label=label,
            custom_id=custom_id
        )
        self.cmd_or_step = cmd_or_step
        self.is_selected = False
        
    async def callback(self, interaction: discord.Interaction):
        # First, acknowledge the interaction to prevent timeout
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=False)
        
        # Get the original message
        message = interaction.message
        if message:
            # Add processing reaction
            await message.add_reaction("⏳")
            
        try:
            # Toggle selection
            self.is_selected = not self.is_selected
            self.style = discord.ButtonStyle.primary if self.is_selected else discord.ButtonStyle.secondary
            
            # Get parent view and update selected days
            view = self.view
            if isinstance(view, DayOffView):
                if self.is_selected:
                    view.selected_days.append(self.label)
                else:
                    view.selected_days.remove(self.label)
            
            # Update the message with the new button states
            await interaction.message.edit(view=self.view)
            
            # Show success reaction for survey steps
            if message:
                await message.remove_reaction("⏳", interaction.client.user)
                await message.add_reaction("✅")
                
        except Exception as e:
            logger.error(f"Error in day off button: {e}")
            if message:
                await message.remove_reaction("⏳", interaction.client.user)
                error_msg = f"Ваш запит: Вибір дня {self.label}\nПомилка: Сталася неочікувана помилка."
                await message.edit(content=error_msg)
                await message.add_reaction("❌")

class ConfirmButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Підтверджую",
            row=4  # Put in the last row
        )
        
    async def callback(self, interaction: discord.Interaction):
        from services import webhook_service
        view = self.view
        if isinstance(view, DayOffView):
            # First, acknowledge the interaction to prevent timeout
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)
            
            # Get the original message
            message = interaction.message
            if message:
                # Add processing reaction
                await message.add_reaction("⏳")
            
            # Sort days according to weekday_map
            sorted_days = sorted(view.selected_days, 
                               key=lambda x: view.weekday_map[x])
            
            try:
                if view.has_survey:
                    # Dynamic survey flow
                    state = survey_manager.get_survey(view.user_id)
                    if not state:
                        if message:
                            await message.remove_reaction("⏳", interaction.client.user)
                            error_msg = "Ваш запит: Підтвердження вихідних\nПомилка: Опитування не знайдено."
                            await message.edit(content=error_msg)
                            await message.add_reaction("❌")
                        return
                    
                    # Send webhook for survey step
                    success, data = await webhook_service.send_webhook(
                        interaction,
                        command="survey",
                        status="step",
                        result={
                            "stepName": view.cmd_or_step,
                            "daysSelected": sorted_days
                        }
                    )
                    
                    if message:
                        # Remove processing reaction
                        await message.remove_reaction("⏳", interaction.client.user)
                    
                    if not success:
                        error_msg = f"Ваш запит: Вихідні дні = {', '.join(sorted_days)}\nПомилка: Не вдалося виконати крок опитування."
                        if message:
                            await message.edit(content=error_msg)
                            await message.add_reaction("❌")
                        return
                    
                    # Update survey state
                    state.results[view.cmd_or_step] = sorted_days
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
                        
                else:
                    # Regular slash command
                    success, data = await webhook_service.send_webhook(
                        interaction,
                        command=view.cmd_or_step,
                        status="ok",
                        result={"value": sorted_days}
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
                        error_msg = f"Ваш запит: Вихідні дні = {', '.join(sorted_days)}\nПомилка: Не вдалося виконати команду."
                        if message:
                            await message.edit(content=error_msg)
                            await message.add_reaction("❌")
                        else:
                            await interaction.followup.send(error_msg)
                        
            except Exception as e:
                logger.error(f"Error in confirm button: {e}")
                if message:
                    await message.remove_reaction("⏳", interaction.client.user)
                    error_msg = f"Ваш запит: Вихідні дні = {', '.join(sorted_days)}\nПомилка: Сталася неочікувана помилка."
                    await message.edit(content=error_msg)
                    await message.add_reaction("❌")

class DeclineButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="Не беру",
            row=4  # Put in the last row
        )
        
    async def callback(self, interaction: discord.Interaction):
        from services import webhook_service
        view = self.view
        if isinstance(view, DayOffView):
            # First, acknowledge the interaction to prevent timeout
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)
            
            # Get the original message
            message = interaction.message
            if message:
                # Add processing reaction
                await message.add_reaction("⏳")
            
            try:
                if view.has_survey:
                    # Dynamic survey flow
                    state = survey_manager.get_survey(view.user_id)
                    if not state:
                        if message:
                            await message.remove_reaction("⏳", interaction.client.user)
                            error_msg = "Ваш запит: Відмова від вихідних\nПомилка: Опитування не знайдено."
                            await message.edit(content=error_msg)
                            await message.add_reaction("❌")
                        return
                    
                    # Send webhook for survey step
                    success, data = await webhook_service.send_webhook(
                        interaction,
                        command="survey",
                        status="step",
                        result={
                            "stepName": view.cmd_or_step,
                            "daysSelected": ["Nothing"]
                        }
                    )
                    
                    if message:
                        # Remove processing reaction
                        await message.remove_reaction("⏳", interaction.client.user)
                    
                    if not success:
                        error_msg = "Ваш запит: Відмова від вихідних\nПомилка: Не вдалося виконати крок опитування."
                        if message:
                            await message.edit(content=error_msg)
                            await message.add_reaction("❌")
                        return
                    
                    # Update survey state
                    state.results[view.cmd_or_step] = ["Nothing"]
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
                        
                else:
                    # Regular slash command
                    success, data = await webhook_service.send_webhook(
                        interaction,
                        command=view.cmd_or_step,
                        status="ok",
                        result={"value": "Nothing"}
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
                        error_msg = "Ваш запит: Відмова від вихідних\nПомилка: Не вдалося виконати команду."
                        if message:
                            await message.edit(content=error_msg)
                            await message.add_reaction("❌")
                        else:
                            await interaction.followup.send(error_msg)
                        
            except Exception as e:
                logger.error(f"Error in decline button: {e}")
                if message:
                    await message.remove_reaction("⏳", interaction.client.user)
                    error_msg = "Ваш запит: Відмова від вихідних\nПомилка: Сталася неочікувана помилка."
                    await message.edit(content=error_msg)
                    await message.add_reaction("❌")

class DayOffView(discord.ui.View):
    def __init__(self, cmd_or_step: str, timeout: Optional[float] = 180):
        super().__init__(timeout=timeout)
        self.selected_days: List[str] = []
        self.cmd_or_step = cmd_or_step
        # Map of weekday names to their numeric values (0 = Monday, 6 = Sunday)
        self.weekday_map = {
            "Monday": 0,
            "Tuesday": 1,
            "Wednesday": 2,
            "Thursday": 3,
            "Friday": 4,
            "Saturday": 5,
            "Sunday": 6
        }

def create_day_off_view(
    cmd_or_step: str,
    user_id: str,
    timeout: Optional[float] = None,
    has_survey: bool = False
) -> DayOffView:
    """Create a day off view with buttons."""
    view = DayOffView(cmd_or_step, timeout=timeout)
    
    # Get current weekday (0 = Monday, 6 = Sunday)
    current_date = datetime.datetime.now()
    current_weekday = current_date.weekday()
    
    # Add day off buttons
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    ]
    
    for day in days:
        # For thisweek command, skip days that have already passed
        if "day_off_thisweek" in cmd_or_step and view.weekday_map[day] < current_weekday:
            continue
            
        custom_id = f"day_off_button_{day}_{cmd_or_step}_{user_id}"
        button = DayOffButton(label=day, custom_id=custom_id, cmd_or_step=cmd_or_step)
        view.add_item(button)
    
    # Add confirm and decline buttons
    view.add_item(ConfirmButton())
    view.add_item(DeclineButton())
    
    return view 