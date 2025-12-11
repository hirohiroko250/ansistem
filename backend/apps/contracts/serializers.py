"""
Contracts Serializers - シンプル版
"""
from rest_framework import serializers
from .models import (
    Product, Discount, Course, CourseItem,
    Pack, PackCourse,
    Seminar, Certification, CourseRequiredSeminar,
    Contract, StudentItem, SeminarEnrollment, CertificationEnrollment
)


# =============================================================================
# 商品 (Product)
# =============================================================================
class ProductListSerializer(serializers.ModelSerializer):
    """商品一覧"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    grade_name = serializers.CharField(source='grade.grade_name', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'product_code', 'product_name', 'item_type',
            'brand', 'brand_name', 'school', 'school_name',
            'grade', 'grade_name',
            'base_price', 'is_one_time', 'is_active'
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    """商品詳細"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    grade_name = serializers.CharField(source='grade.grade_name', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'product_code', 'product_name', 'product_name_short',
            'item_type',
            'brand', 'brand_name', 'school', 'school_name',
            'grade', 'grade_name',
            'base_price', 'tax_rate', 'is_tax_included',
            'prorate_first_month', 'is_one_time',
            'description', 'sort_order', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# =============================================================================
# 割引 (Discount)
# =============================================================================
class DiscountListSerializer(serializers.ModelSerializer):
    """割引一覧"""

    class Meta:
        model = Discount
        fields = [
            'id', 'discount_code', 'discount_name', 'discount_type',
            'calculation_type', 'value', 'is_active'
        ]


