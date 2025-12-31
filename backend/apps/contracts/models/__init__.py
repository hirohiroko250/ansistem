"""
Contracts Models - 契約アプリのモデル

このパッケージは契約関連のモデルを含みます：
- 商品関連: Product, ProductPrice, ProductSet, ProductSetItem
- 割引: Discount
- コース: Course, CourseItem
- 講習・検定: Seminar, CourseSeminar, CourseRequiredSeminar, Certification
- チケット: Ticket, CourseTicket, AdditionalTicket, AdditionalTicketDate
- パック: Pack, PackCourse, PackItem, PackTicket
- 契約: Contract, StudentItem, StudentDiscount
- 申込: SeminarEnrollment, CertificationEnrollment
- 履歴・監査: ContractChangeRequest, ContractHistory, SystemAuditLog, DiscountOperationLog
"""

# 商品関連
from .product import (
    Product,
    ProductPrice,
    ProductSet,
    ProductSetItem,
)

# 割引
from .discount import Discount

# コース
from .course import (
    Course,
    CourseItem,
)

# 講習・検定
from .seminar import (
    Seminar,
    CourseSeminar,
    CourseRequiredSeminar,
    Certification,
)

# チケット
from .ticket import (
    Ticket,
    CourseTicket,
    AdditionalTicket,
    AdditionalTicketDate,
)

# パック
from .pack import (
    Pack,
    PackCourse,
    PackItem,
    PackTicket,
)

# 契約
from .contract import (
    Contract,
    StudentItem,
    StudentDiscount,
)

# 申込
from .enrollment import (
    SeminarEnrollment,
    CertificationEnrollment,
)

# 履歴・監査
from .history import (
    ContractChangeRequest,
    ContractHistory,
    SystemAuditLog,
    DiscountOperationLog,
)

__all__ = [
    # 商品関連
    'Product',
    'ProductPrice',
    'ProductSet',
    'ProductSetItem',
    # 割引
    'Discount',
    # コース
    'Course',
    'CourseItem',
    # 講習・検定
    'Seminar',
    'CourseSeminar',
    'CourseRequiredSeminar',
    'Certification',
    # チケット
    'Ticket',
    'CourseTicket',
    'AdditionalTicket',
    'AdditionalTicketDate',
    # パック
    'Pack',
    'PackCourse',
    'PackItem',
    'PackTicket',
    # 契約
    'Contract',
    'StudentItem',
    'StudentDiscount',
    # 申込
    'SeminarEnrollment',
    'CertificationEnrollment',
    # 履歴・監査
    'ContractChangeRequest',
    'ContractHistory',
    'SystemAuditLog',
    'DiscountOperationLog',
]
