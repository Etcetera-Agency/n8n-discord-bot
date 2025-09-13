import discord
from discord.ext import commands
from services.webhook import WebhookService
from services.logging_utils import get_logger

class EventHandlers:
    def __init__(self, bot):
        """Initialize event handlers with the bot instance"""
        self.bot = bot

    async def setup(self):
        """Register all event handlers with the bot"""
        self.bot.add_listener(self.on_ready)
        self.bot.add_listener(self.on_close)
        # Ensure on_message listener is NOT added here

    async def on_ready(self):
        get_logger("bot.events").info("ready", extra={"bot_user": str(self.bot.user)})
        # Initialize WebhookService and assign to bot
        self.bot.webhook_service = WebhookService()

        try:
            await self.bot.tree.sync()
            get_logger("bot.events").info("slash synced")
        except Exception:
            get_logger("bot.events").exception("slash sync failed")

    async def on_close(self):
        get_logger("bot.events").info("closing")
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Assign a specific role to new members joining the server."""
        get_logger("bot.events.member_join", {"userId": str(member.id)}).info(
            "member joined", extra={"member": member.name, "guild": getattr(member.guild, "name", None)}
        )
        role_id = 1347214463199215637  # Replace with your actual role ID
        guild = member.guild

        if guild:
            role = guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role)
                    get_logger("bot.events.member_join", {"userId": str(member.id)}).info(
                        "role assigned", extra={"role": role.name}
                    )
                except discord.Forbidden:
                    get_logger("bot.events.member_join", {"userId": str(member.id)}).error(
                        "no permission to assign role", extra={"role": role.name}
                    )
                except Exception:
                    get_logger("bot.events.member_join", {"userId": str(member.id)}).exception(
                        "error assigning role"
                    )
            else:
                get_logger("bot.events.member_join").warning("role not found", extra={"role_id": role_id})
        else:
            get_logger("bot.events.member_join").warning("guild not found")

    # Removed the on_message handler from this class to avoid duplication
    # The primary on_message handler is now in bot.py
