"""
Contracts Views Package
契約管理関連のビュー
"""

# Product & Discount
from .product import ProductViewSet, DiscountViewSet

# Course & Pack
from .course import CourseViewSet, PackViewSet

# Event (Seminar & Certification)
from .event import (
    SeminarViewSet,
    CertificationViewSet,
    SeminarEnrollmentViewSet,
    CertificationEnrollmentViewSet,
)

# Student Items & Discounts
from .student_item import StudentItemViewSet, StudentDiscountViewSet

# Contract
from .contract import ContractViewSet

# Public API (認証不要)
from .public import (
    PublicBrandListView,
    PublicCourseListView,
    PublicCourseDetailView,
    PublicPackListView,
    PublicPackDetailView,
)

# Operation History
from .history import OperationHistoryViewSet


__all__ = [
    # Product & Discount
    'ProductViewSet',
    'DiscountViewSet',
    # Course & Pack
    'CourseViewSet',
    'PackViewSet',
    # Event
    'SeminarViewSet',
    'CertificationViewSet',
    'SeminarEnrollmentViewSet',
    'CertificationEnrollmentViewSet',
    # Student Items & Discounts
    'StudentItemViewSet',
    'StudentDiscountViewSet',
    # Contract
    'ContractViewSet',
    # Public API
    'PublicBrandListView',
    'PublicCourseListView',
    'PublicCourseDetailView',
    'PublicPackListView',
    'PublicPackDetailView',
    # Operation History
    'OperationHistoryViewSet',
]
