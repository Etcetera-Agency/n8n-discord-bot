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

###############################################################################
# Logging configuration
###############################################################################
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('discord_bot')

###############################################################################
# Environment variables
###############################################################################
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
WEBHOOK_AUTH_TOKEN = os.getenv("WEBHOOK_AUTH_TOKEN")

# Session TTL for user sessions (24 hours)
SESSION_TTL = 86400
sessions = TTLCache(maxsize=1024, ttl=SESSION_TTL)

http_session = None

###############################################################################
# Utility: build_payload
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
    """
    Constructs a unified JSON payload to send to n8n.
    
    - command: Name of the command (e.g. "mention", "prefix-register", "workload_today", "survey")
    - status: "ok", "step", or "incomplete"
    - message: Raw text from the user (only used for normal messages)
    - result: Structured result (for slash commands or survey steps)
    - author, userId, sessionId, channelId, channelName, timestamp: Metadata
    """
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
# Helper: get_session_id
###############################################################################
def get_session_id(user_id: str) -> str:
    """Returns an existing session_id or creates a new one for the given user."""
    if user_id in sessions:
        return sessions[user_id]
    new_session_id = str(uuid.uuid4())
    sessions[user_id] = new_session_id
    return new_session_id

###############################################################################
# Send webhook with retry
###############################################################################
async def send_webhook_with_retry(target_channel, payload, headers, max_retries=3, retry_delay=1):
    """
    Sends a POST request to n8n with retry logic.
    Returns (success, data).
    """
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
# Bot setup
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
# ON_MESSAGE: Handle mentions and dynamic survey trigger
###############################################################################
# SURVEYS holds dynamic survey state: user_id -> SurveyFlow
SURVEYS = {}

class SurveyFlow:
    """
    Holds a list of survey steps (for dynamic surveys).
    E.g., steps = ["workload_nextweek", "connects_thisweek", "day_off_nextweek"]
    """
    def __init__(self, user_id: str, channel_id: str, steps: List[str]):
        self.user_id = user_id
        self.channel_id = channel_id
        self.steps = steps
        self.current_index = 0
        self.results = {}  # stepName -> value

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

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    # If user mentions the bot
    if bot.user in message.mentions:
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
            reply_text = data.get("output", "").strip()
            if reply_text:
                await message.channel.send(reply_text)

    # Dynamic survey trigger (example message):
    # "start_daily_survey <userId> <channelId> step1 step2 ..."
    if message.content.startswith("start_daily_survey"):
        parts = message.content.split()
        if len(parts) >= 4:
            user_id = parts[1]
            channel_id = parts[2]
            steps = parts[3:]
            await handle_start_daily_survey(user_id, channel_id, steps)

    await bot.process_commands(message)

async def handle_start_daily_survey(user_id: str, channel_id: str, steps: List[str]):
    state = SurveyFlow(user_id, channel_id, steps)
    SURVEYS[user_id] = state
    channel = bot.get_channel(int(channel_id))
    if not channel:
        logger.warning(f"Channel {channel_id} not found for user {user_id}")
        return
    step = state.current_step()
    if step:
        await ask_dynamic_step(channel, state, step)
    else:
        await channel.send(f"<@{user_id}> No survey steps provided.")

async def ask_dynamic_step(channel: discord.TextChannel, state: SurveyFlow, step_name: str):
    user_id = state.user_id
    if step_name.startswith("workload") or step_name.startswith("connects"):
        # Create a workload view (dynamic survey mode)
        if step_name == "workload_nextweek":
            text_q = f"<@{user_id}> How many hours for NEXT week?"
        elif step_name == "workload_thisweek":
            text_q = f"<@{user_id}> How many hours for THIS week?"
        elif step_name == "connects_thisweek":
            text_q = f"<@{user_id}> How many CONNECTS for this week?"
        else:
            text_q = f"<@{user_id}> Please choose a number of hours:"
        view = create_workload_view(step_name, user_id, dynamic_survey=True)
        await channel.send(text_q, view=view)
    elif step_name.startswith("day_off"):
        text_q = f"<@{user_id}> Which day(s) off for next week?"
        view = create_day_off_view(step_name, user_id, dynamic_survey=True)
        await channel.send(text_q, view=view)
    else:
        await channel.send(f"<@{user_id}> Unknown survey step: {step_name}. Skipping.")
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
            rtxt = data.get("output", "Survey results saved.").strip()
            await channel.send(f"<@{state.user_id}> Survey finished!\n{rtxt}")
        else:
            await channel.send(f"<@{state.user_id}> Survey finished, but there was an error sending results to n8n.")
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
    await channel.send(
        f"<@{state.user_id}> Survey timed out after 15 minutes. Incomplete steps: {', '.join(incomplete)}"
    )
    if state.user_id in SURVEYS:
        del SURVEYS[state.user_id]

