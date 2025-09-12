import discord
from discord import AllowedMentions
from discord import app_commands
from discord.ext import commands

from config import logger, Strings
from discord_bot.views.factory import create_view


class DayOffCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        day_off_group = app_commands.Group(
            name="day_off", description=Strings.DAY_OFF_GROUP
        )

        @day_off_group.command(name="thisweek", description=Strings.DAY_OFF_THISWEEK)
        async def day_off_thisweek(interaction: discord.Interaction):
            logger.info(
                f"[Channel {interaction.channel.id}] Day off thisweek command from {interaction.user}"
            )

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
            logger.debug(
                f"[Channel {interaction.channel.id}] Day off nextweek command received from {interaction.user}"
            )
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        f"<@{interaction.user.id}> {Strings.DAY_OFF_NEXTWEEK}",
                        allowed_mentions=AllowedMentions(
                            roles=True, users=True, everyone=False
                        ),
                    )
                command_msg = await interaction.original_response()

                logger.debug(
                    f"[Channel {interaction.channel.id}] Creating day off view for command: day_off_nextweek"
                )
                view = create_view(
                    self.bot, "day_off", "day_off_nextweek", str(interaction.user.id)
                )
                view.command_msg = command_msg

                logger.debug("Sending buttons message")
                buttons_msg = await interaction.channel.send(
                    Strings.CONFIRM_BUTTON, view=view
                )
                view.buttons_msg = buttons_msg
                logger.debug("Day off nextweek command completed successfully")
            except Exception as e:  # pragma: no cover - defensive
                logger.error(f"Error in day_off_nextweek: {e}")
                raise

        # Register group
        self.bot.tree.add_command(day_off_group)


async def setup(bot: commands.Bot):
    await bot.add_cog(DayOffCog(bot))

