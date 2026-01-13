"""
Lessons Views Package
授業スケジュール・出欠・振替のViews
"""

# TimeSlot
from .time_slot import TimeSlotViewSet

# Schedule
from .schedule import LessonScheduleViewSet

# Attendance
from .attendance import AttendanceViewSet

# Makeup
from .makeup import MakeupLessonViewSet

# Record
from .record import (
    LessonRecordViewSet,
    GroupLessonEnrollmentViewSet,
)

# Calendar
from .calendar import StudentCalendarView

# Absence
from .absence import (
    MarkAbsenceView,
    AbsenceTicketListView,
    UseAbsenceTicketView,
    TransferAvailableClassesView,
    CancelAbsenceView,
    CancelMakeupView,
)


__all__ = [
    # TimeSlot
    'TimeSlotViewSet',
    # Schedule
    'LessonScheduleViewSet',
    # Attendance
    'AttendanceViewSet',
    # Makeup
    'MakeupLessonViewSet',
    # Record
    'LessonRecordViewSet',
    'GroupLessonEnrollmentViewSet',
    # Calendar
    'StudentCalendarView',
    # Absence
    'MarkAbsenceView',
    'AbsenceTicketListView',
    'UseAbsenceTicketView',
    'TransferAvailableClassesView',
    'CancelAbsenceView',
    'CancelMakeupView',
]
