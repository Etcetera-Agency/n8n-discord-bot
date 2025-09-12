
import discord
from discord.ext import commands

from config import logger, Strings
from services import webhook_service
from discord_bot.views.factory import create_view


async def handle_webhook_command(
    interaction: discord.Interaction, command: str, result: dict
) -> str:
    """
    Handle a webhook-style slash command in a standard way.

    Adds a processing reaction, sends the webhook, handles success/error,
    and returns the output string to display to the user.
    """
    logger.info(f"⚡ WEBHOOK COMMAND START: {command} from {interaction.user}")
    logger.debug(f"Command payload: {result}")

    message = await interaction.original_response() if interaction.response.is_done() else None

    try:
        if message:
            await message.add_reaction(Strings.PROCESSING)

        success, data = await webhook_service.send_webhook(
            interaction, command=command, result=result
        )

        if message:
            await message.remove_reaction(Strings.PROCESSING, interaction.client.user)

        if success and data and "output" in data:
            return data["output"]
        else:
            if message:
                await message.add_reaction(Strings.ERROR)
            return Strings.GENERAL_ERROR
    except Exception as e:  # pragma: no cover - defensive
        logger.error(f"⛔ Error in {command} command: {str(e)}", exc_info=True)
        if message:
            try:
                await message.remove_reaction(Strings.PROCESSING, interaction.client.user)
            except Exception:
                pass
            try:
                await message.add_reaction(Strings.ERROR)
            except Exception:
                pass
        return Strings.UNEXPECTED_ERROR


async def create_interactive_command(
    bot: commands.Bot, interaction: discord.Interaction, command_name: str
) -> None:
    """
    Create an interactive command message with a corresponding view.

    Sends a visible message with buttons/modals wired to the passed command_name.
    """
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=False)

    command_msg = await interaction.original_response()
    view = create_view(bot, "survey", command_name, str(interaction.user.id))
    view.command_msg = command_msg

    buttons_msg = await interaction.channel.send(Strings.SELECT_OPTION, view=view)
    view.buttons_msg = buttons_msg

