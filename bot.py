import os
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import uuid
import asyncio
import logging
from dotenv import load_dotenv
from cachetools import TTLCache
from typing import Optional, List, Dict, Any, Union, Callable
import ssl
from aiohttp import web

###############################################################################
# Logging configuration
###############################################################################
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('discord_bot')

###############################################################################
# Load environment variables
###############################################################################
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
WEBHOOK_AUTH_TOKEN = os.getenv("WEBHOOK_AUTH_TOKEN")

# Session TTL for user sessions (24 hours)
SESSION_TTL = 86400
sessions = TTLCache(maxsize=1024, ttl=SESSION_TTL)

# Global HTTP session for aiohttp requests
http_session = None

###############################################################################
# Global Constants
###############################################################################
WORKLOAD_OPTIONS = ["Нічого немає", "2", "5", "10", "15", "20", "25", "30", "35", "40", "45", "50"]

WEEKDAY_OPTIONS = [
    discord.SelectOption(label="Monday", value="Monday"),
    discord.SelectOption(label="Tuesday", value="Tuesday"),
    discord.SelectOption(label="Wednesday", value="Wednesday"),
    discord.SelectOption(label="Thursday", value="Thursday"),
    discord.SelectOption(label="Friday", value="Friday"),
    discord.SelectOption(label="Saturday", value="Saturday"),
    discord.SelectOption(label="Sunday", value="Sunday")
]

MONTHS = [
     "January", "February", "March", "April", "May", "June",
     "July", "August", "September", "October", "November", "December"
]

VIEW_TYPES = {
    "dynamic": {"timeout": 900, "has_survey": True},
    "slash": {"timeout": None, "has_survey": False}
}

###############################################################################
# Response Handler Class
###############################################################################
class ResponseHandler:
    @staticmethod
    async def handle_response(
        ctx_or_interaction: Union[commands.Context, discord.Interaction],
        command: str,
        status: str = "ok",
        message: str = "",
        result: Dict[str, Any] = None,
        extra_headers: Dict[str, str] = None
    ) -> tuple:
        """
        Unified handler for sending requests to n8n and processing responses.
        Works with both Context and Interaction objects.
        """
        if result is None:
            result = {}
            
        # Determine if we're dealing with a Context or Interaction
        is_interaction = isinstance(ctx_or_interaction, discord.Interaction)
        
        if is_interaction:
            user = ctx_or_interaction.user
            channel = ctx_or_interaction.channel
            channel_id = str(ctx_or_interaction.channel_id)
        else:
            user = ctx_or_interaction.author
            channel = ctx_or_interaction.channel
            channel_id = str(ctx_or_interaction.channel.id)
            
        user_id = str(user.id)
        session_id = get_session_id(user_id)
        
        # Build the payload
        payload = {
            "command": command,
            "status": status,
            "message": message,
            "result": result,
            "author": str(user),
            "userId": user_id,
            "sessionId": session_id,
            "channelId": channel_id,
            "channelName": getattr(channel, 'name', 'DM'),
            "timestamp": int(asyncio.get_event_loop().time())
        }
        
        # Set up headers
        headers = {}
        if WEBHOOK_AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {WEBHOOK_AUTH_TOKEN}"
        if extra_headers:
            headers.update(extra_headers)
            
        # Send webhook and get response
        success, data = await send_webhook_with_retry(ctx_or_interaction, payload, headers)
        
        # If successful, send the reply via the appropriate channel
        if success and data:
            if is_interaction:
                await send_n8n_reply_interaction(ctx_or_interaction, data)
            else:
                await send_n8n_reply_channel(channel, data)
                
        return success, data

###############################################################################
# Session and Webhook Helper Functions
###############################################################################
def get_session_id(user_id: str) -> str:
    """Returns an existing session_id or creates a new one for the given user."""
    if user_id in sessions:
        return sessions[user_id]
    new_session_id = str(uuid.uuid4())
    sessions[user_id] = new_session_id
    return new_session_id

