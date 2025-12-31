"""
Contracts Admin Package
契約関連Admin
"""

# Product
from .product import (
    ProductPriceInline,
    ProductAdmin,
    ProductPriceAdmin,
)

# ProductSet
from .product_set import (
    ProductSetItemInline,
    ProductSetAdmin,
    ProductSetItemAdmin,
)

# Discount
from .discount import DiscountAdmin

# Course
from .course import (
    CourseItemInline,
    CourseAdmin,
    CourseItemAdmin,
    CourseRequiredSeminarAdmin,
)

# Pack
from .pack import (
    PackCourseInline,
    PackItemInline,
    PackAdmin,
    PackCourseAdmin,
)

# Seminar
from .seminar import (
    SeminarAdmin,
    CertificationAdmin,
)

# Ticket
from .ticket import (
    TicketAdmin,
    CourseTicketInline,
    CourseTicketAdmin,
    PackTicketInline,
    PackTicketAdmin,
)

# Contract
from .contract import (
    StudentItemInline,
    ContractAdmin,
    StudentItemAdmin,
    StudentDiscountAdmin,
    SeminarEnrollmentAdmin,
    CertificationEnrollmentAdmin,
)

# History
from .history import (
    ContractHistoryInline,
    ContractHistoryAdmin,
    SystemAuditLogAdmin,
)

# AdditionalTicket
from .additional_ticket import (
    AdditionalTicketDateInline,
    AdditionalTicketAdmin,
)


# =============================================================================
# 動的にinlinesを追加（モデル定義順序の問題を回避）
# =============================================================================
# CourseAdminにCourseTicketInlineを追加
CourseAdmin.inlines = [CourseItemInline, CourseTicketInline]

# PackAdminにPackTicketInlineを追加
PackAdmin.inlines = [PackCourseInline, PackItemInline, PackTicketInline]

# ContractAdminにContractHistoryInlineを追加
ContractAdmin.inlines = [StudentItemInline, ContractHistoryInline]


__all__ = [
    # Product
    'ProductPriceInline',
    'ProductAdmin',
    'ProductPriceAdmin',
    # ProductSet
    'ProductSetItemInline',
    'ProductSetAdmin',
    'ProductSetItemAdmin',
    # Discount
    'DiscountAdmin',
    # Course
    'CourseItemInline',
    'CourseAdmin',
    'CourseItemAdmin',
    'CourseRequiredSeminarAdmin',
    # Pack
    'PackCourseInline',
    'PackItemInline',
    'PackAdmin',
    'PackCourseAdmin',
    # Seminar
    'SeminarAdmin',
    'CertificationAdmin',
    # Ticket
    'TicketAdmin',
    'CourseTicketInline',
    'CourseTicketAdmin',
    'PackTicketInline',
    'PackTicketAdmin',
    # Contract
    'StudentItemInline',
    'ContractAdmin',
    'StudentItemAdmin',
    'StudentDiscountAdmin',
    'SeminarEnrollmentAdmin',
    'CertificationEnrollmentAdmin',
    # History
    'ContractHistoryInline',
    'ContractHistoryAdmin',
    'SystemAuditLogAdmin',
    # AdditionalTicket
    'AdditionalTicketDateInline',
    'AdditionalTicketAdmin',
]
