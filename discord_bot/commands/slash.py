from discord.ext import commands


async def setup_slash_cogs(bot: commands.Bot) -> None:
    """Load and register slash command cogs.

    This trims the legacy monolithic slash.py into a thin loader that wires
    domain-specific cogs responsible for slash commands.
    """
    # Import locally to avoid import cycles at import time
    from .cogs.day_off import DayOffCog
    from .cogs.workload import WorkloadCog
    from .cogs.connects import ConnectsCog
    from .cogs.vacation import VacationCog

    await bot.add_cog(DayOffCog(bot))
    await bot.add_cog(WorkloadCog(bot))
    await bot.add_cog(ConnectsCog(bot))
    await bot.add_cog(VacationCog(bot))
