import discord
from typing import Optional
from config import logger, Strings # Added Strings
from services import webhook_service # Added webhook_service

class WorkloadView(discord.ui.View):
    """View for workload selection - only used for non-survey commands"""
    def __init__(self, cmd_or_step: str, user_id: str):
        super().__init__(timeout=300)
        self.cmd_or_step = cmd_or_step
        self.user_id = user_id
        
    async def on_timeout(self):
        logger.warning(f"WorkloadView timed out for user {self.user_id}")

class WorkloadButton(discord.ui.Button):
    def __init__(self, hour: str, custom_id: str):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=hour,
            custom_id=custom_id
        )

    async def callback(self, interaction: discord.Interaction):
        # Ensure interaction is deferred to prevent timeout
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=False) # Defer publicly initially

        logger.info(f"Workload button '{self.label}' clicked by {interaction.user} for command '{self.view.cmd_or_step}'")

        # Get original interaction message if possible (for editing later)
        original_message = None
        try:
            if interaction.message: # Button clicks have the message attached
                 original_message = interaction.message
            elif hasattr(self.view, 'buttons_msg'): # Fallback if stored on view
                 original_message = self.view.buttons_msg
        except Exception as e:
            logger.warning(f"Could not get original message for workload button: {e}")

        try:
            # Add processing indicator
            if original_message:
                await original_message.edit(view=None, content=f"{original_message.content}\n⏳ Обробка...") # Remove buttons and show processing

            # Send data via webhook
            success, data = await webhook_service.send_webhook(
                interaction,
                command=self.view.cmd_or_step, # e.g., "workload_today"
                status="ok",
                result={self.view.cmd_or_step: self.label} # Send selected hour
            )

            # Process webhook response
            if success and data and "output" in data:
                response_content = data["output"]
                logger.info(f"Workload webhook successful for {interaction.user}. Response: {response_content}")
                if original_message:
                    await original_message.edit(content=response_content) # Update original message with final response
                else: # Fallback if original message couldn't be edited
                    await interaction.followup.send(response_content, ephemeral=False)
            else:
                error_msg = Strings.WEBHOOK_ERROR # Use generic error string
                logger.error(f"Workload webhook failed for {interaction.user}. Success: {success}, Data: {data}")
                if original_message:
                    await original_message.edit(content=f"{original_message.content.replace('⏳ Обробка...', '')}\n❌ {error_msg}")
                else:
                    await interaction.followup.send(f"❌ {error_msg}", ephemeral=True) # Send error ephemerally if no message to edit

        except Exception as e:
            logger.error(f"Error in WorkloadButton callback: {e}", exc_info=True)
            error_msg = Strings.GENERAL_ERROR
            try:
                if original_message:
                     await original_message.edit(content=f"{original_message.content.replace('⏳ Обробка...', '')}\n❌ {error_msg}")
                elif interaction.followup:
                    await interaction.followup.send(f"❌ {error_msg}", ephemeral=True)
            except Exception as e_resp:
                 logger.error(f"Failed to send error response in workload callback: {e_resp}")

def create_workload_view(cmd: str, user_id: str, timeout: Optional[float] = None) -> WorkloadView:
    """Create workload view for regular commands only"""
    view = WorkloadView(cmd, user_id)
    
    from config.constants import WORKLOAD_OPTIONS
    workload_options = [opt for opt in WORKLOAD_OPTIONS if opt != "Нічого немає"]  # Filter out non-numeric option
    for hour in workload_options:
        button = WorkloadButton(
            hour=hour,
            custom_id=f"workload_cmd_{hour}_{user_id}" 
        )
        view.add_item(button)
    
    return view