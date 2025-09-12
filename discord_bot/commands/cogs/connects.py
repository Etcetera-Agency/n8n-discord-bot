import discord
from discord import AllowedMentions
from discord.ext import commands

from config import logger, Strings
from services import webhook_service


class ConnectsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        @self.bot.tree.command(name="connects_thisweek", description=Strings.CONNECTS_THISWEEK)
        async def slash_connects(interaction: discord.Interaction, connects: int):
            """
            Set Upwork connects for this week.
            """
            logger.info(
                f"[Channel {interaction.channel.id}] [DEBUG] Connects command from {interaction.user}: {connects}"
            )

            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)

            message = await interaction.original_response()
            if message:
                await message.add_reaction(Strings.PROCESSING)

            try:
                logger.debug(
                    f"[Channel {interaction.channel.id}] [{interaction.user}] - Attempting to send webhook for connects command"
                )
                success, data = await webhook_service.send_webhook(
                    interaction,
                    command="connects_thisweek",
                    status="ok",
                    result={"connects": connects},
                )
                logger.debug(
                    f"[{interaction.user}] - Webhook response for connects: success={success}, data={data}"
                )

                if message:
                    await message.remove_reaction(Strings.PROCESSING, interaction.client.user)

                if success and data and "output" in data:
                    await interaction.followup.send(
                        data["output"],
                        allowed_mentions=AllowedMentions(roles=True, users=True, everyone=False),
                    )
                else:
                    error_msg = Strings.CONNECTS_ERROR.format(
                        connects=connects, error=Strings.GENERAL_ERROR
                    )
                    if message:
                        await message.edit(
                            content=error_msg,
                            allowed_mentions=AllowedMentions(
                                roles=True, users=True, everyone=False
                            ),
                        )
                        await message.add_reaction(Strings.ERROR)
                    else:
                        await interaction.followup.send(
                            error_msg,
                            allowed_mentions=AllowedMentions(
                                roles=True, users=True, everyone=False
                            ),
                        )
            except Exception as e:  # pragma: no cover - defensive
                logger.error(
                    f"[{interaction.user}] - ⛔ Error in connects command: {e}",
                    exc_info=True,
                )
                if message:
                    try:
                        await message.remove_reaction(Strings.PROCESSING, interaction.client.user)
                    except Exception:
                        pass
                    error_msg = Strings.CONNECTS_ERROR.format(
                        connects=connects, error=Strings.UNEXPECTED_ERROR
                    )
                    try:
                        await message.edit(
                            content=error_msg,
                            allowed_mentions=AllowedMentions(
                                roles=True, users=True, everyone=False
                            ),
                        )
                    except Exception:
                        pass
                    try:
                        await message.add_reaction(Strings.ERROR)
                    except Exception:
                        pass
                else:
                    error_msg = Strings.CONNECTS_ERROR.format(
                        connects=connects, error=Strings.UNEXPECTED_ERROR
                    )
                    try:
                        await interaction.followup.send(
                            error_msg,
                            allowed_mentions=AllowedMentions(
                                roles=True, users=True, everyone=False
                            ),
                        )
                    except Exception:
                        pass


async def setup(bot: commands.Bot):
    await bot.add_cog(ConnectsCog(bot))

