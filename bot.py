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
from typing import Optional, List
import ssl
from aiohttp import web

###############################################################################
# Logging configuration (English)
###############################################################################
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('discord_bot')

###############################################################################
# Load environment variables (English)
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

###############################################################################
# Helper: create_view_from_components (English)
###############################################################################
def create_view_from_components(components: List[dict]) -> discord.ui.View:
    """Converts a list of component dicts from n8n into a discord.ui.View with buttons."""
    view = discord.ui.View(timeout=None)
    row = 0
    count = 0
    for comp in components:
        if count == 5:
            row += 1
            count = 0
        style_str = comp.get("style", "primary").lower()
        style = discord.ButtonStyle.primary
        if style_str == "secondary":
            style = discord.ButtonStyle.secondary
        elif style_str == "success":
            style = discord.ButtonStyle.success
        elif style_str == "danger":
            style = discord.ButtonStyle.danger
        elif style_str == "link":
            style = discord.ButtonStyle.link
        button = discord.ui.Button(
            label=comp.get("label", "Button"),
            style=style,
            custom_id=comp.get("custom_id"),
            row=row
        )
        view.add_item(button)
        count += 1
    return view

###############################################################################
# Helper: send_n8n_reply for channels and interactions (English)
###############################################################################
async def send_n8n_reply_channel(channel, data: dict):
    """Sends the reply from n8n to a text channel. If 'components' exists, sends buttons."""
    reply_text = data.get("output", "").strip()
    if "components" in data:
        view = create_view_from_components(data["components"])
        await channel.send(reply_text, view=view)
    else:
        if reply_text:
            await channel.send(reply_text)

async def send_n8n_reply_interaction(interaction, data: dict):
    """Sends the reply from n8n to an interaction. If 'components' exists, sends buttons."""
    reply_text = data.get("output", "").strip()
    if "components" in data:
        view = create_view_from_components(data["components"])
        await interaction.response.send_message(reply_text, view=view, ephemeral=False)
    else:
        if reply_text:
            await interaction.response.send_message(reply_text, ephemeral=False)

###############################################################################
# Utility: build_payload (English)
###############################################################################
def build_payload(
    command: str,
    status: str,
    message: str,
    result: dict,
    author: str,
    userId: str,
    sessionId: str,
    channelId: str,
    channelName: str
) -> dict:
    """Constructs a unified JSON payload to send to n8n."""
    return {
        "command": command,
        "status": status,
        "message": message,
        "result": result,
        "author": author,
        "userId": userId,
        "sessionId": sessionId,
        "channelId": channelId,
        "channelName": channelName,
        "timestamp": int(asyncio.get_event_loop().time())
    }

###############################################################################
# Helper: get_session_id (English)
###############################################################################
def get_session_id(user_id: str) -> str:
    """Returns an existing session_id or creates a new one for the given user."""
    if user_id in sessions:
        return sessions[user_id]
    new_session_id = str(uuid.uuid4())
    sessions[user_id] = new_session_id
    return new_session_id

###############################################################################
# Send webhook with retry logic (English)
###############################################################################
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
                            await target_channel.response.send_message(
                                f"Error calling n8n: code {response.status}",
                                ephemeral=False
                            )
        except Exception as e:
            logger.error(f"[{request_id}] Attempt {attempt+1} failed: {e}")
            if attempt == max_retries - 1:
                if hasattr(target_channel, "channel"):
                    await target_channel.channel.send(f"An error occurred: {e}")
                else:
                    await target_channel.response.send_message(
                        f"An error occurred: {e}", ephemeral=False
                    )
        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay * (attempt + 1))
    return False, None

###############################################################################
# Discord Bot Setup (English)
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
# Survey Management (English)
###############################################################################
SURVEYS = {}

class SurveyFlow:
    """
    Holds a list of survey steps (for dynamic surveys).
    Example: steps = ["workload_nextweek", "connects_thisweek", "day_off_nextweek"]
    """
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

