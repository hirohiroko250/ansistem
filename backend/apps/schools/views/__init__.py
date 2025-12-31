"""
Schools Views Package
"""
# Brand Views
from .brand import BrandViewSet, PublicBrandCategoriesView, PublicBrandSchoolsView

# School Views
from .school import (
    SchoolViewSet, PublicSchoolListView, PublicPrefectureListView,
    PublicAreaListView, PublicSchoolsByAreaView
)

# Grade & Subject Views
from .grade import GradeViewSet, SubjectViewSet

# Classroom Views
from .classroom import ClassroomViewSet

# Schedule Views
from .schedule import TimeSlotViewSet, SchoolScheduleViewSet, SchoolCourseViewSet, SchoolClosureViewSet

# Trial Views
from .trial import (
    get_school_year_from_birth_date,
    PublicTrialScheduleView, PublicTrialAvailabilityView, PublicTrialBookingView,
    PublicClassScheduleView, PublicSchoolsByTicketView, PublicTicketsBySchoolView,
    PublicTrialMonthlyAvailabilityView, PublicTrialStatsView
)

# Calendar Views
from .calendar import (
    PublicLessonCalendarView, PublicCalendarSeatsView,
    AdminCalendarView, AdminCalendarEventDetailView, AdminCalendarABSwapView
)

# Attendance Views
from .attendance import AdminMarkAttendanceView, AdminAbsenceTicketListView

# Bank Views
from .bank import PublicBankTypesView, PublicBanksView, PublicBankDetailView, PublicBankBranchesView

# Google Calendar Views
from .google_calendar import GoogleCalendarEventsView, GoogleCalendarListView

__all__ = [
    # Brand
    'BrandViewSet',
    'PublicBrandCategoriesView',
    'PublicBrandSchoolsView',
    # School
    'SchoolViewSet',
    'PublicSchoolListView',
    'PublicPrefectureListView',
    'PublicAreaListView',
    'PublicSchoolsByAreaView',
    # Grade & Subject
    'GradeViewSet',
    'SubjectViewSet',
    # Classroom
    'ClassroomViewSet',
    # Schedule
    'TimeSlotViewSet',
    'SchoolScheduleViewSet',
    'SchoolCourseViewSet',
    'SchoolClosureViewSet',
    # Trial
    'get_school_year_from_birth_date',
    'PublicTrialScheduleView',
    'PublicTrialAvailabilityView',
    'PublicTrialBookingView',
    'PublicClassScheduleView',
    'PublicSchoolsByTicketView',
    'PublicTicketsBySchoolView',
    'PublicTrialMonthlyAvailabilityView',
    'PublicTrialStatsView',
    # Calendar
    'PublicLessonCalendarView',
    'PublicCalendarSeatsView',
    'AdminCalendarView',
    'AdminCalendarEventDetailView',
    'AdminCalendarABSwapView',
    # Attendance
    'AdminMarkAttendanceView',
    'AdminAbsenceTicketListView',
    # Bank
    'PublicBankTypesView',
    'PublicBanksView',
    'PublicBankDetailView',
    'PublicBankBranchesView',
    # Google Calendar
    'GoogleCalendarEventsView',
    'GoogleCalendarListView',
]
