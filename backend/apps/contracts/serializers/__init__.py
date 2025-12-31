"""
Contracts Serializers Package
契約関連シリアライザ
"""

# Product
from .product import (
    ProductListSerializer,
    ProductDetailSerializer,
)

# Discount
from .discount import (
    DiscountListSerializer,
    DiscountDetailSerializer,
)

# Course
from .course import (
    CourseItemSerializer,
    CourseListSerializer,
    CourseDetailSerializer,
)

# Pack
from .pack import (
    PackCourseSerializer,
    PackListSerializer,
    PackDetailSerializer,
)

# Seminar
from .seminar import (
    SeminarListSerializer,
    SeminarDetailSerializer,
)

# Certification
from .certification import (
    CertificationListSerializer,
    CertificationDetailSerializer,
)

# StudentItem & StudentDiscount
from .student_item import (
    StudentItemSerializer,
    StudentDiscountSerializer,
)

# Contract
from .contract import (
    ContractSimpleListSerializer,
    ContractListSerializer,
    ContractDetailSerializer,
    ContractCreateSerializer,
)

# My Contract (Customer-facing)
from .my_contract import (
    MyContractStudentSerializer,
    MyContractSchoolSerializer,
    MyContractBrandSerializer,
    MyContractCourseSerializer,
    MyContractSerializer,
    MyStudentItemStudentSerializer,
    MyStudentItemSchoolSerializer,
    MyStudentItemBrandSerializer,
    MyStudentItemCourseSerializer,
    MyStudentItemTicketSerializer,
    MyStudentItemSerializer,
)

# Enrollment
from .enrollment import (
    SeminarEnrollmentListSerializer,
    SeminarEnrollmentDetailSerializer,
    CertificationEnrollmentListSerializer,
    CertificationEnrollmentDetailSerializer,
)

# Public API
from .public import (
    PublicBrandCategorySerializer,
    PublicBrandSerializer,
    PublicCourseItemSerializer,
    PublicCourseSerializer,
    PublicPackCourseSerializer,
    PublicPackTicketSerializer,
    PublicPackSerializer,
)


__all__ = [
    # Product
    'ProductListSerializer',
    'ProductDetailSerializer',
    # Discount
    'DiscountListSerializer',
    'DiscountDetailSerializer',
    # Course
    'CourseItemSerializer',
    'CourseListSerializer',
    'CourseDetailSerializer',
    # Pack
    'PackCourseSerializer',
    'PackListSerializer',
    'PackDetailSerializer',
    # Seminar
    'SeminarListSerializer',
    'SeminarDetailSerializer',
    # Certification
    'CertificationListSerializer',
    'CertificationDetailSerializer',
    # StudentItem & StudentDiscount
    'StudentItemSerializer',
    'StudentDiscountSerializer',
    # Contract
    'ContractSimpleListSerializer',
    'ContractListSerializer',
    'ContractDetailSerializer',
    'ContractCreateSerializer',
    # My Contract
    'MyContractStudentSerializer',
    'MyContractSchoolSerializer',
    'MyContractBrandSerializer',
    'MyContractCourseSerializer',
    'MyContractSerializer',
    'MyStudentItemStudentSerializer',
    'MyStudentItemSchoolSerializer',
    'MyStudentItemBrandSerializer',
    'MyStudentItemCourseSerializer',
    'MyStudentItemTicketSerializer',
    'MyStudentItemSerializer',
    # Enrollment
    'SeminarEnrollmentListSerializer',
    'SeminarEnrollmentDetailSerializer',
    'CertificationEnrollmentListSerializer',
    'CertificationEnrollmentDetailSerializer',
    # Public API
    'PublicBrandCategorySerializer',
    'PublicBrandSerializer',
    'PublicCourseItemSerializer',
    'PublicCourseSerializer',
    'PublicPackCourseSerializer',
    'PublicPackTicketSerializer',
    'PublicPackSerializer',
]