###############################################################################
# Discord on_message Event (User messages in Ukrainian)
###############################################################################
@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    if bot.user in message.mentions:
        await message.add_reaction("⏳")
        user_id = str(message.author.id)
        session_id = get_session_id(user_id)
        payload = build_payload(
            command="mention",
            status="ok",
            message=message.content,
            result={},
            author=str(message.author),
            userId=user_id,
            sessionId=session_id,
            channelId=str(message.channel.id),
            channelName=getattr(message.channel, 'name', 'DM')
        )
        headers = {}
        if WEBHOOK_AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {WEBHOOK_AUTH_TOKEN}"
        success, data = await send_webhook_with_retry(message, payload, headers)
        await message.add_reaction("✅" if success else "❌")
        if success and data:
            await send_n8n_reply_channel(message.channel, data)

    if message.content.startswith("start_daily_survey"):
        parts = message.content.split()
        if len(parts) >= 4:
            user_id = parts[1]
            channel_id = parts[2]
            steps = parts[3:]
            await handle_start_daily_survey(user_id, channel_id, steps)

    await bot.process_commands(message)

###############################################################################
# Survey Functions (User messages in Ukrainian)
###############################################################################
async def handle_start_daily_survey(user_id: str, channel_id: str, steps: List[str]):
    channel = bot.get_channel(int(channel_id))
    if not channel:
        logger.warning(f"Channel {channel_id} not found for user {user_id}")
        return

    payload_check = build_payload(
        command="registred_channel",
        status="ok",
        message="",
        result={},
        author="",
        userId=user_id,
        sessionId=get_session_id(user_id),
        channelId=channel_id,
        channelName=getattr(channel, 'name', 'DM')
    )
    headers = {}
    if WEBHOOK_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {WEBHOOK_AUTH_TOKEN}"
    success_check, data_check = await send_webhook_with_retry(channel, payload_check, headers)
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
        view = create_workload_view(step_name, user_id, dynamic_survey=True)
        await channel.send(text_q, view=view)
    elif step_name.startswith("day_off"):
        text_q = f"<@{user_id}> Які дні вихідних на наступний тиждень?"
        view = create_day_off_view(step_name, user_id, dynamic_survey=True)
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
        payload = build_payload(
            command="survey",
            status="ok",
            message="",
            result={"final": state.results},
            author="",
            userId=state.user_id,
            sessionId=get_session_id(state.user_id),
            channelId=str(channel.id),
            channelName=getattr(channel, 'name', 'DM')
        )
        headers = {}
        if WEBHOOK_AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {WEBHOOK_AUTH_TOKEN}"
        success, data = await send_webhook_with_retry(channel, payload, headers)
        if success and data:
            await send_n8n_reply_channel(channel, data)
        else:
            await channel.send("Помилка надсилання результатів до n8n.")
    if state.user_id in SURVEYS:
        del SURVEYS[state.user_id]

async def survey_incomplete_timeout(user_id: str):
    state = SURVEYS.get(user_id)
    if not state:
        return
    channel = bot.get_channel(int(state.channel_id))
    if not channel:
        return
    incomplete = state.incomplete_steps()
    payload = build_payload(
        command="survey",
        status="incomplete",
        message="",
        result={"incompleteSteps": incomplete},
        author="",
        userId=state.user_id,
        sessionId=get_session_id(state.user_id),
        channelId=str(channel.id),
        channelName=getattr(channel, 'name', 'DM')
    )
    headers = {}
    if WEBHOOK_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {WEBHOOK_AUTH_TOKEN}"
    success, data = await send_webhook_with_retry(channel, payload, headers)
    if success and data:
        await send_n8n_reply_channel(channel, data)
    else:
        await channel.send(f"<@{state.user_id}> {', '.join(incomplete)}")
    if state.user_id in SURVEYS:
        del SURVEYS[state.user_id]

###############################################################################
# Factory Functions for UI Views (User messages in Ukrainian)
###############################################################################
def create_workload_view(step_or_cmd: str, user_id: str, dynamic_survey: bool = False) -> discord.ui.View:
    if dynamic_survey:
        return WorkloadDynamicView(step_or_cmd, user_id)
    else:
        return WorkloadSlashView(step_or_cmd, user_id, get_session_id(user_id))

