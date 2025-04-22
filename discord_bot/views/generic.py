import discord
from typing import Optional, List
from .base import BaseView
from services import webhook_service

class GenericSelect(discord.ui.Select):
    """Generic select menu for various purposes."""
    def __init__(
        self,
        parent_view: BaseView,
        field_name: str,
        placeholder: str,
        options: List[discord.SelectOption]
    ):
        """
        Initialize the generic select menu.
        
        Args:
            parent_view: Parent view
            field_name: Field name for storing the selected value
            placeholder: Placeholder text
            options: Select options
        """
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)
        self.parent_view = parent_view
        self.field_name = field_name
    
    async def callback(self, interaction: discord.Interaction) -> None:
        """
        Handle select menu change.
        
        Args:
            interaction: Discord interaction
        """
        await webhook_service.send_button_pressed_info(interaction, self)
        self.parent_view.data[self.field_name] = self.values[0]
        await interaction.response.defer() 