# Simplified imports for command-only views
from .workload_slash import WorkloadView_slash, WorkloadButton_slash # Import from slash-specific workload
from .day_off_slash import DayOffView_slash, DayOffButton_slash # Import from slash-specific day_off
from .factory import create_view
from .connects_survey import ConnectsModal
 
__all__ = [
    'WorkloadView_slash',
    'WorkloadButton_slash',
    'DayOffView_slash',
    'DayOffButton_slash',
    'create_view',
    'ConnectsModal'
]

DEPRECATION_NOTICE = """
Survey-related view functionality has been moved to modal-based flow.
These views are now only for non-survey commands.
"""