async def send_webhook_with_retry(target_channel, payload, headers, max_retries=3, retry_delay=1):
    """Sends a POST request to n8n with retry logic. Returns (success, data)."""
    request_id = str(uuid.uuid4())[:8]
    for attempt in range(max_retries):
        try:
            logger.info(f"[{request_id}] Sending to n8n (attempt {attempt+1}/{max_retries})")
            async with http_session.post(
                N8N_WEBHOOK_URL,
                json=payload,
                headers=headers,
                timeout=15
            ) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        return True, data
                    except Exception as e:
                        logger.error(f"[{request_id}] JSON parse error: {e}")
                        fallback = (await response.text()).strip()
                        return True, {"output": fallback or "No valid JSON from n8n."}
                else:
                    logger.warning(f"[{request_id}] HTTP Error {response.status}")
                    if attempt == max_retries - 1:
                        if hasattr(target_channel, "channel"):
                            await target_channel.channel.send(f"Error calling n8n: code {response.status}")
                        else:
                            await send_error_message(target_channel, f"Error calling n8n: code {response.status}")
        except Exception as e:
            logger.error(f"[{request_id}] Attempt {attempt+1} failed: {e}")
            if attempt == max_retries - 1:
                if hasattr(target_channel, "channel"):
                    await target_channel.channel.send(f"An error occurred: {e}")
                else:
                    await send_error_message(target_channel, f"An error occurred: {e}")
        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay * (attempt + 1))
    return False, None

async def send_error_message(target, message):
    """Send error message to appropriate destination based on object type."""
    if isinstance(target, discord.Interaction):
        if target.response.is_done():
            await target.followup.send(message, ephemeral=False)
        else:
            await target.response.send_message(message, ephemeral=False)
    else:
        await target.send(message)

async def send_n8n_reply_channel(channel, data):
    """Sends n8n response to a text channel."""
    if data and "output" in data:
        await channel.send(data["output"])

async def send_n8n_reply_interaction(interaction, data):
    """Sends n8n response to an interaction."""
    if data and "output" in data:
        if interaction.response.is_done():
            await interaction.followup.send(data["output"], ephemeral=False)
        else:
            await interaction.response.send_message(data["output"], ephemeral=False)

async def send_button_pressed_info(interaction: discord.Interaction, button_or_select: Union[discord.ui.Button, discord.ui.Select]):
    """Sends to n8n the information about which button/select was pressed."""
    # Get appropriate attributes for different UI elements
    if isinstance(button_or_select, discord.ui.Button):
        item_info = {"label": button_or_select.label, "custom_id": button_or_select.custom_id}
    elif isinstance(button_or_select, discord.ui.Select):
        item_info = {"placeholder": button_or_select.placeholder, "custom_id": button_or_select.custom_id, "values": button_or_select.values}
    else:
        item_info = {"type": str(type(button_or_select))}
    
    await ResponseHandler.handle_response(
        interaction,
        command="button_pressed",
        result=item_info
    )
    logger.info(f"UI element info sent: {item_info}, user: {interaction.user}")

###############################################################################
# Discord Bot Setup
###############################################################################
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    global http_session
    logger.info(f"Bot connected as {bot.user}")
    connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
    http_session = aiohttp.ClientSession(connector=connector)
    try:
        await bot.tree.sync()
        logger.info("Slash commands synced!")
    except Exception as e:
        logger.error(f"Error syncing slash commands: {e}")

@bot.event
async def on_close():
    logger.info("Bot shutting down, cleaning up resources")
    if http_session and not http_session.closed:
        await http_session.close()

###############################################################################
# Survey Management
###############################################################################
SURVEYS = {}

class SurveyFlow:
    """Holds a list of survey steps for dynamic surveys."""
    def __init__(self, user_id: str, channel_id: str, steps: List[str]):
        self.user_id = user_id
        self.channel_id = channel_id
        self.steps = steps
        self.current_index = 0
        self.results = {}

    def current_step(self) -> Optional[str]:
        if self.current_index < len(self.steps):
            return self.steps[self.current_index]
        return None

    def next_step(self):
        self.current_index += 1

    def is_done(self) -> bool:
        return self.current_index >= len(self.steps)

    def incomplete_steps(self) -> List[str]:
        return self.steps[self.current_index:] if not self.is_done() else []

