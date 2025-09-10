import discord
from discord.ext import commands
from services.webhook import WebhookService
from config.logger import logger

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
        logger.info(f"Bot connected as {self.bot.user}")
        # Initialize WebhookService and assign to bot
        self.bot.webhook_service = WebhookService()

        try:
            await self.bot.tree.sync()
            logger.info("Slash commands synced!")
        except Exception as e:
            logger.error(f"Error syncing slash commands: {e}")

    async def on_close(self):
        logger.info("Bot shutting down, cleaning up resources")
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Assign a specific role to new members joining the server."""
        logger.info(f"Member {member.name} ({member.id}) joined the server {member.guild.name} ({member.guild.id}).")
        role_id = 1347214463199215637  # Replace with your actual role ID
        guild = member.guild

        if guild:
            role = guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role)
                    logger.info(f"Assigned role {role.name} ({role.id}) to member {member.name} ({member.id}).")
                except discord.Forbidden:
                    logger.error(f"Bot does not have permissions to assign role {role.name} ({role.id}) in guild {guild.name} ({guild.id}).")
                except Exception as e:
                    logger.error(f"Error assigning role to member {member.name} ({member.id}): {e}")
            else:
                logger.warning(f"Role with ID {role_id} not found in guild {guild.name} ({guild.id}).")
        else:
            logger.warning(f"Guild not found for member {member.name} ({member.id}).")

    # Removed the on_message handler from this class to avoid duplication
    # The primary on_message handler is now in bot.py
