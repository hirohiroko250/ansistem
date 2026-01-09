"""
Students Views Package
"""
# Student Views
from .student import StudentViewSet

# Guardian Views
from .guardian import GuardianViewSet

# Relations Views
from .relations import StudentGuardianViewSet, StudentSchoolViewSet

# Request Views
from .requests import SuspensionRequestViewSet, WithdrawalRequestViewSet

# Bank Views
from .bank import BankAccountViewSet, BankAccountChangeRequestViewSet

# Friendship Views
from .friendship import FriendshipViewSet

__all__ = [
    # Student
    'StudentViewSet',
    # Guardian
    'GuardianViewSet',
    # Relations
    'StudentGuardianViewSet',
    'StudentSchoolViewSet',
    # Requests
    'SuspensionRequestViewSet',
    'WithdrawalRequestViewSet',
    # Bank
    'BankAccountViewSet',
    'BankAccountChangeRequestViewSet',
    # Friendship
    'FriendshipViewSet',
]
