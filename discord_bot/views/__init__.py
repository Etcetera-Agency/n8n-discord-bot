# Simplified imports for command-only views
from .workload_slash import WorkloadView, WorkloadButton # Import from slash-specific workload
from .day_off_slash import DayOffView, DayOffButton # Import from slash-specific day_off
from .factory import create_view

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