async def survey_incomplete_timeout(user_id: str):
    state = SURVEYS.get(user_id)
    if not state:
        return
    channel = bot.get_channel(int(state.channel_id))
    if not channel:
        return
    
    incomplete = state.incomplete_steps()
    await ResponseHandler.handle_response(
        channel,
        command="survey",
        status="incomplete",
        result={"incompleteSteps": incomplete}
    )
    
    if state.user_id in SURVEYS:
        del SURVEYS[state.user_id]

async def handle_start_daily_survey(user_id: str, channel_id: str, steps: List[str]):
    channel = bot.get_channel(int(channel_id))
    if not channel:
        logger.warning(f"Channel {channel_id} not found for user {user_id}")
        return

    # Check if channel is registered
    success_check, data_check = await ResponseHandler.handle_response(
        channel,
        command="registred_channel",
        result={}
    )
    
    if not success_check or not data_check:
        await channel.send(f"<@{user_id}> Помилка перевірки реєстрації каналу.")
        return
        
    is_registered = str(data_check.get("output", "false")).lower() == "true"
    if not is_registered:
        await channel.send(f"<@{user_id}> Канал не зареєстровано. Будь ласка, зареєструйте його перед початком опитування.")
        return

    state = SurveyFlow(user_id, channel_id, steps)
    SURVEYS[user_id] = state
    step = state.current_step()
    if step:
        await ask_dynamic_step(channel, state, step)
    else:
        await channel.send(f"<@{user_id}> Не вказано кроків опитування.")

async def ask_dynamic_step(channel: discord.TextChannel, state: SurveyFlow, step_name: str):
    user_id = state.user_id
    if step_name.startswith("workload") or step_name.startswith("connects"):
        if step_name == "workload_nextweek":
            text_q = f"<@{user_id}> Скільки годин на НАСТУПНИЙ тиждень?"
        elif step_name == "workload_thisweek":
            text_q = f"<@{user_id}> Скільки годин на ЦЬОГО тижня?"
        elif step_name == "connects_thisweek":
            text_q = f"<@{user_id}> Скільки CONNECTS на ЦЬОГО тижня?"
        else:
            text_q = f"<@{user_id}> Будь ласка, оберіть кількість годин:"
        view = create_view("workload", step_name, user_id, "dynamic")
        await channel.send(text_q, view=view)
    elif step_name.startswith("day_off"):
        text_q = f"<@{user_id}> Які дні вихідних на наступний тиждень?"
        view = create_view("day_off", step_name, user_id, "dynamic")
        await channel.send(text_q, view=view)
    else:
        await channel.send(f"<@{user_id}> Невідомий крок опитування: {step_name}. Пропускаємо.")
        state.next_step()
        nxt = state.current_step()
        if nxt:
            await ask_dynamic_step(channel, state, nxt)
        else:
            await finish_survey(channel, state)

async def finish_survey(channel: discord.TextChannel, state: SurveyFlow):
    if state.is_done():
        await ResponseHandler.handle_response(
            channel,
            command="survey",
            result={"final": state.results}
        )
    if state.user_id in SURVEYS:
        del SURVEYS[state.user_id]

###############################################################################
# UI Component Factory
###############################################################################
def create_view(view_name: str, cmd_or_step: str, user_id: str, view_type: str = "slash") -> discord.ui.View:
    """Factory function to create the appropriate view type."""
    config = VIEW_TYPES.get(view_type, VIEW_TYPES["slash"])
    
    if view_name == "workload":
        view = WorkloadView(cmd_or_step, user_id, config["timeout"], config["has_survey"])
        for opt in WORKLOAD_OPTIONS:
            view.add_item(WorkloadButton(opt, view))
        return view
    elif view_name == "day_off":
        view = DayOffView(cmd_or_step, user_id, config["timeout"], config["has_survey"])
        view.add_item(DayOffSelect(view))
        view.add_item(DayOffSubmitButton(view))
        return view
    
    return discord.ui.View(timeout=config["timeout"])

