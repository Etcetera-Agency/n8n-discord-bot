import discord
from discord import AllowedMentions
from discord import app_commands
from discord.ext import commands

from config import Strings
from services.logging_utils import get_logger
from discord_bot.views.factory import create_view


class DayOffCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        day_off_group = app_commands.Group(
            name="day_off", description=Strings.DAY_OFF_GROUP
        )

        @day_off_group.command(name="thisweek", description=Strings.DAY_OFF_THISWEEK)
        async def day_off_thisweek(interaction: discord.Interaction):
            log = get_logger(
                "cmd.day_off.thisweek",
                {"userId": str(interaction.user.id), "channelId": str(interaction.channel.id)},
            )
            log.info("received")

            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"<@{interaction.user.id}> {Strings.DAY_OFF_THISWEEK}",
                    allowed_mentions=AllowedMentions(roles=True, users=True, everyone=False),
                )
            command_msg = await interaction.original_response()

            view = create_view(
                self.bot, "day_off", "day_off_thisweek", str(interaction.user.id)
            )
            view.command_msg = command_msg
            buttons_msg = await interaction.channel.send(Strings.CONFIRM_BUTTON, view=view)
            view.buttons_msg = buttons_msg

        @day_off_group.command(name="nextweek", description=Strings.DAY_OFF_NEXTWEEK)
        async def day_off_nextweek(interaction: discord.Interaction):
            log = get_logger(
                "cmd.day_off.nextweek",
                {"userId": str(interaction.user.id), "channelId": str(interaction.channel.id)},
            )
            log.debug("received")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        f"<@{interaction.user.id}> {Strings.DAY_OFF_NEXTWEEK}",
                        allowed_mentions=AllowedMentions(
                            roles=True, users=True, everyone=False
                        ),
                    )
                command_msg = await interaction.original_response()

                log.debug("creating view")
                view = create_view(
                    self.bot, "day_off", "day_off_nextweek", str(interaction.user.id)
                )
                view.command_msg = command_msg

                log.debug("sending buttons")
                buttons_msg = await interaction.channel.send(
                    Strings.CONFIRM_BUTTON, view=view
                )
                view.buttons_msg = buttons_msg
                log.debug("completed")
            except Exception:  # pragma: no cover - defensive
                log.exception("error")
                raise

        # Register group
        self.bot.tree.add_command(day_off_group)


async def setup(bot: commands.Bot):
    await bot.add_cog(DayOffCog(bot))
