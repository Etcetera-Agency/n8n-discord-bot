# Simplified imports for command-only views
from bot.views.workload import WorkloadView, WorkloadButton
from bot.views.day_off import DayOffView, DayOffButton
from bot.views.factory import create_view

__all__ = [
    'WorkloadView',
    'WorkloadButton',
    'DayOffView', 
    'DayOffButton',
    'create_view'
]

DEPRECATION_NOTICE = """
Survey-related view functionality has been moved to modal-based flow.
These views are now only for non-survey commands.
"""