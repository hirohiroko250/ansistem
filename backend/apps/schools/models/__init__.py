"""
Schools Models Package
校舎・ブランド・スケジュール関連モデル
"""

# Brand
from .brand import (
    BrandCategory,
    Brand,
    BrandSchool,
)

# School
from .school import School

# Grade
from .grade import (
    SchoolYear,
    Grade,
    GradeSchoolYear,
    Subject,
)

# Classroom
from .classroom import (
    Classroom,
    TimeSlot,
)

# Schedule
from .schedule import (
    SchoolSchedule,
    ClassSchedule,
    SchoolCourse,
    SchoolClosure,
)

# Calendar
from .calendar import (
    CalendarMaster,
    LessonCalendar,
    CalendarOperationLog,
)

# Bank Master
from .bank_master import (
    BankType,
    Bank,
    BankBranch,
)

__all__ = [
    # Brand
    'BrandCategory',
    'Brand',
    'BrandSchool',
    # School
    'School',
    # Grade
    'SchoolYear',
    'Grade',
    'GradeSchoolYear',
    'Subject',
    # Classroom
    'Classroom',
    'TimeSlot',
    # Schedule
    'SchoolSchedule',
    'ClassSchedule',
    'SchoolCourse',
    'SchoolClosure',
    # Calendar
    'CalendarMaster',
    'LessonCalendar',
    'CalendarOperationLog',
    # Bank Master
    'BankType',
    'Bank',
    'BankBranch',
]
