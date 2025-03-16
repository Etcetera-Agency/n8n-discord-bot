import discord
from discord import app_commands
from discord.ext import commands
from typing import List
from config import MONTHS, ViewType, logger
from services import webhook_service
from bot.views.factory import create_view

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
        
    def register_commands(self) -> None:
        """Register all slash commands."""
        
        # Day off command group
        day_off_group = app_commands.Group(name="day_off", description="Команди для вихідних")

        @day_off_group.command(name="thisweek", description="Оберіть вихідні на ЦЕЙ тиждень.")
        async def day_off_thisweek(interaction: discord.Interaction):
            """
            Select days off for the current week.
            
            Args:
                interaction: Discord interaction
            """
            logger.info(f"Day off thisweek command from {interaction.user}")
            await interaction.response.defer(thinking=True, ephemeral=False)
            view = create_view("day_off", "day_off_thisweek", str(interaction.user.id))
            await interaction.followup.send(
                "Оберіть свої вихідні (цей тиждень), потім натисніть «Відправити»:",
                view=view,
                ephemeral=False
            )

        @day_off_group.command(name="nextweek", description="Оберіть вихідні на НАСТУПНИЙ тиждень.")
        async def day_off_nextweek(interaction: discord.Interaction):
            """
            Select days off for the next week.
            
            Args:
                interaction: Discord interaction
            """
            logger.info(f"Day off nextweek command from {interaction.user}")
            await interaction.response.defer(thinking=True, ephemeral=False)
            view = create_view("day_off", "day_off_nextweek", str(interaction.user.id))
            await interaction.followup.send(
                "Оберіть свої вихідні (наступний тиждень), потім натисніть «Відправити»:",
                view=view,
                ephemeral=False
            )

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
                await interaction.response.send_message("День повинен бути між 1 та 31.", ephemeral=False)
                return
            
            # Process vacation request
            await webhook_service.send_webhook(
                interaction,
                command="vacation",
                result={
                    "start_day": str(start_day),
                    "start_month": start_month,
                    "end_day": str(end_day),
                    "end_month": end_month
                }
            )
            
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
            view = create_view("workload", "workload_today", str(interaction.user.id))
            await interaction.response.send_message(
                "Скільки годин підтверджено з СЬОГОДНІ до кінця тижня?\nЯкщо нічого, оберіть «Нічого немає».",
                view=view,
                ephemeral=False
            )

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
            view = create_view("workload", "workload_nextweek", str(interaction.user.id))
            await interaction.response.send_message(
                "Скільки годин підтверджено на НАСТУПНИЙ тиждень?\nЯкщо нічого, оберіть «Нічого немає».",
                view=view,
                ephemeral=False
            )

        @self.bot.tree.command(
            name="connects_thisweek",
            description="Скільки CONNECTS Upwork Connects History показує ЦЬОГО тижня?"
        )
        async def slash_connects_thisweek(interaction: discord.Interaction, connects: int):
            """
            Set Upwork connects for this week.
            
            Args:
                interaction: Discord interaction
                connects: Number of connects
            """
            logger.info(f"Connects thisweek command from {interaction.user}: {connects}")
            # Defer the response first
            await interaction.response.defer(thinking=True, ephemeral=False)
            
            # Send initial message and add processing reaction
            initial_message = await interaction.followup.send("Processing...", ephemeral=False)
            await initial_message.add_reaction("⏳")
            
            try:
                success, data = await webhook_service.send_webhook(
                    interaction,
                    command="connects_thisweek",
                    result={"connects": connects}
                )
                
                # Remove processing reaction
                await initial_message.remove_reaction("⏳", interaction.client.user)
                
                # Add success/error reaction based on the result
                await initial_message.add_reaction("✅" if success else "❌")
                
                # Edit the message with the actual response if we got data
                if success and data and "output" in data:
                    await initial_message.edit(content=data["output"])
                elif not success:
                    await initial_message.edit(content="Помилка: Не вдалося оновити connects.")
            except Exception as e:
                logger.error(f"Error in connects_thisweek: {e}")
                await initial_message.remove_reaction("⏳", interaction.client.user)
                await initial_message.add_reaction("❌")
                await initial_message.edit(content="Помилка: Сталася неочікувана помилка.") 