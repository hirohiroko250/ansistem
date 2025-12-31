"""
Students Serializers

モジュール構成:
- student.py: 生徒シリアライザ
- guardian.py: 保護者シリアライザ
- enrollment.py: 生徒所属・保護者関連シリアライザ
- request.py: 休会・退会申請シリアライザ
- bank.py: 銀行口座関連シリアライザ
"""
from .student import (
    StudentListSerializer,
    StudentDetailSerializer,
    StudentCreateSerializer,
    StudentUpdateSerializer,
    StudentWithGuardiansSerializer,
)
from .guardian import (
    GuardianListSerializer,
    GuardianDetailSerializer,
    GuardianPaymentSerializer,
    GuardianPaymentUpdateSerializer,
    GuardianCreateUpdateSerializer,
)
from .enrollment import (
    StudentSchoolSerializer,
    StudentGuardianSerializer,
)
from .request import (
    SuspensionRequestSerializer,
    SuspensionRequestCreateSerializer,
    WithdrawalRequestSerializer,
    WithdrawalRequestCreateSerializer,
)
from .bank import (
    BankAccountSerializer,
    BankAccountChangeRequestSerializer,
    BankAccountChangeRequestCreateSerializer,
)

__all__ = [
    # Student
    'StudentListSerializer',
    'StudentDetailSerializer',
    'StudentCreateSerializer',
    'StudentUpdateSerializer',
    'StudentWithGuardiansSerializer',
    # Guardian
    'GuardianListSerializer',
    'GuardianDetailSerializer',
    'GuardianPaymentSerializer',
    'GuardianPaymentUpdateSerializer',
    'GuardianCreateUpdateSerializer',
    # Enrollment
    'StudentSchoolSerializer',
    'StudentGuardianSerializer',
    # Request
    'SuspensionRequestSerializer',
    'SuspensionRequestCreateSerializer',
    'WithdrawalRequestSerializer',
    'WithdrawalRequestCreateSerializer',
    # Bank
    'BankAccountSerializer',
    'BankAccountChangeRequestSerializer',
    'BankAccountChangeRequestCreateSerializer',
]
