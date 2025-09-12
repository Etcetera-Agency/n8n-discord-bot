import discord
from discord import AllowedMentions
from discord.ext import commands

from config import logger, Strings
from discord_bot.views.factory import create_view


class WorkloadCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        @self.bot.tree.command(name="workload_today", description=Strings.WORKLOAD_TODAY)
        async def slash_workload_today(interaction: discord.Interaction):
            logger.info(
                f"[Channel {interaction.channel.id}] Workload today command from {interaction.user}"
            )
            logger.debug(f"[{interaction.user}] - slash_workload_today called")

            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"<@{interaction.user.id}> {Strings.WORKLOAD_TODAY}",
                    allowed_mentions=AllowedMentions(roles=True, users=True, everyone=False),
                )
            command_msg = await interaction.original_response()

            logger.debug(
                f"[Channel {interaction.channel.id}] [{interaction.user}] - Calling create_view for workload_today"
            )
            view = create_view(
                self.bot, "workload", "workload_today", str(interaction.user.id)
            )
            view.command_msg = command_msg
            buttons_msg = await interaction.channel.send(Strings.SELECT_HOURS, view=view)
            view.buttons_msg = buttons_msg

        @self.bot.tree.command(
            name="workload_nextweek", description=Strings.WORKLOAD_NEXTWEEK
        )
        async def slash_workload_nextweek(interaction: discord.Interaction):
            logger.info(
                f"[Channel {interaction.channel.id}] Workload nextweek command from {interaction.user}"
            )
            logger.debug(f"[{interaction.user}] - slash_workload_nextweek called")

            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"<@{interaction.user.id}> {Strings.WORKLOAD_NEXTWEEK}",
                    allowed_mentions=AllowedMentions(roles=True, users=True, everyone=False),
                )
            command_msg = await interaction.original_response()

            logger.debug(
                f"[Channel {interaction.channel.id}] [{interaction.user}] - Calling create_view for workload_nextweek"
            )
            view = create_view(
                self.bot, "workload", "workload_nextweek", str(interaction.user.id)
            )
            view.command_msg = command_msg
            buttons_msg = await interaction.channel.send(Strings.SELECT_HOURS, view=view)
            view.buttons_msg = buttons_msg


async def setup(bot: commands.Bot):
    await bot.add_cog(WorkloadCog(bot))