###############################################################################
# Base View and UI Components
###############################################################################
class BaseView(discord.ui.View):
    def __init__(self, cmd_or_step: str, user_id: str, timeout: int = None, has_survey: bool = False):
        super().__init__(timeout=timeout)
        self.cmd_or_step = cmd_or_step
        self.user_id = user_id
        self.session_id = get_session_id(user_id)
        self.has_survey = has_survey
        self.data = {}  # Store all selected data here
    
    def disable_all_items(self):
        for item in self.children:
            item.disabled = True
    
    async def on_timeout(self):
        if self.has_survey:
            await survey_incomplete_timeout(self.user_id)
        self.disable_all_items()
        self.stop()

class WorkloadView(BaseView):
    pass

class WorkloadButton(discord.ui.Button):
    def __init__(self, label: str, parent_view: WorkloadView):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        await send_button_pressed_info(interaction, self)
        
        # Extract value from label
        value = 0 if self.label == "Нічого немає" else int(self.label)
        
        if self.parent_view.has_survey:
            # Dynamic survey flow handling
            state = SURVEYS.get(self.parent_view.user_id)
            if not state:
                await interaction.response.send_message("Опитування не знайдено.", ephemeral=False)
                return
                
            success, _ = await ResponseHandler.handle_response(
                interaction, 
                command="survey",
                status="step",
                result={"stepName": self.parent_view.cmd_or_step, "value": value}
            )
            
            if not success:
                await interaction.response.send_message("Помилка виклику n8n.", ephemeral=False)
                return
            
            state.results[self.parent_view.cmd_or_step] = value
            state.next_step()
            nxt = state.current_step()
            
            if nxt:
                await ask_dynamic_step(interaction.channel, state, nxt)
            else:
                await finish_survey(interaction.channel, state)
        else:
            # Regular slash command handling
            await ResponseHandler.handle_response(
                interaction,
                command=self.parent_view.cmd_or_step,
                result={"hours": value}
            )
        
        self.parent_view.disable_all_items()
        self.parent_view.stop()

class DayOffView(BaseView):
    def __init__(self, cmd_or_step: str, user_id: str, timeout: int = None, has_survey: bool = False):
        super().__init__(cmd_or_step, user_id, timeout, has_survey)
        self.days_selected = []

class DayOffSelect(discord.ui.Select):
    def __init__(self, parent_view: DayOffView):
        super().__init__(placeholder="Оберіть день(і) вихідних", min_values=1, max_values=7, options=WEEKDAY_OPTIONS)
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        await send_button_pressed_info(interaction, self)
        self.parent_view.days_selected = self.values
        await interaction.response.defer()

class DayOffSubmitButton(discord.ui.Button):
    def __init__(self, parent_view: DayOffView):
        super().__init__(label="Відправити дні", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        await send_button_pressed_info(interaction, self)
        
        if not self.parent_view.days_selected:
            await interaction.response.send_message("Дні не обрано.", ephemeral=False)
            return
        
        if self.parent_view.has_survey:
            # Dynamic survey flow
            state = SURVEYS.get(self.parent_view.user_id)
            if not state:
                await interaction.response.send_message("Опитування не знайдено.", ephemeral=False)
                return
            
            success, _ = await ResponseHandler.handle_response(
                interaction,
                command="survey",
                status="step",
                result={"stepName": self.parent_view.cmd_or_step, "daysSelected": self.parent_view.days_selected}
            )
            
            if not success:
                await interaction.response.send_message("Помилка виклику n8n.", ephemeral=False)
                return
            
            state.results[self.parent_view.cmd_or_step] = self.parent_view.days_selected
            state.next_step()
            nxt = state.current_step()
            
            if nxt:
                await ask_dynamic_step(interaction.channel, state, nxt)
            else:
                await finish_survey(interaction.channel, state)
        else:
            # Regular slash command
            await ResponseHandler.handle_response(
                interaction,
                command=self.parent_view.cmd_or_step,
                result={"daysSelected": self.parent_view.days_selected}
            )
        
        self.parent_view.disable_all_items()
        self.parent_view.stop()

class GenericSelect(discord.ui.Select):
    def __init__(self, parent_view: BaseView, field_name: str, placeholder: str, options: List[discord.SelectOption]):
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)
        self.parent_view = parent_view
        self.field_name = field_name
    
    async def callback(self, interaction: discord.Interaction):
        await send_button_pressed_info(interaction, self)
        self.parent_view.data[self.field_name] = self.values[0]
        await interaction.response.defer()

