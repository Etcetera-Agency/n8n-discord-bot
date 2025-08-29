"""
Adapter interface for Notion API operations.
"""
from typing import Optional, Dict, Any

class NotionClient:
    """An interface for interacting with the Notion API."""

    def find_user_by_discord_id(self, discord_id: str) -> Optional[Dict[str, Any]]:
        """Finds a Notion page by a user's Discord ID."""
        pass

    def update_user_channel(self, notion_page_id: str, channel_id: str) -> None:
        """Updates the 'Discord channel ID' property on a Notion page."""
        pass

    def clear_user_channel(self, notion_page_id: str) -> None:
        """Clears the 'Discord channel ID' property on a Notion page."""
        pass

    def update_user_workload(self, notion_page_id: str, field_name: str, hours: int) -> None:
        """Updates a workload number property on a Notion page."""
        pass

    def update_user_connects(self, notion_page_id: str, connects_count: int) -> None:
        """
        Updates the 'Connects' number property on a user's Notion page.

        Args:
            notion_page_id: The ID of the Notion page to update.
            connects_count: The number of connects to set.
        """
        pass
