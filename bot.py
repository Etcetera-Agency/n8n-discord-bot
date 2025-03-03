import os
import discord
import aiohttp
import uuid
import asyncio
import logging
from dotenv import load_dotenv
from cachetools import TTLCache  # For session management with automatic expiration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('discord_bot')

# Load environment variables
load_dotenv()

# Get environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
WEBHOOK_AUTH_TOKEN = os.getenv("WEBHOOK_AUTH_TOKEN")

# Session lifetime: 24 hours (in seconds)
SESSION_TTL = 86400

# Cache to store sessions with automatic expiration
sessions = TTLCache(maxsize=1024, ttl=SESSION_TTL)

# Global HTTP session
http_session = None

def get_session_id(user_id):
    """
    Returns the existing session ID if present,
    otherwise creates a new session that will expire after 24 hours.
    """
    if user_id in sessions:
        return sessions[user_id]
    
    new_session_id = str(uuid.uuid4())
    sessions[user_id] = new_session_id
    return new_session_id

async def send_webhook_with_retry(message, payload, headers, max_retries=3, retry_delay=1):
    """Sends a request to the webhook with retry logic."""
    request_id = str(uuid.uuid4())[:8]  # ID for logging purposes only
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Request {request_id}: Sending to webhook (attempt {attempt+1}/{max_retries})")
            async with http_session.post(
                N8N_WEBHOOK_URL,
                json=payload,
                headers=headers,
                timeout=15
            ) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        # Assume response is a dictionary with an "output" key
                        reply_text = data.get("output", "").strip() if isinstance(data, dict) else ""
                        if not reply_text:
                            reply_text = (await response.text()).strip() or "No response received from n8n."
                    except Exception as e:
                        logger.error(f"Request {request_id}: Error processing response: {e}")
                        reply_text = (await response.text()).strip() or "No response received from n8n."
                    
                    await message.channel.send(reply_text)
                    logger.info(f"Request {request_id}: Successful")
                    return True
                else:
                    logger.warning(f"Request {request_id}: HTTP Error {response.status}")
                    if attempt == max_retries - 1:
                        await message.channel.send(f"Error calling n8n: code {response.status}")
        except Exception as e:
            logger.error(f"Request {request_id}: Attempt {attempt+1} failed: {e}")
            if attempt == max_retries - 1:
                await message.channel.send(f"An error occurred: {e}")
        
        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay * (attempt + 1))
    
    return False

# Discord client setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    global http_session
    logger.info(f"Bot connected as {client.user}")
    
    # Create global HTTP session with connection pooling
    connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
    http_session = aiohttp.ClientSession(connector=connector)

@client.event
async def on_close():
    logger.info("Bot shutting down, cleaning up resources")
    if http_session and not http_session.closed:
        await http_session.close()

@client.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    # Only respond when the bot is mentioned
    if client.user in message.mentions:
        # Add reaction to indicate processing
        await message.add_reaction("⏳")
        
        user_id = str(message.author.id)
        session_id = get_session_id(user_id)
        
        logger.info(f"Processing message from {message.author}")
        
        # Prepare payload for n8n
        payload = {
            "content": message.content,
            "author": str(message.author),
            "userId": user_id,
            "sessionId": session_id,
            "timestamp": int(asyncio.get_event_loop().time())
        }
        
        # Prepare headers including authorization if configured
        headers = {}
        if WEBHOOK_AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {WEBHOOK_AUTH_TOKEN}"
        
        # Send webhook with retry logic
        success = await send_webhook_with_retry(message, payload, headers)
        
        # Update reaction to indicate completion status
        await message.remove_reaction("⏳", client.user)
        await message.add_reaction("✅" if success else "❌")

# Run the bot
client.run(DISCORD_TOKEN)