import discord
import datetime
from discord import app_commands
from discord.ext import commands
from typing import List
from config import MONTHS, ViewType, logger, Strings, constants
from services import webhook_service
from bot.views.factory import create_view
import asyncio

class SlashCommands:
    """
    Slash commands for the bot.
    These are commands that use Discord's application commands.
    """
    
    def __init__(self, bot: commands.Bot):
        """
        Initialize slash commands.
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.register_commands()
        
    async def handle_webhook_command(self, interaction: discord.Interaction, command: str, result: dict):
        """
        Handle webhook command with standard processing flow.
        
        Args:
            interaction: Discord interaction
            command: Command name for webhook
            result: Data to send to webhook
        """
        # Get the original message
        message = await interaction.original_response() if interaction.response.is_done() else None
        
        try:
            if message:
                await message.add_reaction("⏳")
                
            success, data = await webhook_service.send_webhook(
                interaction,
                command=command,
                result=result
            )
            
            if message:
                await message.remove_reaction("⏳", interaction.client.user)
                
            if success and data and "output" in data:
                if message:
                    pass
                return data["output"]
            else:
                error_msg = f"Помилка: Не вдалося виконати команду."
                if message:
                    await message.add_reaction("❌")
                return error_msg
                
        except Exception as e:
            logger.error(f"Error in {command} command: {e}")
            if message:
                await message.remove_reaction("⏳", interaction.client.user)
                await message.add_reaction("❌")
            return f"Помилка: Сталася неочікувана помилка."
    
    async def create_interactive_command(self, interaction: discord.Interaction, view_type: str, command_name: str):
        """
        Create an interactive command with view.
        
        Args:
            interaction: Discord interaction
            view_type: Type of view to create
            command_name: Command name for the view
        """
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=False)
            
        command_msg = await interaction.original_response()
        view = create_view(
            "survey",  # Force survey view type
            command_name,
            str(interaction.user.id),
            view_type=ViewType.DYNAMIC
        )
        view.command_msg = command_msg
        
        buttons_msg = await interaction.channel.send(
            "Оберіть варіант:",
            view=view
        )
        view.buttons_msg = buttons_msg
        
    def register_commands(self) -> None:
        """Register all slash commands."""
        
        # Day off command group
        day_off_group = app_commands.Group(name="day_off", description=Strings.DAY_OFF_GROUP)

        @day_off_group.command(name="thisweek", description=Strings.DAY_OFF_THISWEEK)
        async def day_off_thisweek(interaction: discord.Interaction):
            """
            Select days off for the current week.
            
            Args:
                interaction: Discord interaction
            """
            logger.info(f"Day off thisweek command from {interaction.user}")
            
            # First send the command usage message and store it
            if not interaction.response.is_done():
                await interaction.response.send_message(f"{interaction.user} Оберіть свої вихідні (цей тиждень):")
            command_msg = await interaction.original_response()
            
            # Then send the buttons in a separate message
            view = create_view("day_off", "day_off_thisweek", str(interaction.user.id))
            view.command_msg = command_msg  # Store reference to command message
            buttons_msg = await interaction.channel.send(
                "В кінці натисніть кнопку Підтверджую",
                view=view
            )
            view.buttons_msg = buttons_msg  # Store reference to buttons message

        @day_off_group.command(name="nextweek", description="Оберіть вихідні на НАСТУПНИЙ тиждень.")
        async def day_off_nextweek(interaction: discord.Interaction):
            """
            Select days off for the next week.
            
            Args:
                interaction: Discord interaction
            """
            logger.info(f"Day off nextweek command from {interaction.user}")
            
            # First send the command usage message and store it
            if not interaction.response.is_done():
                await interaction.response.send_message(f"{interaction.user} Оберіть свої вихідні на наступний тиждень:")
            command_msg = await interaction.original_response()
            
            # Then send the buttons in a separate message
            view = create_view("day_off", "day_off_nextweek", str(interaction.user.id))
            view.command_msg = command_msg  # Store reference to command message
            buttons_msg = await interaction.channel.send(
                "В кінці натисніть кнопку Підтверждую",
                view=view
            )
            view.buttons_msg = buttons_msg  # Store reference to buttons message

        self.bot.tree.add_command(day_off_group)

        @self.bot.tree.command(name="vacation", description="Вкажіть день/місяць початку та кінця відпустки.")
        @app_commands.describe(
            start_day="День початку відпустки (1-31)",
            start_month="Місяць початку відпустки",
            end_day="День закінчення відпустки (1-31)",
            end_month="Місяць закінчення відпустки"
        )
        async def vacation_slash(
            interaction: discord.Interaction, 
            start_day: int,
            start_month: str,
            end_day: int,
            end_month: str
        ):
            """
            Set vacation dates.
            
            Args:
                interaction: Discord interaction
                start_day: Start day
                start_month: Start month
                end_day: End day
                end_month: End month
            """
            logger.info(f"Vacation command from {interaction.user}: {start_day}/{start_month} - {end_day}/{end_month}")
            
            # Validate inputs
            if not (1 <= start_day <= 31) or not (1 <= end_day <= 31):
                error_msg = f"Ваш запит: Відпустка {start_day}/{start_month} - {end_day}/{end_month}\nПомилка: День повинен бути між 1 та 31."
                await interaction.response.send_message(error_msg, ephemeral=False)
                return
            
            # First, acknowledge the interaction to prevent timeout
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)
            
            # Get the original message
            message = await interaction.original_response()
            if message:
                # Add processing reaction
                await message.add_reaction("⏳")
            
            try:
                # Get month numbers from constants
                start_month_num = constants.MONTHS.index(start_month) + 1
                end_month_num = constants.MONTHS.index(end_month) + 1
                
                # Determine correct years
                current_year = datetime.datetime.now().year
                current_month = datetime.datetime.now().month
                
                start_year = current_year
                if start_month_num < current_month:
                    start_year += 1
                    
                end_year = start_year
                if end_month_num < start_month_num:
                    end_year += 1
                
                # Create datetime objects in Kyiv timezone
                start_date = constants.KYIV_TIMEZONE.localize(
                    datetime.datetime(start_year, start_month_num, start_day)
                )
                end_date = constants.KYIV_TIMEZONE.localize(
                    datetime.datetime(end_year, end_month_num, end_day)
                )
                
                # Send ISO formatted dates to n8n
                success, data = await webhook_service.send_webhook(
                    interaction,
                    command="vacation",
                    status="ok",
                    result={
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    }
                )
                
                if message:
                    # Remove processing reaction
                    await message.remove_reaction("⏳", interaction.client.user)
                
                if success and data and "output" in data:
                    if message:
                        await message.edit(content=data["output"])
                    else:
                        await interaction.followup.send(data["output"])
                else:
                    error_msg = f"Ваш запит: Відпустка {start_day}/{start_month} - {end_day}/{end_month}\nПомилка: Не вдалося виконати команду."
                    if message:
                        await message.edit(content=error_msg)
                        await message.add_reaction("❌")
                    else:
                        await interaction.followup.send(error_msg)
                    
            except Exception as e:
                logger.error(f"Error in vacation command: {e}")
                if message:
                    await message.remove_reaction("⏳", interaction.client.user)
                    error_msg = f"Ваш запит: Відпустка {start_day}/{start_month} - {end_day}/{end_month}\nПомилка: Сталася неочікувана помилка."
                    await message.edit(content=error_msg)
                    await message.add_reaction("❌")
            
        @vacation_slash.autocomplete("start_month")
        @vacation_slash.autocomplete("end_month")
        async def month_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
            """
            Autocomplete for month selection.
            
            Args:
                interaction: Discord interaction
                current: Current input
                
            Returns:
                List of month choices
            """
            current = current.lower()
            return [
                app_commands.Choice(name=month, value=month)
                for month in MONTHS
                if current in month.lower()
            ][:25]  # Limit to 25 choices as per Discord limits
            
        @self.bot.tree.command(
            name="workload_today",
            description="Скільки годин підтверджено з СЬОГОДНІ до кінця тижня?"
        )
        async def slash_workload_today(interaction: discord.Interaction):
            """
            Set workload hours from today until the end of the week.
            
            Args:
                interaction: Discord interaction
            """
            logger.info(f"Workload today command from {interaction.user}")
            logger.debug(f"[{interaction.user}] - slash_workload_today called")
            
            # First send the command usage message and store it
            if not interaction.response.is_done():
                await interaction.response.send_message(f"{interaction.user} На скільки годин у тебе підтверджена зайнятість з СЬОГОДНІ до кінця тижня? ")
            command_msg = await interaction.original_response()
            
            # Then send the buttons in a separate message
            logger.debug(f"[{interaction.user}] - Calling create_view for workload_today")
            view = create_view("workload", "workload_today", str(interaction.user.id))
            view.command_msg = command_msg  # Store reference to command message
            buttons_msg = await interaction.channel.send(
                "Оберіть кількість годин:",
                view=view
            )
            view.buttons_msg = buttons_msg  # Store reference to buttons message

        @self.bot.tree.command(
            name="workload_nextweek",
            description="Скільки годин підтверджено на НАСТУПНИЙ тиждень?"
        )
        async def slash_workload_nextweek(interaction: discord.Interaction):
            """
            Set workload hours for the next week.
            
            Args:
                interaction: Discord interaction
            """
            logger.info(f"Workload nextweek command from {interaction.user}")
            logger.debug(f"[{interaction.user}] - slash_workload_nextweek called")
            
            # First send the command usage message and store it
            if not interaction.response.is_done():
                await interaction.response.send_message(f"{interaction.user} Скажи, а чи є підтверджені завдання на наступний тиждень? ")
            command_msg = await interaction.original_response()
            
            # Then send the buttons in a separate message
            logger.debug(f"[{interaction.user}] - Calling create_view for workload_nextweek")
            view = create_view("workload", "workload_nextweek", str(interaction.user.id))
            view.command_msg = command_msg  # Store reference to command message
            buttons_msg = await interaction.channel.send(
                "Оберіть кількість годин:",
                view=view
            )
            view.buttons_msg = buttons_msg  # Store reference to buttons message

        @self.bot.tree.command(
            name="connects",
            description="Скільки CONNECTS Upwork Connects History показує ЦЬОГО тижня?"
        )
        async def slash_connects(interaction: discord.Interaction, connects: int):
            """
            Set Upwork connects for this week.
            
            Args:
                interaction: Discord interaction
                connects: Number of connects
            """
            logger.info(f"[DEBUG] Connects command from {interaction.user}: {connects}")
            
            # First, acknowledge the interaction to prevent timeout
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)
            
            # Get the original message
            message = await interaction.original_response()
            if message:
                # Add processing reaction
                await message.add_reaction("⏳")
            
            try:
                # Send webhook
                success, data = await webhook_service.send_webhook(
                    interaction,
                    command="connects",
                    status="ok",
                    result={"connects": connects}
                )
                
                logger.debug(f"[DEBUG] Webhook response for connects: success={success}, data={data}")
                
                if message:
                    # Remove processing reaction
                    await message.remove_reaction("⏳", interaction.client.user)
                
                if success and data and "output" in data:
                    if message:
                        pass
                    await interaction.followup.send(data["output"])
                else:
                    error_msg = f"Ваш запит: Connects на цей тиждень = {connects}\nПомилка: Не вдалося виконати команду."
                    if message:
                        await message.edit(content=error_msg)
                        await message.add_reaction("❌")
                    else:
                        await interaction.followup.send(error_msg)
                    
            except Exception as e:
                logger.error(f"Error in connects command: {e}")
                if message:
                    await message.remove_reaction("⏳", interaction.client.user)
                    error_msg = f"Ваш запит: Connects на цей тиждень = {connects}\nПомилка: Сталася неочікувана помилка."
                    await message.edit(content=error_msg)
                    await message.add_reaction("❌")