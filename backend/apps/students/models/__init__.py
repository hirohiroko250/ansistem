"""
Students Models Package
生徒・保護者関連モデル
"""

# Student
from .student import Student

# Guardian
from .guardian import Guardian

# Relations
from .relations import (
    StudentSchool,
    StudentEnrollment,
    StudentGuardian,
)

# Booking
from .booking import (
    TrialBooking,
    AbsenceTicket,
)

# Bank Account
from .bank import (
    BankAccount,
    BankAccountChangeRequest,
)

# Requests (Suspension/Withdrawal)
from .requests import (
    SuspensionRequest,
    WithdrawalRequest,
)

# Friendship
from .friendship import (
    FriendshipRegistration,
    FSDiscount,
)

__all__ = [
    # Student
    'Student',
    # Guardian
    'Guardian',
    # Relations
    'StudentSchool',
    'StudentEnrollment',
    'StudentGuardian',
    # Booking
    'TrialBooking',
    'AbsenceTicket',
    # Bank Account
    'BankAccount',
    'BankAccountChangeRequest',
    # Requests
    'SuspensionRequest',
    'WithdrawalRequest',
    # Friendship
    'FriendshipRegistration',
    'FSDiscount',
]