def create_day_off_view(step_or_cmd: str, user_id: str, dynamic_survey: bool = False) -> discord.ui.View:
    if dynamic_survey:
        return DayOffDynamicView(step_or_cmd, user_id)
    else:
        return DayOffSlashView(step_or_cmd, user_id, get_session_id(user_id))

def create_vacation_view(slash_command_name: str, user_id: str) -> discord.ui.View:
    return VacationSlashView(slash_command_name, user_id, get_session_id(user_id))

###############################################################################
# WORKLOAD VIEWS (Dynamic and Slash) (User messages in Ukrainian)
###############################################################################
class WorkloadDynamicView(discord.ui.View):
    def __init__(self, step_name: str, user_id: str):
        super().__init__(timeout=900)
        self.step_name = step_name
        self.user_id = user_id
        for opt in WORKLOAD_OPTIONS:
            self.add_item(WorkloadDynamicButton(opt, self))

    async def on_timeout(self):
        await survey_incomplete_timeout(self.user_id)
        for c in self.children:
            c.disabled = True
        self.stop()

class WorkloadDynamicButton(discord.ui.Button):
    def __init__(self, label: str, parent_view: WorkloadDynamicView):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        value = 0 if self.label == "Нічого немає" else int(self.label)
        state = SURVEYS.get(self.parent_view.user_id)
        if not state:
            await interaction.response.send_message("Опитування не знайдено.", ephemeral=False)
            return
        payload = build_payload(
            command="survey",
            status="step",
            message="",
            result={"stepName": self.parent_view.step_name, "value": value},
            author=str(interaction.user),
            userId=self.parent_view.user_id,
            sessionId=get_session_id(self.parent_view.user_id),
            channelId=str(interaction.channel_id),
            channelName=getattr(interaction.channel, 'name', 'DM')
        )
        headers = {}
        if WEBHOOK_AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {WEBHOOK_AUTH_TOKEN}"
        success, data = await send_webhook_with_retry(interaction, payload, headers)
        if not success or not data:
            await interaction.response.send_message("Помилка виклику n8n.", ephemeral=False)
            return
        await send_n8n_reply_interaction(interaction, data)
        state.results[self.parent_view.step_name] = value
        state.next_step()
        nxt = state.current_step()
        if nxt:
            await ask_dynamic_step(interaction.channel, state, nxt)
        else:
            await finish_survey(interaction.channel, state)
        for c in self.parent_view.children:
            c.disabled = True
        self.parent_view.stop()

class WorkloadSlashView(discord.ui.View):
    def __init__(self, slash_cmd_name: str, user_id: str, session_id: str, timeout=None):
        super().__init__(timeout=timeout)
        self.slash_cmd_name = slash_cmd_name
        self.user_id = user_id
        self.session_id = session_id
        for label in WORKLOAD_OPTIONS:
            self.add_item(WorkloadSlashButton(label, self))

    def disable_all_items(self):
        for c in self.children:
            c.disabled = True

class WorkloadSlashButton(discord.ui.Button):
    def __init__(self, label: str, parent_view: WorkloadSlashView):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        hours_value = 0 if self.label == "Нічого немає" else int(self.label)
        payload = build_payload(
            command=self.parent_view.slash_cmd_name,
            status="ok",
            message="",
            result={"hours": hours_value},
            author=str(interaction.user),
            userId=self.parent_view.user_id,
            sessionId=self.parent_view.session_id,
            channelId=str(interaction.channel_id),
            channelName=getattr(interaction.channel, 'name', 'DM')
        )
        headers = {}
        if WEBHOOK_AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {WEBHOOK_AUTH_TOKEN}"
        success, data = await send_webhook_with_retry(interaction, payload, headers)
        if not success or not data:
            return
        await send_n8n_reply_interaction(interaction, data)
        self.parent_view.disable_all_items()
        self.parent_view.stop()

###############################################################################
# DAY OFF VIEWS (Dynamic and Slash) (User messages in Ukrainian)
###############################################################################
class DayOffDynamicView(discord.ui.View):
    def __init__(self, step_name: str, user_id: str):
        super().__init__(timeout=900)
        self.step_name = step_name
        self.user_id = user_id
        self.days_selected = []
        self.add_item(DayOffDynamicSelect(self))
        self.add_item(DayOffDynamicSubmit(self))

    async def on_timeout(self):
        await survey_incomplete_timeout(self.user_id)
        for c in self.children:
            c.disabled = True
        self.stop()