###############################################################################
# Discord on_message Event
###############################################################################
@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    if bot.user in message.mentions:
        await message.add_reaction("⏳")
        success, _ = await ResponseHandler.handle_response(
            message,
            command="mention",
            message=message.content,
            result={}
        )
        await message.add_reaction("✅" if success else "❌")

    if message.content.startswith("start_daily_survey"):
        parts = message.content.split()
        if len(parts) >= 4:
            user_id = parts[1]
            channel_id = parts[2]
            steps = parts[3:]
            await handle_start_daily_survey(user_id, channel_id, steps)

    await bot.process_commands(message)

###############################################################################
# PREFIX COMMANDS
###############################################################################
@bot.command(name="register", help="Використання: !register <будь-який текст>")
async def register_cmd(ctx: commands.Context, *, text: str):
    await ResponseHandler.handle_response(
        ctx,
        command="register",
        result={"text": text}
    )

@bot.command(name="unregister", help="Використання: !unregister")
async def unregister_cmd(ctx: commands.Context):
    await ResponseHandler.handle_response(
        ctx,
        command="unregister",
        result={}
    )

###############################################################################
# SLASH COMMANDS
###############################################################################
day_off_group = app_commands.Group(name="day_off", description="Команди для вихідних")

@day_off_group.command(name="thisweek", description="Оберіть вихідні на ЦЕЙ тиждень.")
async def day_off_thisweek(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=False)
    view = create_view("day_off", "day_off_thisweek", str(interaction.user.id))
    await interaction.followup.send("Оберіть свої вихідні (цей тиждень), потім натисніть «Відправити»:", view=view, ephemeral=False)

@day_off_group.command(name="nextweek", description="Оберіть вихідні на НАСТУПНИЙ тиждень.")
async def day_off_nextweek(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=False)
    view = create_view("day_off", "day_off_nextweek", str(interaction.user.id))
    await interaction.followup.send("Оберіть свої вихідні (наступний тиждень), потім натисніть «Відправити»:", view=view, ephemeral=False)

bot.tree.add_command(day_off_group)

@bot.tree.command(name="vacation", description="Вкажіть день/місяць початку та кінця відпустки.")
@app_commands.describe(
    start_day="День початку відпустки (1-31)",
    start_month="Місяць початку відпустки",
    end_day="День закінчення відпустки (1-31)",
    end_month="Місяць закінчення відпустки"
)
async def vacation_slash(
    interaction: discord.Interaction, 
    start_day: int,
    start_month: str,
    end_day: int,
    end_month: str
):
    # Validate inputs
    if not (1 <= start_day <= 31) or not (1 <= end_day <= 31):
        await interaction.response.send_message("День повинен бути між 1 та 31.", ephemeral=False)
        return
    
    # Process vacation request
    await ResponseHandler.handle_response(
        interaction,
        command="vacation",
        result={
            "start_day": str(start_day),
            "start_month": start_month,
            "end_day": str(end_day),
            "end_month": end_month
        }
    )
@vacation_slash.autocomplete("start_month")
@vacation_slash.autocomplete("end_month")
async def month_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    current = current.lower()
    return [
        app_commands.Choice(name=month, value=month)
        for month in MONTHS
        if current in month.lower()
    ][:25]  # Limit to 25 choices as per Discord limits
    
