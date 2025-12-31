"""
Trial Views Package
体験授業関連Views
"""

# Utils
from .utils import get_school_year_from_birth_date

# Schedule
from .schedule import PublicTrialScheduleView

# Availability
from .availability import (
    PublicTrialAvailabilityView,
    PublicTrialMonthlyAvailabilityView,
)

# Booking
from .booking import PublicTrialBookingView

# Class Schedule
from .class_schedule import PublicClassScheduleView

# Lookup
from .lookup import (
    PublicSchoolsByTicketView,
    PublicTicketsBySchoolView,
)

# Stats
from .stats import PublicTrialStatsView


__all__ = [
    # Utils
    'get_school_year_from_birth_date',
    # Schedule
    'PublicTrialScheduleView',
    # Availability
    'PublicTrialAvailabilityView',
    'PublicTrialMonthlyAvailabilityView',
    # Booking
    'PublicTrialBookingView',
    # Class Schedule
    'PublicClassScheduleView',
    # Lookup
    'PublicSchoolsByTicketView',
    'PublicTicketsBySchoolView',
    # Stats
    'PublicTrialStatsView',
]