class DiscountDetailSerializer(serializers.ModelSerializer):
    """割引詳細"""

    class Meta:
        model = Discount
        fields = [
            'id', 'discount_code', 'discount_name', 'discount_type',
            'calculation_type', 'value',
            'valid_from', 'valid_until', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# =============================================================================
# コース (Course)
# =============================================================================
class CourseItemSerializer(serializers.ModelSerializer):
    """コース商品構成"""
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    price = serializers.SerializerMethodField()

    class Meta:
        model = CourseItem
        fields = [
            'id', 'product', 'product_name', 'quantity',
            'price_override', 'price', 'sort_order', 'is_active'
        ]

    def get_price(self, obj):
        return obj.get_price()


class CourseListSerializer(serializers.ModelSerializer):
    """コース一覧"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    price = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'course_code', 'course_name', 'brand', 'brand_name',
            'course_price', 'price', 'is_active'
        ]

    def get_price(self, obj):
        return obj.get_price()


class CourseDetailSerializer(serializers.ModelSerializer):
    """コース詳細"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    grade_name = serializers.CharField(source='grade.grade_name', read_only=True)
    course_items = CourseItemSerializer(many=True, read_only=True)
    price = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'course_code', 'course_name',
            'brand', 'brand_name', 'school', 'school_name',
            'grade', 'grade_name',
            'course_price', 'price',
            'description', 'sort_order', 'is_active',
            'course_items',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_price(self, obj):
        return obj.get_price()


# =============================================================================
# パック (Pack)
# =============================================================================
class PackCourseSerializer(serializers.ModelSerializer):
    """パックコース構成"""
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    course_price = serializers.SerializerMethodField()

    class Meta:
        model = PackCourse
        fields = [
            'id', 'course', 'course_name', 'course_price',
            'sort_order', 'is_active'
        ]

    def get_course_price(self, obj):
        return obj.course.get_price()


class PackListSerializer(serializers.ModelSerializer):
    """パック一覧"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    price = serializers.SerializerMethodField()

    class Meta:
        model = Pack
        fields = [
            'id', 'pack_code', 'pack_name', 'brand', 'brand_name',
            'pack_price', 'price', 'discount_type', 'discount_value', 'is_active'
        ]

    def get_price(self, obj):
        return obj.get_price()


class PackDetailSerializer(serializers.ModelSerializer):
    """パック詳細"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    pack_courses = PackCourseSerializer(many=True, read_only=True)
    price = serializers.SerializerMethodField()

    class Meta:
        model = Pack
        fields = [
            'id', 'pack_code', 'pack_name',
            'brand', 'brand_name',
            'pack_price', 'price', 'discount_type', 'discount_value',
            'description', 'sort_order', 'is_active',
            'pack_courses',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_price(self, obj):
        return obj.get_price()


# =============================================================================
# 講習 (Seminar)
# =============================================================================
class SeminarListSerializer(serializers.ModelSerializer):
    """講習一覧"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)

    class Meta:
        model = Seminar
        fields = [
            'id', 'seminar_code', 'seminar_name', 'seminar_type',
            'brand', 'brand_name', 'year', 'base_price', 'is_active'
        ]


class SeminarDetailSerializer(serializers.ModelSerializer):
    """講習詳細"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    grade_name = serializers.CharField(source='grade.grade_name', read_only=True)

    class Meta:
        model = Seminar
        fields = [
            'id', 'seminar_code', 'seminar_name', 'seminar_type',
            'brand', 'brand_name', 'grade', 'grade_name',
            'year', 'start_date', 'end_date', 'base_price',
            'description', 'sort_order', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# =============================================================================
# 検定 (Certification)
# =============================================================================
class CertificationListSerializer(serializers.ModelSerializer):
    """検定一覧"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)

    class Meta:
        model = Certification
        fields = [
            'id', 'certification_code', 'certification_name',
            'certification_type', 'level',
            'brand', 'brand_name', 'year', 'exam_fee', 'is_active'
        ]


class CertificationDetailSerializer(serializers.ModelSerializer):
    """検定詳細"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)

    class Meta:
        model = Certification
        fields = [
            'id', 'certification_code', 'certification_name',
            'certification_type', 'level',
            'brand', 'brand_name', 'year', 'exam_date', 'exam_fee',
            'description', 'sort_order', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# =============================================================================
# 生徒商品/請求明細 (StudentItem)
# =============================================================================
class StudentItemSerializer(serializers.ModelSerializer):
    """生徒商品（請求明細）"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = StudentItem
        fields = [
            'id', 'student', 'student_name', 'contract',
            'product', 'product_name',
            'billing_month', 'quantity', 'unit_price',
            'discount_amount', 'final_price', 'notes'
        ]
        read_only_fields = ['id']


# =============================================================================
# 契約 (Contract)
# =============================================================================
class ContractListSerializer(serializers.ModelSerializer):
    """契約一覧"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    course_name = serializers.CharField(source='course.course_name', read_only=True)

    class Meta:
        model = Contract
        fields = [
            'id', 'contract_no', 'student', 'student_name',
            'school', 'school_name', 'brand',
            'course', 'course_name',
            'contract_date', 'start_date', 'end_date',
            'status', 'monthly_total'
        ]


class ContractDetailSerializer(serializers.ModelSerializer):
    """契約詳細"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    school_name = serializers.CharField(source='school.school_name', read_only=True)
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True)
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    student_items = StudentItemSerializer(many=True, read_only=True)

    class Meta:
        model = Contract
        fields = [
            'id', 'contract_no',
            'student', 'student_name', 'guardian', 'guardian_name',
            'school', 'school_name', 'brand', 'brand_name',
            'course', 'course_name',
            'contract_date', 'start_date', 'end_date',
            'status', 'monthly_total', 'notes',
            'student_items',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ContractCreateSerializer(serializers.ModelSerializer):
    """契約作成"""

    class Meta:
        model = Contract
        fields = [
            'contract_no', 'student', 'guardian', 'school', 'brand',
            'course', 'contract_date', 'start_date', 'end_date',
            'notes'
        ]


# =============================================================================
# 顧客用契約シリアライザー (MyContract)
# =============================================================================
class MyContractStudentSerializer(serializers.Serializer):
    """顧客用生徒シリアライザー"""
    id = serializers.UUIDField()
    studentNo = serializers.CharField(source='student_no')
    fullName = serializers.CharField(source='full_name')
    grade = serializers.CharField(source='grade.grade_name', allow_null=True)


class MyContractSchoolSerializer(serializers.Serializer):
    """顧客用校舎シリアライザー"""
    id = serializers.UUIDField()
    schoolCode = serializers.CharField(source='school_code')
    schoolName = serializers.CharField(source='school_name')


class MyContractBrandSerializer(serializers.Serializer):
    """顧客用ブランドシリアライザー"""
    id = serializers.UUIDField()
    brandCode = serializers.CharField(source='brand_code')
    brandName = serializers.CharField(source='brand_name')


class MyContractCourseSerializer(serializers.Serializer):
    """顧客用コースシリアライザー"""
    id = serializers.UUIDField()
    courseCode = serializers.CharField(source='course_code')
    courseName = serializers.CharField(source='course_name')


class MyContractSerializer(serializers.ModelSerializer):
    """顧客用契約シリアライザー（保護者向け）"""
    contractNo = serializers.CharField(source='contract_no')
    student = MyContractStudentSerializer(read_only=True)
    school = MyContractSchoolSerializer(read_only=True)
    brand = MyContractBrandSerializer(read_only=True)
    course = MyContractCourseSerializer(read_only=True, allow_null=True)
    contractDate = serializers.DateField(source='contract_date')
    startDate = serializers.DateField(source='start_date')
    endDate = serializers.DateField(source='end_date', allow_null=True)
    monthlyTotal = serializers.DecimalField(source='monthly_total', max_digits=10, decimal_places=0)
    dayOfWeek = serializers.IntegerField(source='day_of_week', allow_null=True)
    startTime = serializers.TimeField(source='start_time', allow_null=True)
    endTime = serializers.TimeField(source='end_time', allow_null=True)

    class Meta:
        model = Contract
        fields = [
            'id', 'contractNo', 'student', 'school', 'brand', 'course',
            'status', 'contractDate', 'startDate', 'endDate',
            'monthlyTotal', 'dayOfWeek', 'startTime', 'endTime'
        ]


# =============================================================================
# 顧客用受講コースシリアライザー (MyStudentItem - StudentItemベース)
# =============================================================================
class MyStudentItemStudentSerializer(serializers.Serializer):
    """顧客用生徒シリアライザー（StudentItem用）"""
    id = serializers.UUIDField()
    studentNo = serializers.CharField(source='student_no')
    fullName = serializers.SerializerMethodField()
    grade = serializers.CharField(source='grade.grade_name', allow_null=True)

    def get_fullName(self, obj):
        return f"{obj.last_name} {obj.first_name}"


class MyStudentItemSchoolSerializer(serializers.Serializer):
    """顧客用校舎シリアライザー（StudentItem用）"""
    id = serializers.UUIDField()
    schoolCode = serializers.CharField(source='school_code')
    schoolName = serializers.CharField(source='school_name')


class MyStudentItemBrandSerializer(serializers.Serializer):
    """顧客用ブランドシリアライザー（StudentItem用）"""
    id = serializers.UUIDField()
    brandCode = serializers.CharField(source='brand_code')
    brandName = serializers.CharField(source='brand_name')


class MyStudentItemCourseSerializer(serializers.Serializer):
    """顧客用コースシリアライザー（StudentItem用）"""
    id = serializers.UUIDField()
    courseCode = serializers.CharField(source='course_code')
    courseName = serializers.CharField(source='course_name')


class MyStudentItemSerializer(serializers.ModelSerializer):
    """顧客用受講コースシリアライザー（保護者向け、StudentItemベース）

    生徒の受講中コース情報を返す。
    StudentItemをベースにして、student, school, brand, courseをネストで返す。
    フロントエンドのMyContract型に合わせたフィールド名で返す。
    """
    # MyContract型互換フィールド（フロントエンド型に合わせる）
    contractNo = serializers.SerializerMethodField()
    student = MyStudentItemStudentSerializer(read_only=True)
    school = MyStudentItemSchoolSerializer(read_only=True)
    brand = MyStudentItemBrandSerializer(read_only=True)
    course = MyStudentItemCourseSerializer(read_only=True, allow_null=True)
    status = serializers.SerializerMethodField()
    contractDate = serializers.DateField(source='start_date', allow_null=True)
    startDate = serializers.DateField(source='start_date', allow_null=True)
    endDate = serializers.SerializerMethodField()
    monthlyTotal = serializers.DecimalField(source='final_price', max_digits=10, decimal_places=0, allow_null=True, default=0)
    dayOfWeek = serializers.SerializerMethodField()
    startTime = serializers.SerializerMethodField()
    endTime = serializers.SerializerMethodField()

    class Meta:
        model = StudentItem
        fields = [
            'id', 'contractNo', 'student', 'school', 'brand', 'course',
            'status', 'contractDate', 'startDate', 'endDate',
            'monthlyTotal', 'dayOfWeek', 'startTime', 'endTime'
        ]

    def get_contractNo(self, obj):
        # StudentItemのIDをcontractNoとして使用
        return str(obj.id)[:8].upper()

    def get_status(self, obj):
        # StudentItemにはステータスがないので、常にactiveを返す
        return 'active'

    def get_endDate(self, obj):
        # StudentItemにはend_dateがないのでNone
        return None

    def get_dayOfWeek(self, obj):
        # StudentItemにはday_of_weekがないのでNone
        # 将来的にはLessonScheduleから取得することもできる
        return None

    def get_startTime(self, obj):
        # StudentItemにはstart_timeがないのでNone
        return None

    def get_endTime(self, obj):
        # StudentItemにはend_timeがないのでNone
        return None


# =============================================================================
# 講習申込 (SeminarEnrollment)
# =============================================================================
class SeminarEnrollmentListSerializer(serializers.ModelSerializer):
    """講習申込一覧"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    seminar_name = serializers.CharField(source='seminar.seminar_name', read_only=True)

    class Meta:
        model = SeminarEnrollment
        fields = [
            'id', 'student', 'student_name',
            'seminar', 'seminar_name',
            'status', 'unit_price', 'final_price', 'applied_at'
        ]


class SeminarEnrollmentDetailSerializer(serializers.ModelSerializer):
    """講習申込詳細"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    seminar_name = serializers.CharField(source='seminar.seminar_name', read_only=True)

    class Meta:
        model = SeminarEnrollment
        fields = [
            'id', 'student', 'student_name',
            'seminar', 'seminar_name',
            'status', 'applied_at',
            'unit_price', 'discount_amount', 'final_price',
            'is_required', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# =============================================================================
# 検定申込 (CertificationEnrollment)
# =============================================================================
class CertificationEnrollmentListSerializer(serializers.ModelSerializer):
    """検定申込一覧"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    certification_name = serializers.CharField(source='certification.certification_name', read_only=True)

    class Meta:
        model = CertificationEnrollment
        fields = [
            'id', 'student', 'student_name',
            'certification', 'certification_name',
            'status', 'exam_fee', 'final_price', 'score', 'applied_at'
        ]


class CertificationEnrollmentDetailSerializer(serializers.ModelSerializer):
    """検定申込詳細"""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    certification_name = serializers.CharField(source='certification.certification_name', read_only=True)

    class Meta:
        model = CertificationEnrollment
        fields = [
            'id', 'student', 'student_name',
            'certification', 'certification_name',
            'status', 'applied_at',
            'exam_fee', 'discount_amount', 'final_price',
            'score', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# =============================================================================
# 公開API用シリアライザ（顧客向け）
# =============================================================================

class PublicBrandCategorySerializer(serializers.Serializer):
    """公開ブランドカテゴリシリアライザ"""
    id = serializers.UUIDField()
    categoryCode = serializers.CharField(source='category_code')
    categoryName = serializers.CharField(source='category_name')
    categoryNameShort = serializers.CharField(source='category_name_short', allow_null=True)
    colorPrimary = serializers.CharField(source='color_primary', allow_null=True)
    sortOrder = serializers.IntegerField(source='sort_order')


class PublicBrandSerializer(serializers.Serializer):
    """公開ブランドシリアライザ"""
    id = serializers.UUIDField()
    brandCode = serializers.CharField(source='brand_code')
    brandName = serializers.CharField(source='brand_name')
    brandNameShort = serializers.CharField(source='brand_name_short', allow_null=True)
    brandType = serializers.CharField(source='brand_type', allow_null=True)
    description = serializers.CharField(allow_null=True)
    logoUrl = serializers.CharField(source='logo_url', allow_null=True)
    colorPrimary = serializers.CharField(source='color_primary', allow_null=True)
    colorSecondary = serializers.CharField(source='color_secondary', allow_null=True)
    category = PublicBrandCategorySerializer(allow_null=True)


class PublicCourseItemSerializer(serializers.Serializer):
    """公開コース商品シリアライザ"""
    productId = serializers.UUIDField(source='product.id')
    productName = serializers.CharField(source='product.product_name')
    productType = serializers.CharField(source='product.item_type')
    quantity = serializers.IntegerField()
    price = serializers.SerializerMethodField()

    def get_price(self, obj):
        return obj.get_price()


class PublicCourseSerializer(serializers.Serializer):
    """公開コースシリアライザ"""
    id = serializers.UUIDField()
    courseCode = serializers.CharField(source='course_code')
    courseName = serializers.CharField(source='course_name')
    description = serializers.CharField(allow_null=True, allow_blank=True)
    price = serializers.SerializerMethodField()
    isMonthly = serializers.SerializerMethodField()

    # ブランド情報
    brandId = serializers.UUIDField(source='brand.id', allow_null=True)
    brandName = serializers.CharField(source='brand.brand_name', allow_null=True)
    brandCode = serializers.CharField(source='brand.brand_code', allow_null=True)

    # 校舎情報
    schoolId = serializers.UUIDField(source='school.id', allow_null=True)
    schoolName = serializers.CharField(source='school.school_name', allow_null=True)

    # 学年情報
    gradeName = serializers.CharField(source='grade.grade_name', allow_null=True)

    # コースに含まれる商品
    items = PublicCourseItemSerializer(source='course_items', many=True, read_only=True)

    # チケット情報（開講時間割のフィルタ用）
    ticketId = serializers.SerializerMethodField()
    ticketCode = serializers.SerializerMethodField()
    ticketName = serializers.SerializerMethodField()

    def get_price(self, obj):
        return obj.get_price()

    def get_isMonthly(self, obj):
        # コース価格が設定されていれば月額コースとみなす
        return obj.course_price is not None

    def get_ticketId(self, obj):
        # コースに紐づく最初のチケットのIDを返す
        course_ticket = obj.course_tickets.first() if hasattr(obj, 'course_tickets') else None
        if course_ticket and course_ticket.ticket:
            return str(course_ticket.ticket.id)
        return None

    def get_ticketCode(self, obj):
        # コースに紐づく最初のチケットのコードを返す
        course_ticket = obj.course_tickets.first() if hasattr(obj, 'course_tickets') else None
        if course_ticket and course_ticket.ticket:
            return course_ticket.ticket.ticket_code
        return None

    def get_ticketName(self, obj):
        # コースに紐づく最初のチケット名を返す
        course_ticket = obj.course_tickets.first() if hasattr(obj, 'course_tickets') else None
        if course_ticket and course_ticket.ticket:
            return course_ticket.ticket.ticket_name
        return None


class PublicPackCourseSerializer(serializers.Serializer):
    """公開パックコースシリアライザ"""
    courseId = serializers.UUIDField(source='course.id')
    courseName = serializers.CharField(source='course.course_name')
    courseCode = serializers.CharField(source='course.course_code')
    coursePrice = serializers.SerializerMethodField()

    def get_coursePrice(self, obj):
        return obj.course.get_price()


class PublicPackTicketSerializer(serializers.Serializer):
    """公開パックチケットシリアライザ"""
    ticketId = serializers.UUIDField(source='ticket.id')
    ticketName = serializers.CharField(source='ticket.ticket_name')
    ticketCode = serializers.CharField(source='ticket.ticket_code')
    quantity = serializers.IntegerField()
    perWeek = serializers.IntegerField(source='per_week')


class PublicPackSerializer(serializers.Serializer):
    """公開パックシリアライザ"""
    id = serializers.UUIDField()
    packCode = serializers.CharField(source='pack_code')
    packName = serializers.CharField(source='pack_name')
    description = serializers.CharField(allow_null=True, allow_blank=True)
    price = serializers.SerializerMethodField()
    discountType = serializers.CharField(source='discount_type')
    discountValue = serializers.DecimalField(source='discount_value', max_digits=10, decimal_places=2)

    # ブランド情報
    brandId = serializers.UUIDField(source='brand.id', allow_null=True)
    brandName = serializers.CharField(source='brand.brand_name', allow_null=True)
    brandCode = serializers.CharField(source='brand.brand_code', allow_null=True)

    # 校舎情報
    schoolId = serializers.UUIDField(source='school.id', allow_null=True)
    schoolName = serializers.CharField(source='school.school_name', allow_null=True)

    # 学年情報
    gradeName = serializers.CharField(source='grade.grade_name', allow_null=True)

    # 含まれるコース
    courses = PublicPackCourseSerializer(source='pack_courses', many=True, read_only=True)

    # 含まれるチケット（クラス選択用）
    tickets = PublicPackTicketSerializer(source='pack_tickets', many=True, read_only=True)

    def get_price(self, obj):
        return obj.get_price()
