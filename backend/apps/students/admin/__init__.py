"""
Students Admin Package
生徒関連Admin
"""

# Importer
from .importer import StudentCSVImporter

# Student
from .student import StudentAdmin

# Guardian
from .guardian import GuardianAdmin

# StudentSchool
from .student_school import StudentSchoolAdmin

# StudentGuardian
from .student_guardian import StudentGuardianAdmin

# Attendance
from .attendance import AttendanceAdmin

# Enrollment
from .enrollment import (
    StudentEnrollmentAdmin,
    AbsenceTicketAdmin,
)

# Suspension
from .suspension import SuspensionRequestAdmin

# Withdrawal
from .withdrawal import WithdrawalRequestAdmin

# BankAccount
from .bank_account import (
    BankAccountAdmin,
    BankAccountChangeRequestAdmin,
)

# Friendship
from .friendship import (
    FriendshipRegistrationAdmin,
    FSDiscountAdmin,
)


__all__ = [
    # Importer
    'StudentCSVImporter',
    # Student
    'StudentAdmin',
    # Guardian
    'GuardianAdmin',
    # StudentSchool
    'StudentSchoolAdmin',
    # StudentGuardian
    'StudentGuardianAdmin',
    # Attendance
    'AttendanceAdmin',
    # Enrollment
    'StudentEnrollmentAdmin',
    'AbsenceTicketAdmin',
    # Suspension
    'SuspensionRequestAdmin',
    # Withdrawal
    'WithdrawalRequestAdmin',
    # BankAccount
    'BankAccountAdmin',
    'BankAccountChangeRequestAdmin',
    # Friendship
    'FriendshipRegistrationAdmin',
    'FSDiscountAdmin',
]