###############################################################################
# Factory functions for common UI views
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
# WORKLOAD VIEWS (Static and Dynamic)
###############################################################################
WORKLOAD_OPTIONS = ["Нічого немає","2","5","10","15","20","25","30","35","40","45","50"]

class WorkloadDynamicView(discord.ui.View):
    def __init__(self, step_name: str, user_id: str):
        super().__init__(timeout=900)  # 15 minutes timeout
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
        if self.label == "Нічого немає":
            value = 0
        else:
            value = int(self.label)
        state = SURVEYS.get(self.parent_view.user_id)
        if not state:
            await interaction.response.send_message("Survey not found.", ephemeral=False)
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
            await interaction.response.send_message("Error calling n8n.", ephemeral=False)
            return
        rtxt = data.get("output", "No text from n8n.").strip()
        await interaction.response.send_message(f"n8n says: {rtxt}", ephemeral=False)
        state.results[self.parent_view.step_name] = value
        state.next_step()
        nxt = state.current_step()
        if nxt:
            await interaction.channel.send(f"Moving on to step: {nxt}")
            await ask_dynamic_step(interaction.channel, state, nxt)
        else:
            await interaction.channel.send("All steps done!")
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
        if self.label == "Нічого немає":
            hours_value = 0
        else:
            hours_value = int(self.label)
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
        rtxt = data.get("output", "No text from n8n.").strip()
        await interaction.response.send_message(f"Selected: {hours_value}. {rtxt}", ephemeral=False)
        self.parent_view.disable_all_items()
        self.parent_view.stop()

###############################################################################
# DAY OFF VIEWS (Dynamic and Slash)
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
        options = [
            discord.SelectOption(label="Monday", value="Monday"),
            discord.SelectOption(label="Tuesday", value="Tuesday"),
            discord.SelectOption(label="Wednesday", value="Wednesday"),
            discord.SelectOption(label="Thursday", value="Thursday"),
            discord.SelectOption(label="Friday", value="Friday"),
            discord.SelectOption(label="Saturday", value="Saturday"),
            discord.SelectOption(label="Sunday", value="Sunday")
        ]
        super().__init__(placeholder="Select day(s) off", min_values=1, max_values=7, options=options)
    async def callback(self, interaction: discord.Interaction):
        self.parent_view.days_selected = self.values
        await interaction.response.defer()

