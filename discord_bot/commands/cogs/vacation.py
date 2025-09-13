import datetime

import discord
from discord import AllowedMentions
from discord import app_commands
from discord.ext import commands

from config import Strings, constants
from services.logging_utils import get_logger
from services import webhook_service


class VacationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        @self.bot.tree.command(name="vacation", description=Strings.VACATION)
        @app_commands.describe(
            start_day=Strings.START_DAY,
            start_month=Strings.START_MONTH,
            end_day=Strings.END_DAY,
            end_month=Strings.END_MONTH,
        )
        async def vacation_slash(
            interaction: discord.Interaction,
            start_day: int,
            start_month: str,
            end_day: int,
            end_month: str,
        ):
            log = get_logger(
                "cmd.vacation",
                {"userId": str(interaction.user.id), "channelId": str(interaction.channel.id)},
            )
            log.info(
                f"request: {start_day}/{start_month} - {end_day}/{end_month}"
            )

            if not (1 <= start_day <= 31) or not (1 <= end_day <= 31):
                error_msg = (
                    f"Ваш запит: Відпустка {start_day}/{start_month} - {end_day}/{end_month}\n"
                    f"Помилка: День повинен бути між 1 та 31."
                )
                await interaction.response.send_message(
                    error_msg,
                    ephemeral=False,
                    allowed_mentions=AllowedMentions(roles=True, users=True, everyone=False),
                )
                return

            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)

            message = await interaction.original_response()
            if message:
                await message.add_reaction(Strings.PROCESSING)

            try:
                start_month_num = constants.MONTHS.index(start_month) + 1
                end_month_num = constants.MONTHS.index(end_month) + 1

                current_year = datetime.datetime.now().year
                current_month = datetime.datetime.now().month

                start_year = current_year
                if start_month_num < current_month:
                    start_year += 1

                end_year = start_year
                if end_month_num < start_month_num:
                    end_year += 1

                start_date = constants.KYIV_TIMEZONE.localize(
                    datetime.datetime(start_year, start_month_num, start_day)
                )
                end_date = constants.KYIV_TIMEZONE.localize(
                    datetime.datetime(end_year, end_month_num, end_day)
                )

                success, data = await webhook_service.send_webhook(
                    interaction,
                    command="vacation",
                    status="ok",
                    result={
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                    },
                )

                if message:
                    await message.remove_reaction(Strings.PROCESSING, interaction.client.user)

                if success and data and "output" in data:
                    output_content = data["output"]
                    log.debug(
                        f"Output content before mention check: '{output_content}', Mention message: '{Strings.MENTION_MESSAGE}'"
                    )
                    if (
                        output_content
                        and "Помилка" not in output_content
                        and Strings.MENTION_MESSAGE not in output_content
                    ):
                        output_content += Strings.MENTION_MESSAGE

                    if message:
                        await message.edit(
                            content=output_content,
                            allowed_mentions=AllowedMentions(
                                roles=True, users=True, everyone=False
                            ),
                        )
                    else:
                        await interaction.followup.send(
                            output_content,
                            allowed_mentions=AllowedMentions(
                                roles=True, users=True, everyone=False
                            ),
                        )
                else:
                    error_msg = Strings.DAYOFF_ERROR.format(
                        days=f"{start_day}/{start_month} - {end_day}/{end_month}",
                        error=Strings.GENERAL_ERROR,
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
            except Exception:  # pragma: no cover - defensive
                log.exception("error")
                if message:
                    try:
                        await message.remove_reaction(Strings.PROCESSING, interaction.client.user)
                    except Exception:
                        pass
                    error_msg = Strings.DAYOFF_ERROR.format(
                        days=f"{start_day}/{start_month} - {end_day}/{end_month}",
                        error=Strings.UNEXPECTED_ERROR,
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

        @vacation_slash.autocomplete("start_month")
        @vacation_slash.autocomplete("end_month")
        async def month_autocomplete(
            interaction: discord.Interaction, current: str
        ) -> list[app_commands.Choice[str]]:
            current = current.lower()
            return [
                app_commands.Choice(name=month, value=month)
                for month in constants.MONTHS
                if current in month.lower()
            ][:25]


async def setup(bot: commands.Bot):
    await bot.add_cog(VacationCog(bot))