class DayOffDynamicSelect(discord.ui.Select):
    def __init__(self, parent_view: DayOffDynamicView):
        self.parent_view = parent_view
        super().__init__(placeholder="Оберіть день(і) вихідних", min_values=1, max_values=7, options=WEEKDAY_OPTIONS)
    async def callback(self, interaction: discord.Interaction):
        self.parent_view.days_selected = self.values
        await interaction.response.defer()

class DayOffDynamicSubmit(discord.ui.Button):
    def __init__(self, parent_view: DayOffDynamicView):
        super().__init__(label="Відправити дні", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view
    async def callback(self, interaction: discord.Interaction):
        if not self.parent_view.days_selected:
            await interaction.response.send_message("Дні не обрано.", ephemeral=False)
            return
        state = SURVEYS.get(self.parent_view.user_id)
        if not state:
            await interaction.response.send_message("Опитування не знайдено.", ephemeral=False)
            return
        payload = build_payload(
            command="survey",
            status="step",
            message="",
            result={"incompleteSteps": self.parent_view.days_selected},
            author=str(interaction.user),
            userId=self.parent_view.user_id,
            sessionId=get_session_id(self.parent_view.user_id),
            channelId=str(interaction.channel_id),
            channelName=getattr(interaction.channel, 'name', 'DM')
        )
        headers = {}
        if WEBHOOK_AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {WEBHOOK_AUTH_TOKEN}"
        success, data = await send_webhook_with_retry(interaction, payload, headers)
        if not success or not data:
            await interaction.response.send_message("Помилка виклику n8n.", ephemeral=False)
            return
        await send_n8n_reply_interaction(interaction, data)
        state.results[self.parent_view.step_name] = self.parent_view.days_selected
        state.next_step()
        nxt = state.current_step()
        if nxt:
            await ask_dynamic_step(interaction.channel, state, nxt)
        else:
            await finish_survey(interaction.channel, state)
        for c in self.parent_view.children:
            c.disabled = True
        self.parent_view.stop()

class DayOffSlashView(discord.ui.View):
    def __init__(self, slash_cmd_name: str, user_id: str, session_id: str):
        super().__init__(timeout=None)
        self.slash_cmd_name = slash_cmd_name
        self.user_id = user_id
        self.session_id = session_id
        self.days_selected = []
        self.add_item(DayOffSlashSelect(self))
        self.add_item(DayOffSlashButton(self))
    def disable_all_items(self):
        for c in self.children:
            c.disabled = True

class DayOffSlashSelect(discord.ui.Select):
    def __init__(self, parent_view: DayOffSlashView):
        self.parent_view = parent_view
        super().__init__(placeholder="Оберіть день(і) вихідних...", min_values=1, max_values=7, options=WEEKDAY_OPTIONS)
    async def callback(self, interaction: discord.Interaction):
        self.parent_view.days_selected = self.values
        await interaction.response.defer()

class DayOffSlashButton(discord.ui.Button):
    def __init__(self, parent_view: DayOffSlashView):
        super().__init__(label="Відправити", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view
    async def callback(self, interaction: discord.Interaction):
        if not self.parent_view.days_selected:
            await interaction.response.send_message("Дні не обрано!", ephemeral=False)
            return
        payload = build_payload(
            command=self.parent_view.slash_cmd_name,
            status="ok",
            message="",
            result={"daysSelected": self.parent_view.days_selected},
            author=str(interaction.user),
            userId=self.parent_view.user_id,
            sessionId=self.parent_view.session_id,
            channelId=str(interaction.channel_id),
            channelName=getattr(interaction.channel, 'name', 'DM')
        )
        headers = {}
        if WEBHOOK_AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {WEBHOOK_AUTH_TOKEN}"
        success, data = await send_webhook_with_retry(interaction, payload, headers)
        if not success or not data:
            return
        await send_n8n_reply_interaction(interaction, data)
        self.parent_view.disable_all_items()
        self.parent_view.stop()

###############################################################################
# VACATION SLASH VIEW (Static) (User messages in Ukrainian)
###############################################################################
def day_options():
    return [discord.SelectOption(label=str(d), value=str(d)) for d in range(1, 32)]

def month_options():
    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    return [discord.SelectOption(label=f"{i} - {n}", value=str(i)) for i, n in enumerate(month_names, start=1)]

class VacationSlashView(discord.ui.View):
    def __init__(self, slash_cmd_name: str, user_id: str, session_id: str, timeout=None):
        super().__init__(timeout=timeout)
        self.slash_cmd_name = slash_cmd_name
        self.user_id = user_id
        self.session_id = session_id
        self.start_day = None
        self.start_month = None
        self.end_day = None
        self.end_month = None
        self.add_item(StartDaySelect(self))
        self.add_item(StartMonthSelect(self))
        self.add_item(EndDaySelect(self))
        self.add_item(EndMonthSelect(self))
        self.add_item(VacationSlashButton(self))
    def disable_all_items(self):
        for c in self.children:
            c.disabled = True

class StartDaySelect(discord.ui.Select):
    def __init__(self, parent_view: VacationSlashView):
        super().__init__(placeholder="День початку", min_values=1, max_values=1, options=day_options())
        self.parent_view = parent_view
    async def callback(self, interaction: discord.Interaction):
        self.parent_view.start_day = self.values[0]
        await interaction.response.defer()

class StartMonthSelect(discord.ui.Select):
    def __init__(self, parent_view: VacationSlashView):
        super().__init__(placeholder="Місяць початку", min_values=1, max_values=1, options=month_options())
        self.parent_view = parent_view
    async def callback(self, interaction: discord.Interaction):
        self.parent_view.start_month = self.values[0]
        await interaction.response.defer()

class EndDaySelect(discord.ui.Select):
    def __init__(self, parent_view: VacationSlashView):
        super().__init__(placeholder="День закінчення", min_values=1, max_values=1, options=day_options())
        self.parent_view = parent_view
    async def callback(self, interaction: discord.Interaction):
        self.parent_view.end_day = self.values[0]
        await interaction.response.defer()

class EndMonthSelect(discord.ui.Select):
    def __init__(self, parent_view: VacationSlashView):
        super().__init__(placeholder="Місяць закінчення", min_values=1, max_values=1, options=month_options())
        self.parent_view = parent_view
    async def callback(self, interaction: discord.Interaction):
        self.parent_view.end_month = self.values[0]
        await interaction.response.defer()

class VacationSlashButton(discord.ui.Button):
    def __init__(self, parent_view: VacationSlashView):
        super().__init__(label="Відправити", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view
    async def callback(self, interaction: discord.Interaction):
        if not (self.parent_view.start_day and self.parent_view.start_month and 
                self.parent_view.end_day and self.parent_view.end_month):
            await interaction.response.send_message("Будь ласка, оберіть усі поля!", ephemeral=False)
            return
        payload = build_payload(
            command=self.parent_view.slash_cmd_name,
            status="ok",
            message="",
            result={
                "start_day": self.parent_view.start_day,
                "start_month": self.parent_view.start_month,
                "end_day": self.parent_view.end_day,
                "end_month": self.parent_view.end_month
            },
            author=str(interaction.user),
            userId=self.parent_view.user_id,
            sessionId=self.parent_view.session_id,
            channelId=str(interaction.channel_id),
            channelName=getattr(interaction.channel, 'name', 'DM')
        )
        headers = {}
        if WEBHOOK_AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {WEBHOOK_AUTH_TOKEN}"
        success, data = await send_webhook_with_retry(interaction, payload, headers)
        if not success or not data:
            return
        await send_n8n_reply_interaction(interaction, data)
        self.parent_view.disable_all_items()
        self.parent_view.stop()

###############################################################################
# PREFIX COMMANDS (User messages in Ukrainian)
###############################################################################
@bot.command(name="register", help="Використання: !register <будь-який текст>")
async def register_cmd(ctx: commands.Context, *, text: str):
    user_id = str(ctx.author.id)
    session_id = get_session_id(user_id)
    payload = build_payload(
        command="prefix-register",
        status="ok",
        message="",
        result={"text": text},
        author=str(ctx.author),
        userId=user_id,
        sessionId=session_id,
        channelId=str(ctx.channel.id),
        channelName=getattr(ctx.channel, 'name', 'DM')
    )
    headers = {}
    if WEBHOOK_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {WEBHOOK_AUTH_TOKEN}"
    success, data = await send_webhook_with_retry(ctx, payload, headers)
    if not success or not data:
        return
    await send_n8n_reply_channel(ctx.channel, data)

@bot.command(name="unregister", help="Використання: !unregister")
async def unregister_cmd(ctx: commands.Context):
    user_id = str(ctx.author.id)
    session_id = get_session_id(user_id)
    payload = build_payload(
        command="unregister",
        status="ok",
        message="",
        result={},
        author=str(ctx.author),
        userId=user_id,
        sessionId=session_id,
        channelId=str(ctx.channel.id),
        channelName=getattr(ctx.channel, 'name', 'DM')
    )
    headers = {}
    if WEBHOOK_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {WEBHOOK_AUTH_TOKEN}"
    success, data = await send_webhook_with_retry(ctx, payload, headers)
    if not success or not data:
        await ctx.send("Помилка виклику n8n.")
        return
    await send_n8n_reply_channel(ctx.channel, data)

###############################################################################
# SLASH COMMANDS (User messages in Ukrainian)
###############################################################################
day_off_group = app_commands.Group(name="day_off", description="Команди для вихідних")

@day_off_group.command(name="thisweek", description="Оберіть вихідні на ЦЕЙ тиждень.")
async def day_off_thisweek(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=False)
    user_id = str(interaction.user.id)
    view = create_day_off_view("day_off_thisweek", user_id, dynamic_survey=False)
    await interaction.followup.send("Оберіть свої вихідні (цей тиждень), потім натисніть «Відправити»:", view=view, ephemeral=False)

@day_off_group.command(name="nextweek", description="Оберіть вихідні на НАСТУПНИЙ тиждень.")
async def day_off_nextweek(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=False)
    user_id = str(interaction.user.id)
    view = create_day_off_view("day_off_nextweek", user_id, dynamic_survey=False)
    await interaction.followup.send("Оберіть свої вихідні (наступний тиждень), потім натисніть «Відправити»:", view=view, ephemeral=False)

bot.tree.add_command(day_off_group)

@bot.tree.command(name="vacation", description="Оберіть день/місяць початку та кінця відпустки.")
async def vacation_slash(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    view = create_vacation_view("vacation", user_id)
    await interaction.response.send_message("Будь ласка, оберіть день/місяць початку та кінця відпустки, потім натисніть «Відправити»:", view=view, ephemeral=False)

@bot.tree.command(name="workload_today", description="Скільки годин підтверджено з СЬОГОДНІ до кінця тижня?")
async def slash_workload_today(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    view = create_workload_view("workload_today", user_id, dynamic_survey=False)
    await interaction.response.send_message("Скільки годин підтверджено з СЬОГОДНІ до кінця тижня?\nЯкщо нічого, оберіть «Нічого немає».", view=view, ephemeral=False)

@bot.tree.command(name="workload_nextweek", description="Скільки годин підтверджено на НАСТУПНИЙ тиждень?")
async def slash_workload_nextweek(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    view = create_workload_view("workload_nextweek", user_id, dynamic_survey=False)
    await interaction.response.send_message("Скільки годин підтверджено на НАСТУПНИЙ тиждень?\nЯкщо нічого, оберіть «Нічого немає».", view=view, ephemeral=False)

@bot.tree.command(name="connects_thisweek", description="Скільки CONNECTS підтверджено на ЦЬОГО тижня?")
async def slash_connects_thisweek(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    view = create_workload_view("connects_thisweek", user_id, dynamic_survey=True)
    await interaction.response.send_message("Скільки CONNECTS підтверджено на ЦЬОГА тижня?\nЯкщо нічого, оберіть «Нічого немає».", view=view, ephemeral=False)

###############################################################################
# HTTP/HTTPS Server for Survey Activation (CapRover) (Responses remain in English)
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