class DayOffDynamicSubmit(discord.ui.Button):
    def __init__(self, parent_view: DayOffDynamicView):
        super().__init__(label="Submit days", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view
    async def callback(self, interaction: discord.Interaction):
        if not self.parent_view.days_selected:
            await interaction.response.send_message("No days selected.", ephemeral=False)
            return
        state = SURVEYS.get(self.parent_view.user_id)
        if not state:
            await interaction.response.send_message("Survey not found.", ephemeral=False)
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
            await interaction.response.send_message("Error calling n8n.", ephemeral=False)
            return
        rtxt = data.get("output", "No text from n8n.").strip()
        await interaction.response.send_message(f"n8n says: {rtxt}", ephemeral=False)
        state.results[self.parent_view.step_name] = self.parent_view.days_selected
        state.next_step()
        nxt = state.current_step()
        if nxt:
            await interaction.channel.send(f"Moving on to step: {nxt}")
            await ask_dynamic_step(interaction.channel, state, nxt)
        else:
            await interaction.channel.send("All steps done!")
            await finish_survey(interaction.channel, state)
        for c in self.parent_view.children:
            c.disabled = True
        self.parent_view.stop()

# For static slash commands, a similar DayOffSlashView is created:
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
        options = [
            discord.SelectOption(label="Monday", value="Monday"),
            discord.SelectOption(label="Tuesday", value="Tuesday"),
            discord.SelectOption(label="Wednesday", value="Wednesday"),
            discord.SelectOption(label="Thursday", value="Thursday"),
            discord.SelectOption(label="Friday", value="Friday"),
            discord.SelectOption(label="Saturday", value="Saturday"),
            discord.SelectOption(label="Sunday", value="Sunday")
        ]
        super().__init__(placeholder="Select day(s) off...", min_values=1, max_values=7, options=options)
    async def callback(self, interaction: discord.Interaction):
        self.parent_view.days_selected = self.values
        await interaction.response.defer()

class DayOffSlashButton(discord.ui.Button):
    def __init__(self, parent_view: DayOffSlashView):
        super().__init__(label="Submit", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view
    async def callback(self, interaction: discord.Interaction):
        if not self.parent_view.days_selected:
            await interaction.response.send_message("No days selected!", ephemeral=False)
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
        rtxt = data.get("output", "No text from n8n.").strip()
        await interaction.response.send_message(
            f"You selected: {', '.join(self.parent_view.days_selected)}\n{rtxt}",
            ephemeral=False
        )
        self.parent_view.disable_all_items()
        self.parent_view.stop()

###############################################################################
# VACATION SLASH VIEW (Static)
###############################################################################
def day_options():
    return [discord.SelectOption(label=str(d), value=str(d)) for d in range(1, 32)]
def month_options():
    month_names = ["January","February","March","April","May","June","July","August","September","October","November","December"]
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
        super().__init__(placeholder="Start Day", min_values=1, max_values=1, options=day_options())
        self.parent_view = parent_view
    async def callback(self, interaction: discord.Interaction):
        self.parent_view.start_day = self.values[0]
        await interaction.response.defer()

class StartMonthSelect(discord.ui.Select):
    def __init__(self, parent_view: VacationSlashView):
        super().__init__(placeholder="Start Month", min_values=1, max_values=1, options=month_options())
        self.parent_view = parent_view
    async def callback(self, interaction: discord.Interaction):
        self.parent_view.start_month = self.values[0]
        await interaction.response.defer()

class EndDaySelect(discord.ui.Select):
    def __init__(self, parent_view: VacationSlashView):
        super().__init__(placeholder="End Day", min_values=1, max_values=1, options=day_options())
        self.parent_view = parent_view
    async def callback(self, interaction: discord.Interaction):
        self.parent_view.end_day = self.values[0]
        await interaction.response.defer()

class EndMonthSelect(discord.ui.Select):
    def __init__(self, parent_view: VacationSlashView):
        super().__init__(placeholder="End Month", min_values=1, max_values=1, options=month_options())
        self.parent_view = parent_view
    async def callback(self, interaction: discord.Interaction):
        self.parent_view.end_month = self.values[0]
        await interaction.response.defer()

class VacationSlashButton(discord.ui.Button):
    def __init__(self, parent_view: VacationSlashView):
        super().__init__(label="Submit", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view
    async def callback(self, interaction: discord.Interaction):
        if not (self.parent_view.start_day and self.parent_view.start_month and 
                self.parent_view.end_day and self.parent_view.end_month):
            await interaction.response.send_message("Please select all fields!", ephemeral=False)
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
        rtxt = data.get("output", "No text from n8n.").strip()
        await interaction.response.send_message(
            f"Vacation request submitted!\nStart: {self.parent_view.start_day}.{self.parent_view.start_month}\n"
            f"End: {self.parent_view.end_day}.{self.parent_view.end_month}\n{rtxt}",
            ephemeral=False
        )
        self.parent_view.disable_all_items()
        self.parent_view.stop()

###############################################################################
# PREFIX COMMAND: !register (Accept any text)
###############################################################################
@bot.command(name="register", help="Usage: !register <any text>")
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
    reply_text = data.get("output", "No text from n8n.").strip()
    if reply_text:
        await ctx.send(reply_text)

###############################################################################
# SLASH COMMANDS (Static)
###############################################################################

# /day_off group
day_off_group = app_commands.Group(name="day_off", description="Commands for day(s) off")

@day_off_group.command(name="thisweek", description="Select your day(s) off for THIS week.")
async def day_off_thisweek(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=False)
    user_id = str(interaction.user.id)
    view = create_day_off_view("day_off_thisweek", user_id, dynamic_survey=False)
    await interaction.followup.send(
        "Select your day(s) off (this week), then press Submit:",
        view=view,
        ephemeral=False
    )

@day_off_group.command(name="nextweek", description="Select your day(s) off for NEXT week.")
async def day_off_nextweek(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=False)
    user_id = str(interaction.user.id)
    view = create_day_off_view("day_off_nextweek", user_id, dynamic_survey=False)
    await interaction.followup.send(
        "Select your day(s) off (next week), then press Submit:",
        view=view,
        ephemeral=False
    )

bot.tree.add_command(day_off_group)

# /vacation command
@bot.tree.command(name="vacation", description="Pick start/end day/month for your vacation.")
async def vacation_slash(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    view = create_vacation_view("vacation", user_id)
    await interaction.response.send_message(
        "Please select start day/month, end day/month, then press Submit:",
        view=view,
        ephemeral=False
    )

# /workload_today and /workload_nextweek
@bot.tree.command(name="workload_today", description="How many hours from TODAY until end of week?")
async def slash_workload_today(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    view = create_workload_view("workload_today", user_id, dynamic_survey=False)
    await interaction.response.send_message(
        "How many hours are confirmed from TODAY until end of week?\nIf none, pick 'Нічого немає'.",
        view=view,
        ephemeral=False
    )

@bot.tree.command(name="workload_nextweek", description="How many hours for NEXT week?")
async def slash_workload_nextweek(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    view = create_workload_view("workload_nextweek", user_id, dynamic_survey=False)
    await interaction.response.send_message(
        "How many hours are confirmed for NEXT week?\nIf none, pick 'Нічого немає'.",
        view=view,
        ephemeral=False
    )

###############################################################################
# Factory functions for UI views
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
# RUN THE BOT
###############################################################################
bot.run(DISCORD_TOKEN)
