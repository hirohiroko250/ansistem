"""
Schools Admin Package
校舎関連Admin
"""

# Importers
from .importer import (
    SchoolCSVImporter,
    ClassroomCSVImporter,
    LessonCalendarCSVImporter,
)

# Brand
from .brand import (
    BrandSchoolInline,
    BrandInline,
    BrandCategoryAdmin,
    BrandAdmin,
    BrandSchoolAdmin,
)

# School
from .school import SchoolAdmin

# Grade
from .grade import (
    GradeSchoolYearInline,
    SchoolYearAdmin,
    GradeAdmin,
    SubjectAdmin,
)

# Classroom
from .classroom import (
    ClassroomAdmin,
    TimeSlotAdmin,
)

# Calendar
from .calendar import (
    CalendarMasterAdmin,
    LessonCalendarAdmin,
    ClassScheduleAdmin,
    CalendarOperationLogAdmin,
)

# Bank
from .bank import (
    BankBranchInline,
    BankTypeAdmin,
    BankAdmin,
    BankBranchAdmin,
)


__all__ = [
    # Importers
    'SchoolCSVImporter',
    'ClassroomCSVImporter',
    'LessonCalendarCSVImporter',
    # Brand
    'BrandSchoolInline',
    'BrandInline',
    'BrandCategoryAdmin',
    'BrandAdmin',
    'BrandSchoolAdmin',
    # School
    'SchoolAdmin',
    # Grade
    'GradeSchoolYearInline',
    'SchoolYearAdmin',
    'GradeAdmin',
    'SubjectAdmin',
    # Classroom
    'ClassroomAdmin',
    'TimeSlotAdmin',
    # Calendar
    'CalendarMasterAdmin',
    'LessonCalendarAdmin',
    'ClassScheduleAdmin',
    'CalendarOperationLogAdmin',
    # Bank
    'BankBranchInline',
    'BankTypeAdmin',
    'BankAdmin',
    'BankBranchAdmin',
]
