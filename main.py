import asyncio
from config import Config, logger
from web import create_and_start_server
from bot import bot # Import the bot instance from bot.py

async def main():
    """
    Main entry point for the application.
    Starts both the Discord bot and the web server.
    """
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return
    
    # Bot instance is created in bot.py and imported
    
    # Start web server
    server_task = asyncio.create_task(create_and_start_server(bot))
    
    # Start bot
    try:
        await bot.start(Config.DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        # Wait for server task to complete
        await server_task

if __name__ == "__main__":
    asyncio.run(main()) 