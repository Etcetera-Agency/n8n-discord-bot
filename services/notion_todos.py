import asyncio
from config.logger import logger
import os
import re
import json
from dataclasses import dataclass, field
from datetime import date, timedelta, datetime
from typing import List, Optional
from notion_client import Client as NotionClient

@dataclass
class ToDoBlock:
    title: str = ""
    todo_date: str = ""
    id: str = ""

@dataclass
class TodosBlocks:
    title: str = ""
    todo_date: str = ""
    todo_list: List[ToDoBlock] = field(default_factory=list)

def _parse_url(url: str) -> Optional[str]:
    match = re.search(r'([a-f0-9]{32}|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', url)
    if match:
        return match.group(1)
    parts = url.split('/')
    if parts[-1] and len(parts[-1].replace('-', '')) == 32:
        return parts[-1]
    return None

class Notion_todos:
    def __init__(self, todo_url: str, days: int = None):
        notion_token = os.environ.get("NOTION_TOKEN")
        if not notion_token:
            raise ValueError("Notion API token is required. Set NOTION_TOKEN environment variable.")
        if not todo_url:
            raise ValueError("Notion ToDo page URL is required.")
        self.todo_url = todo_url
        self.client = NotionClient(auth=notion_token)
        self.block_id = _parse_url(self.todo_url)
        if not self.block_id:
            raise ValueError(f"Could not parse a valid Notion block ID from URL: {self.todo_url}")
        self.days = days

    async def get_tasks_text(self, only_unchecked: bool = True) -> str:
        # Calculate date range if days is set
        start_date = None
        end_date = None
        if self.days is not None:
            end_date = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            start_dt = datetime.now() - timedelta(days=self.days)
            start_date = start_dt.strftime('%Y-%m-%dT%H:%M:%S')
        try:
            # Run blocking Notion API call in a separate thread
            page = await asyncio.to_thread(self.client.blocks.retrieve, self.block_id)
        except Exception as e:
            logger.error(f"Failed to fetch Notion page: {e}")
            raise ConnectionError(f"Failed to fetch Notion page (ID: {self.block_id}) from URL {self.todo_url}. Error: {e}")

        todos = await self._extract_todos(self.block_id, only_unchecked=only_unchecked, start_date=start_date, end_date=end_date)

        tasks_found = bool(todos)
        if not tasks_found:
            return json.dumps({"tasks_found": False, "text": "Дякую. /nЧудового дня!"}, ensure_ascii=False)
        lines = ["### Зверни увагу, що у тебе в ToDo є такі завдання, які було б чудово вже  виконати:"]
        for block in todos:
            lines.append(f" * *{block.title}*")
        return json.dumps({"tasks_found": True, "text": "\n".join(lines)}, ensure_ascii=False)

    async def _extract_todos(self, block_id: str, only_unchecked: bool = True, start_date: str = None, end_date: str = None) -> List[ToDoBlock]:
        todos = []
        # Run blocking Notion API call in a separate thread
        children = await asyncio.to_thread(self.client.blocks.children.list, block_id)
        for child in children.get('results', []):
            if child['type'] == 'to_do':
                checked = child['to_do'].get('checked', False)
                created_time = child.get('created_time', '')
                # Date filtering
                if start_date and created_time < start_date:
                    continue
                if end_date and created_time >= end_date:
                    continue
                if only_unchecked and checked:
                    continue
                title = "".join([t['plain_text'] for t in child['to_do']['rich_text']])
                todo = ToDoBlock(title=title, todo_date=created_time, id=child['id'])
                setattr(todo, 'checked', checked)
                todos.append(todo)
            # Recursively check children
            if child.get('has_children'):
                # Recursively call the async version
                todos.extend(await self._extract_todos(child['id'], only_unchecked=only_unchecked, start_date=start_date, end_date=end_date))
        return todos