@bot.tree.command(name="workload_today", description="Скільки годин підтверджено з СЬОГОДНІ до кінця тижня?")
async def slash_workload_today(interaction: discord.Interaction):
    view = create_view("workload", "workload_today", str(interaction.user.id))
    await interaction.response.send_message("Скільки годин підтверджено з СЬОГОДНІ до кінця тижня?\nЯкщо нічого, оберіть «Нічого немає».", view=view, ephemeral=False)

@bot.tree.command(name="workload_nextweek", description="Скільки годин підтверджено на НАСТУПНИЙ тиждень?")
async def slash_workload_nextweek(interaction: discord.Interaction):
    view = create_view("workload", "workload_nextweek", str(interaction.user.id))
    await interaction.response.send_message("Скільки годин підтверджено на НАСТУПНИЙ тиждень?\nЯкщо нічого, оберіть «Нічого немає».", view=view, ephemeral=False)

@bot.tree.command(name="connects_thisweek", description="Скільки CONNECTS Upwork Connects History показує ЦЬОГО тижня?")
async def slash_connects_thisweek(interaction: discord.Interaction, connects: int):
    await ResponseHandler.handle_response(
        interaction,
        command="connects_thisweek",
        result={"connects": connects}
    )

###############################################################################
# HTTP/HTTPS Server for Survey Activation (CapRover)
###############################################################################
async def start_survey_http(request):
    auth_header = request.headers.get("Authorization")
    expected_header = f"Bearer {WEBHOOK_AUTH_TOKEN}"
    if not auth_header or auth_header != expected_header:
        return web.json_response({"error": "Unauthorized"}, status=401)
    
    try:
        data = await request.json()
        user_id = data.get("userId")
        channel_id = data.get("channelId")
        steps = data.get("steps", [])
        
        if not user_id or not channel_id or not steps:
            return web.json_response({"error": "Missing parameters"}, status=400)

        channel = bot.get_channel(int(channel_id))
        if not channel:
            return web.json_response({"error": "Channel not found"}, status=404)
            
        # Check if channel is registered
        payload = {
            "command": "registered_channel",
            "status": "ok",
            "message": "",
            "result": {},
            "author": "",
            "userId": user_id,
            "sessionId": get_session_id(user_id),
            "channelId": channel_id,
            "channelName": getattr(channel, 'name', 'Unknown')
        }
        headers = {"Authorization": f"Bearer {WEBHOOK_AUTH_TOKEN}"} if WEBHOOK_AUTH_TOKEN else {}
        
        success_check, data_check = await send_webhook_with_retry(None, payload, headers)
        if not success_check or str(data_check.get("output", "false")).lower() != "true":
            return web.json_response({"error": "Channel is not registered"}, status=403)

        await handle_start_daily_survey(user_id, channel_id, steps)
        return web.json_response({"status": "Survey started"})
    
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def run_server():
    app = web.Application()
    app.router.add_post('/start_survey', start_survey_http)
    port = int(os.getenv("PORT", "3000"))
    host = "0.0.0.0"
    ssl_cert_path = os.getenv("SSL_CERT_PATH")
    ssl_key_path = os.getenv("SSL_KEY_PATH")
    ssl_context = None     
    if ssl_cert_path and ssl_key_path:         
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile=ssl_cert_path, keyfile=ssl_key_path)
        logger.info(f"Starting HTTPS server on {host}:{port}")     
    else:
        logger.info(f"Starting HTTP server on {host}:{port}")
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port, ssl_context=ssl_context)
        await site.start()
###############################################################################
# Main function to run both the HTTP/HTTPS server and the Discord Bot (English) 
###############################################################################
async def main():     
    server_task = asyncio.create_task(run_server())
    await bot.start(DISCORD_TOKEN)
    await server_task  
if __name__ == "__main__":
    asyncio.run(main())
