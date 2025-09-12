import discord
from discord import AllowedMentions
import datetime
from discord import app_commands
from discord.ext import commands
from typing import List
from config import MONTHS, logger, Strings, constants
from services import webhook_service
from discord_bot.views.factory import create_view

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
        logger.info(f"⚡ WEBHOOK COMMAND START: {command} from {interaction.user}")
        logger.debug(f"Command payload: {result}")
        
        # Get the original message
        message = await interaction.original_response() if interaction.response.is_done() else None
        
        try:
            if message:
                logger.debug(f"Adding processing reaction to message {message.id}")
                await message.add_reaction(Strings.PROCESSING)
                
            logger.info(f"Sending webhook for {command} command...")
            success, data = await webhook_service.send_webhook(
                interaction,
                command=command,
                result=result
            )
            logger.info(f"Webhook response for {command}: success={success}, data={bool(data)}")
            
            if message:
                logger.debug(f"Removing processing reaction from message {message.id}")
                await message.remove_reaction(Strings.PROCESSING, interaction.client.user)
                
            if success and data and "output" in data:
                logger.debug(f"Webhook success output: {data['output']}")
                if message:
                    logger.debug(f"Returning success output for message {message.id}")
                return data["output"]
            else:
                error_msg = Strings.GENERAL_ERROR
                logger.warning(f"Webhook failed for {command}: {error_msg}")
                if message:
                    logger.debug(f"Adding error reaction to message {message.id}")
                    await message.add_reaction(Strings.ERROR)
                return error_msg
                
        except Exception as e:
            logger.error(f"⛔ Error in {command} command: {str(e)}", exc_info=True)
            if message:
                logger.debug(f"Handling error for message {message.id}")
                await message.remove_reaction(Strings.PROCESSING, interaction.client.user)
                await message.add_reaction(Strings.ERROR)
            return Strings.UNEXPECTED_ERROR
    
    async def create_interactive_command(self, interaction: discord.Interaction, command_name: str):
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
            self.bot,
            "survey",
            command_name,
            str(interaction.user.id)
        )
        view.command_msg = command_msg
        
        buttons_msg = await interaction.channel.send(
            Strings.SELECT_OPTION,
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
            logger.info(f"[Channel {interaction.channel.id}] Day off thisweek command from {interaction.user}")
            
            # First send the command usage message and store it
            if not interaction.response.is_done():
                await interaction.response.send_message(f"<@{interaction.user.id}> {Strings.DAY_OFF_THISWEEK}", allowed_mentions=AllowedMentions(roles=True, users=True, everyone=False))
            command_msg = await interaction.original_response()
            
            # Then send the buttons in a separate message
            view = create_view(self.bot, "day_off", "day_off_thisweek", str(interaction.user.id)) # Pass bot_instance and survey=None
            view.command_msg = command_msg  # Store reference to command message
            buttons_msg = await interaction.channel.send(
                Strings.CONFIRM_BUTTON,
                view=view
            )
            view.buttons_msg = buttons_msg  # Store reference to buttons message

        @day_off_group.command(name="nextweek", description=Strings.DAY_OFF_NEXTWEEK)
        async def day_off_nextweek(interaction: discord.Interaction):
            """
            Select days off for the next week.
            
            Args:
                interaction: Discord interaction
            """
            logger.debug(f"[Channel {interaction.channel.id}] Day off nextweek command received from {interaction.user}")
            
            try:
                # First send the command usage message and store it
                logger.debug("Sending command usage message")
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"<@{interaction.user.id}> {Strings.DAY_OFF_NEXTWEEK}", allowed_mentions=AllowedMentions(roles=True, users=True, everyone=False))
                command_msg = await interaction.original_response()
                
                # Then send the buttons in a separate message
                logger.debug(f"[Channel {interaction.channel.id}] Creating day off view for command: day_off_nextweek")
                view = create_view(self.bot, "day_off", "day_off_nextweek", str(interaction.user.id)) # Pass bot_instance and survey=None
                view.command_msg = command_msg  # Store reference to command message
                
                logger.debug("Sending buttons message")
                buttons_msg = await interaction.channel.send(
                    Strings.CONFIRM_BUTTON,
                    view=view
                )
                view.buttons_msg = buttons_msg  # Store reference to buttons message
                logger.debug("Day off nextweek command completed successfully")
            except Exception as e:
                logger.error(f"Error in day_off_nextweek: {e}")
                raise

        self.bot.tree.add_command(day_off_group)

        @self.bot.tree.command(name="vacation", description=Strings.VACATION)
        @app_commands.describe(
            start_day=Strings.START_DAY,
            start_month=Strings.START_MONTH,
            end_day=Strings.END_DAY,
            end_month=Strings.END_MONTH
        )
        async def vacation_slash(
            interaction: discord.Interaction,
            start_day: int,
            start_month: str,
            end_day: int,
            end_month: str
        ):
            from config import Strings # Import Strings locally
            """
            Set vacation dates.
            
            Args:
                interaction: Discord interaction
                start_day: Start day
                start_month: Start month
                end_day: End day
                end_month: End month
            """
            logger.info(f"[Channel {interaction.channel.id}] Vacation command from {interaction.user}: {start_day}/{start_month} - {end_day}/{end_month}")
            
            # Validate inputs
            if not (1 <= start_day <= 31) or not (1 <= end_day <= 31):
                error_msg = f"Ваш запит: Відпустка {start_day}/{start_month} - {end_day}/{end_month}\nПомилка: День повинен бути між 1 та 31."
                await interaction.response.send_message(error_msg, ephemeral=False, allowed_mentions=AllowedMentions(roles=True, users=True, everyone=False))
                return
            
            # First, acknowledge the interaction to prevent timeout
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)
            
            # Get the original message
            message = await interaction.original_response()
            if message:
                # Add processing reaction
                await message.add_reaction(Strings.PROCESSING)
            
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
                    await message.remove_reaction(Strings.PROCESSING, interaction.client.user)
                
                if success and data and "output" in data:
                    if message:
                        output_content = data["output"]
                        logger.debug(f"Output content before mention check: '{output_content}', Mention message: '{Strings.MENTION_MESSAGE}'")
                        # Check if output is not empty, does not contain an error indicator, and mention is not already present
                        if output_content and "Помилка" not in output_content and Strings.MENTION_MESSAGE not in output_content:
                            output_content += Strings.MENTION_MESSAGE
 
                        if message:
                            await message.edit(content=output_content, allowed_mentions=AllowedMentions(roles=True, users=True, everyone=False))
                        else:
                            await interaction.followup.send(output_content, allowed_mentions=AllowedMentions(roles=True, users=True, everyone=False))
                else:
                    error_msg = Strings.DAYOFF_ERROR.format(
                        days=f"{start_day}/{start_month} - {end_day}/{end_month}",
                        error=Strings.GENERAL_ERROR
                    )
                    if message:
                        await message.edit(content=error_msg, allowed_mentions=AllowedMentions(roles=True, users=True, everyone=False))
                        await message.add_reaction(Strings.ERROR)
                    else:
                        await interaction.followup.send(error_msg, allowed_mentions=AllowedMentions(roles=True, users=True, everyone=False))
                    
            except Exception as e:
                logger.error(f"Error in vacation command: {e}")
                if message:
                    await message.remove_reaction(Strings.PROCESSING, interaction.client.user)
                    error_msg = Strings.DAYOFF_ERROR.format(
                        days=f"{start_day}/{start_month} - {end_day}/{end_month}",
                        error=Strings.UNEXPECTED_ERROR
                    )
                    await message.edit(content=error_msg, allowed_mentions=AllowedMentions(roles=True, users=True, everyone=False))
                    await message.add_reaction(Strings.ERROR)
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
            description=Strings.WORKLOAD_TODAY
        )
        async def slash_workload_today(interaction: discord.Interaction):
            """
            Set workload hours from today until the end of the week.
            
            Args:
                interaction: Discord interaction
            """
            logger.info(f"[Channel {interaction.channel.id}] Workload today command from {interaction.user}")
            logger.debug(f"[{interaction.user}] - slash_workload_today called")
            
            # First send the command usage message and store it
            if not interaction.response.is_done():
                await interaction.response.send_message(f"<@{interaction.user.id}> На скільки годин у тебе підтверджена зайнятість з СЬОГОДНІ до кінця тижня? ", allowed_mentions=AllowedMentions(roles=True, users=True, everyone=False))
            command_msg = await interaction.original_response()
            
            # Then send the buttons in a separate message
            logger.debug(f"[Channel {interaction.channel.id}] [{interaction.user}] - Calling create_view for workload_today")
            view = create_view(self.bot, "workload", "workload_today", str(interaction.user.id)) # Pass bot_instance and survey=None
            view.command_msg = command_msg  # Store reference to command message
            logger.debug(f"[{interaction.user}] - Workload view items before sending: {len(view.children)}") # Add this log
            buttons_msg = await interaction.channel.send(
                Strings.SELECT_HOURS,
                view=view
            )
            view.buttons_msg = buttons_msg  # Store reference to buttons message

        @self.bot.tree.command(
            name="workload_nextweek",
            description=Strings.WORKLOAD_NEXTWEEK
        )
        async def slash_workload_nextweek(interaction: discord.Interaction):
            """
            Set workload hours for the next week.
            
            Args:
                interaction: Discord interaction
            """
            logger.info(f"[Channel {interaction.channel.id}] Workload nextweek command from {interaction.user}")
            logger.debug(f"[{interaction.user}] - slash_workload_nextweek called")
            
            # First send the command usage message and store it
            if not interaction.response.is_done():
                await interaction.response.send_message(f"<@{interaction.user.id}> Скажи, а чи є підтверджені завдання на наступний тиждень? ", allowed_mentions=AllowedMentions(roles=True, users=True, everyone=False))
            command_msg = await interaction.original_response()
            
            # Then send the buttons in a separate message
            logger.debug(f"[Channel {interaction.channel.id}] [{interaction.user}] - Calling create_view for workload_nextweek")
            view = create_view(self.bot, "workload", "workload_nextweek", str(interaction.user.id))
            view.command_msg = command_msg  # Store reference to command message
            buttons_msg = await interaction.channel.send(
                Strings.SELECT_HOURS,
                view=view
            )
            view.buttons_msg = buttons_msg  # Store reference to buttons message

        @self.bot.tree.command(
            name="connects_thisweek",
            description=Strings.CONNECTS
        )
        async def slash_connects(interaction: discord.Interaction, connects: int):
            """
            Set Upwork connects for this week.
            
            Args:
                interaction: discord.Interaction
                connects: Number of connects
            """
            from config import Strings # Import Strings locally
            logger.info(f"[Channel {interaction.channel.id}] [DEBUG] Connects command from {interaction.user}: {connects}")
            
            # First, acknowledge the interaction to prevent timeout
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)
            
            # Get the original message
            message = await interaction.original_response()
            if message:
                # Add processing reaction
                await message.add_reaction(Strings.PROCESSING)
            
            try:
                # Send webhook
                logger.debug(f"[Channel {interaction.channel.id}] [{interaction.user}] - Attempting to send webhook for connects command")
                success, data = await webhook_service.send_webhook(
                    interaction,
                    command="connects_thisweek",
                    status="ok",
                    result={"connects": connects}
                )
                logger.debug(f"[{interaction.user}] - Webhook response for connects: success={success}, data={data}")
                
                logger.debug(f"[{interaction.user}] - Checking webhook success and data for connects command")
                if message:
                    logger.debug(f"[{interaction.user}] - Attempting to remove processing reaction from message {message.id}")
                    # Remove processing reaction
                    await message.remove_reaction(Strings.PROCESSING, interaction.client.user)
                    logger.debug(f"[{interaction.user}] - Removed processing reaction from message {message.id}")
                
                logger.debug(f"[{interaction.user}] - Checking webhook success and data for connects command")
                if success and data and "output" in data:
                    if message:
                        logger.debug(f"[{interaction.user}] - Message exists, no edit needed for success output")
                        pass # No need to edit the original message if sending a follow-up
                    logger.info(f"[{interaction.user}] - Attempting to send followup message. Type: {type(data.get('output'))}, Value: '{data.get('output')}'")
                    await interaction.followup.send(data["output"], allowed_mentions=AllowedMentions(roles=True, users=True, everyone=False))
                    logger.debug(f"[{interaction.user}] - Followup message sent")
                else:
                    logger.debug(f"[{interaction.user}] - Webhook failed or no output in data for connects command")
                    error_msg = Strings.CONNECTS_ERROR.format(
                        connects=connects,
                        error=Strings.GENERAL_ERROR
                    )
                    if message:
                        logger.debug(f"[{interaction.user}] - Attempting to edit message {message.id} with error message: {error_msg}")
                        await message.edit(content=error_msg, allowed_mentions=AllowedMentions(roles=True, users=True, everyone=False))
                        logger.debug(f"[{interaction.user}] - Attempting to add error reaction to message {message.id}")
                        await message.add_reaction(Strings.ERROR)
                        logger.debug(f"[{interaction.user}] - Added error reaction to message {message.id}")
                    else:
                        logger.debug(f"[{interaction.user}] - Attempting to send followup error message: {error_msg}")
                        await interaction.followup.send(error_msg, allowed_mentions=AllowedMentions(roles=True, users=True, everyone=False))
                        logger.debug(f"[{interaction.user}] - Followup error message sent")
                    
            except Exception as e:
                logger.error(f"[{interaction.user}] - ⛔ Error in connects command: {e}", exc_info=True)
                if message:
                    logger.debug(f"[{interaction.user}] - Handling error for message {message.id}")
                    try:
                        await message.remove_reaction(Strings.PROCESSING, interaction.client.user)
                    except Exception as remove_e:
                        logger.error(f"[{interaction.user}] - Error removing processing reaction in error handler: {remove_e}")
                    
                    error_msg = Strings.CONNECTS_ERROR.format(
                        connects=connects,
                        error=Strings.UNEXPECTED_ERROR
                    )
                    try:
                        await message.edit(content=error_msg, allowed_mentions=AllowedMentions(roles=True, users=True, everyone=False))
                    except Exception as edit_e:
                        logger.error(f"[{interaction.user}] - Error editing message with error message in error handler: {edit_e}")
                        
                    try:
                        await message.add_reaction(Strings.ERROR)
                    except Exception as add_e:
                        logger.error(f"[{interaction.user}] - Error adding error reaction in error handler: {add_e}")
                else:
                    logger.debug(f"[{interaction.user}] - No message to edit, sending followup error message")
                    error_msg = Strings.CONNECTS_ERROR.format(
                        connects=connects,
                        error=Strings.UNEXPECTED_ERROR
                    )
                    try:
                        await interaction.followup.send(error_msg, allowed_mentions=AllowedMentions(roles=True, users=True, everyone=False))
                    except Exception as followup_e:
                        logger.error(f"[{interaction.user}] - Error sending followup error message in error handler: {followup_e}")
