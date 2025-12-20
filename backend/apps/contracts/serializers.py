"""
Contracts Serializers - シンプル版
"""
from rest_framework import serializers
from .models import (
    Product, Discount, Course, CourseItem,
    Pack, PackCourse,
    Seminar, Certification, CourseRequiredSeminar,
    Contract, StudentItem, StudentDiscount, SeminarEnrollment, CertificationEnrollment
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
# 割引 (StudentDiscount)
# =============================================================================
class StudentDiscountSerializer(serializers.ModelSerializer):
    """生徒割引シリアライザー"""
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True, allow_null=True)
    product_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentDiscount
        fields = [
            'id', 'discount_name', 'amount', 'discount_unit',
            'student_item_id', 'product_name',  # 明細単位の割引対応
            'brand', 'brand_name',
            'start_date', 'end_date', 'is_recurring', 'is_active'
        ]
        read_only_fields = ['id']

    def get_product_name(self, obj):
        """関連する明細の商品名を取得"""
        if obj.student_item_id and obj.student_item:
            return obj.student_item.product.product_name if obj.student_item.product else None
        return None


# =============================================================================
# 生徒商品/請求明細 (StudentItem)
# =============================================================================
class StudentItemSerializer(serializers.ModelSerializer):
    """生徒商品（請求明細）"""
    student_name = serializers.SerializerMethodField()
    student_no = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()
    product_code = serializers.SerializerMethodField()
    brand_name = serializers.SerializerMethodField()
    school_name = serializers.SerializerMethodField()
    course_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentItem
        fields = [
            'id', 'old_id',
            'student', 'student_name', 'student_no',
            'contract',
            'product', 'product_name', 'product_code',
            'brand', 'brand_name',
            'school', 'school_name',
            'course', 'course_name',
            'start_date', 'day_of_week', 'start_time', 'end_time',
            'billing_month', 'quantity', 'unit_price',
            'discount_amount', 'final_price', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_student_name(self, obj):
        if obj.student:
            return obj.student.full_name or f"{obj.student.last_name}{obj.student.first_name}"
        return None

    def get_student_no(self, obj):
        return obj.student.student_no if obj.student else None

    def get_product_name(self, obj):
        return obj.product.product_name if obj.product else None

    def get_product_code(self, obj):
        return obj.product.product_code if obj.product else None

    def get_brand_name(self, obj):
        return obj.brand.brand_name if obj.brand else None

    def get_school_name(self, obj):
        return obj.school.school_name if obj.school else None

    def get_course_name(self, obj):
        return obj.course.course_name if obj.course else None


class StudentDiscountSerializer(serializers.ModelSerializer):
    """生徒割引"""
    student_name = serializers.SerializerMethodField()
    student_no = serializers.SerializerMethodField()
    guardian_name = serializers.SerializerMethodField()
    brand_name = serializers.SerializerMethodField()
    discount_unit_display = serializers.CharField(source='get_discount_unit_display', read_only=True)
    end_condition_display = serializers.CharField(source='get_end_condition_display', read_only=True)

    class Meta:
        model = StudentDiscount
        fields = [
            'id', 'old_id',
            'student', 'student_name', 'student_no',
            'guardian', 'guardian_name',
            'contract', 'student_item',
            'brand', 'brand_name',
            'discount_name', 'amount', 'discount_unit', 'discount_unit_display',
            'start_date', 'end_date',
            'is_recurring', 'is_auto', 'end_condition', 'end_condition_display',
            'is_active', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_student_name(self, obj):
        if obj.student:
            return obj.student.full_name or f"{obj.student.last_name}{obj.student.first_name}"
        return None

    def get_student_no(self, obj):
        return obj.student.student_no if obj.student else None

    def get_guardian_name(self, obj):
        if obj.guardian:
            return obj.guardian.full_name or f"{obj.guardian.last_name}{obj.guardian.first_name}"
        return None

    def get_brand_name(self, obj):
        return obj.brand.brand_name if obj.brand else None


# =============================================================================
# 契約 (Contract)
# =============================================================================
class ContractSimpleListSerializer(serializers.ModelSerializer):
    """契約一覧（高速版）- N+1問題を回避するためシンプルなフィールドのみ"""
    student_name = serializers.SerializerMethodField()
    school_name = serializers.CharField(source='school.school_name', read_only=True, allow_null=True)
    brand_name = serializers.CharField(source='brand.brand_name', read_only=True, allow_null=True)
    course_name = serializers.CharField(source='course.course_name', read_only=True, allow_null=True)

    class Meta:
        model = Contract
        fields = [
            'id', 'contract_no', 'student', 'student_name',
            'school', 'school_name', 'brand', 'brand_name',
            'course', 'course_name',
            'contract_date', 'start_date', 'end_date',
            'status', 'monthly_total',
            'discount_applied', 'discount_type',
            'day_of_week', 'start_time', 'end_time',
            'created_at', 'updated_at',
        ]

    def get_student_name(self, obj):
        if obj.student:
            return obj.student.full_name or f"{obj.student.last_name}{obj.student.first_name}"
        return None


class ContractListSerializer(serializers.ModelSerializer):
    """契約一覧（詳細版）"""
    student_name = serializers.SerializerMethodField()
    school_name = serializers.SerializerMethodField()  # StudentItemからフォールバック
    brand_name = serializers.SerializerMethodField()
    course_name = serializers.SerializerMethodField()
    student_items = serializers.SerializerMethodField()
    monthly_total = serializers.SerializerMethodField()
    discounts = serializers.SerializerMethodField()
    discount_total = serializers.SerializerMethodField()
    discount_max = serializers.SerializerMethodField()
    # スケジュール（StudentItemからフォールバック）
    day_of_week = serializers.SerializerMethodField()
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()

    def get_student_name(self, obj):
        if obj.student:
            return obj.student.full_name or f"{obj.student.last_name}{obj.student.first_name}"
        return None

    def get_brand_name(self, obj):
        return obj.brand.brand_name if obj.brand else None

    def get_course_name(self, obj):
        return obj.course.course_name if obj.course else None

    class Meta:
        model = Contract
        fields = [
            'id', 'contract_no', 'student', 'student_name',
            'school', 'school_name', 'brand', 'brand_name',
            'course', 'course_name',
            'contract_date', 'start_date', 'end_date',
            'status', 'monthly_total',
            # 割引関連
            'discount_applied', 'discount_type',
            'discounts', 'discount_total', 'discount_max',
            # スケジュール
            'day_of_week', 'start_time', 'end_time',
            # 料金内訳
            'student_items',
            # タイムスタンプ
            'created_at', 'updated_at',
        ]

    def _find_student_items(self, obj):
        """生徒に関連するStudentItemを検索（全て取得して結合）"""
        from django.db.models import Q

        # 生徒の全てのStudentItemを取得（複数条件をORで結合）
        # 1. 契約に直接紐付いているアイテム
        # 2. 生徒 + ブランド でマッチするアイテム（契約なしも含む）
        # 3. 生徒 + 校舎 でマッチするアイテム（契約なしも含む）
        all_items = StudentItem.objects.filter(
            Q(contract_id=obj.id) |  # 直接紐付け
            Q(student_id=obj.student_id, brand_id=obj.brand_id) |  # 生徒+ブランド
            Q(student_id=obj.student_id, school_id=obj.school_id)  # 生徒+校舎
        ).select_related('product', 'school').distinct()

        if all_items.exists():
            return all_items

        # フォールバック: 生徒のみで検索
        student_items = StudentItem.objects.filter(
            student_id=obj.student_id,
        ).select_related('product', 'school')
        return student_items

    def get_school_name(self, obj):
        """校舎名を取得（StudentItemから優先、なければContractから）"""
        # 1. StudentItemから校舎を取得（最初のアイテムの校舎）
        related_items = self._find_student_items(obj)
        if related_items:
            for item in related_items:
                if hasattr(item, 'school') and item.school:
                    return item.school.school_name
                elif hasattr(item, 'school_id') and item.school_id:
                    # school_idはあるがschoolオブジェクトがない場合
                    from apps.schools.models import School
                    try:
                        school = School.objects.get(id=item.school_id)
                        return school.school_name
                    except School.DoesNotExist:
                        pass

        # 2. Contractの校舎にフォールバック
        if obj.school:
            return obj.school.school_name
        return None

    def get_student_items(self, obj):
        """契約に紐づく生徒商品を取得"""
        # 1. コースの商品構成から生成（優先）
        if obj.course:
            course_items = obj.course.course_items.filter(is_active=True).select_related('product')
            if course_items.exists():
                items = []
                for ci in course_items:
                    items.append({
                        'id': str(ci.id),
                        'product_name': ci.product.product_name if ci.product else '',
                        'quantity': ci.quantity,
                        'unit_price': ci.get_price(),
                        'final_price': ci.get_price() * ci.quantity,
                        'billing_month': None,  # コース構成は請求月なし
                    })
                return items

        # 2. StudentItemを検索（全て返す、フロントエンドでフィルタ）
        related_items = self._find_student_items(obj)
        if related_items:
            return StudentItemSerializer(related_items, many=True).data

        return []

    def get_monthly_total(self, obj):
        """月額合計を計算"""
        # 契約に設定されている場合はそれを使用
        if obj.monthly_total and obj.monthly_total > 0:
            return obj.monthly_total

        # コースの価格を取得
        if obj.course:
            return obj.course.get_price()

        # StudentItemから計算
        related_items = self._find_student_items(obj)
        if related_items:
            return sum(item.final_price or 0 for item in related_items)

        return 0

    def get_discounts(self, obj):
        """生徒の割引情報を取得"""
        # 生徒に紐づく有効な割引を取得
        discounts = StudentDiscount.objects.filter(
            student_id=obj.student_id,
            is_active=True,
        ).select_related('brand')

        # ブランドでフィルタ（ブランド指定がある割引のみ）
        brand_discounts = discounts.filter(brand_id=obj.brand_id)
        general_discounts = discounts.filter(brand_id__isnull=True)

        # 結合して返す
        all_discounts = list(brand_discounts) + list(general_discounts)
        return StudentDiscountSerializer(all_discounts, many=True).data

    def get_discount_total(self, obj):
        """割引合計を計算（負の値は絶対値で計算）"""
        discounts = StudentDiscount.objects.filter(
            student_id=obj.student_id,
            is_active=True,
        )
        # ブランド指定またはブランドなしの割引
        discounts = discounts.filter(
            brand_id__isnull=True
        ) | discounts.filter(brand_id=obj.brand_id)

        # 割引額は負の値で格納されている場合があるため、絶対値で計算
        total = sum(abs(d.amount or 0) for d in discounts)
        return total

    def get_discount_max(self, obj):
        """割引Max取得（契約に紐づくコースまたは商品から）"""
        discount_max = 0
        # コースの商品から割引Maxを取得
        if obj.course:
            course_items = obj.course.course_items.filter(is_active=True).select_related('product')
            for ci in course_items:
                if ci.product and ci.product.discount_max:
                    discount_max = max(discount_max, ci.product.discount_max)
        # StudentItemから商品の割引Maxも確認
        related_items = self._find_student_items(obj)
        for si in related_items:
            if hasattr(si, 'product') and si.product and si.product.discount_max:
                discount_max = max(discount_max, si.product.discount_max)
        return discount_max

    def get_day_of_week(self, obj):
        """曜日を取得（ContractまたはStudentItemから）"""
        # 契約自体に曜日があればそれを使用
        if obj.day_of_week is not None:
            return obj.day_of_week
        # StudentItemから曜日を取得
        related_items = self._find_student_items(obj)
        for si in related_items:
            if hasattr(si, 'day_of_week') and si.day_of_week is not None:
                return si.day_of_week
        return None

    def get_start_time(self, obj):
        """開始時間を取得（ContractまたはStudentItemから）"""
        if obj.start_time is not None:
            return obj.start_time
        related_items = self._find_student_items(obj)
        for si in related_items:
            if hasattr(si, 'start_time') and si.start_time is not None:
                return si.start_time
        return None

    def get_end_time(self, obj):
        """終了時間を取得（ContractまたはStudentItemから）"""
        if obj.end_time is not None:
            return obj.end_time
        related_items = self._find_student_items(obj)
        for si in related_items:
            if hasattr(si, 'end_time') and si.end_time is not None:
                return si.end_time
        return None


class ContractDetailSerializer(ContractListSerializer):
    """契約詳細（ContractListSerializerを継承）"""
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)

    class Meta:
        model = Contract
        fields = [
            'id', 'contract_no',
            'student', 'student_name', 'guardian', 'guardian_name',
            'school', 'school_name', 'brand', 'brand_name',
            'course', 'course_name',
            'contract_date', 'start_date', 'end_date',
            'status', 'monthly_total', 'notes',
            # 割引関連
            'discount_applied', 'discount_type',
            'discounts', 'discount_total', 'discount_max',
            # スケジュール
            'day_of_week', 'start_time', 'end_time',
            # 料金内訳
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


class MyStudentItemTicketSerializer(serializers.Serializer):
    """顧客用チケットシリアライザー（StudentItem用）"""
    id = serializers.UUIDField()
    ticketCode = serializers.CharField(source='ticket_code')
    ticketName = serializers.CharField(source='ticket_name')
    ticketType = serializers.CharField(source='ticket_type', allow_null=True)
    ticketCategory = serializers.CharField(source='ticket_category', allow_null=True)
    durationMinutes = serializers.IntegerField(source='duration_minutes', allow_null=True)


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
    ticket = serializers.SerializerMethodField()  # コースに紐づくチケット
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
            'id', 'contractNo', 'student', 'school', 'brand', 'course', 'ticket',
            'status', 'contractDate', 'startDate', 'endDate',
            'monthlyTotal', 'dayOfWeek', 'startTime', 'endTime'
        ]

    def get_contractNo(self, obj):
        # StudentItemのIDをcontractNoとして使用
        return str(obj.id)[:8].upper()

    def get_ticket(self, obj):
        """StudentItemまたはコースに紐づくチケットを取得"""
        # 1. StudentItemに直接ticketが紐づいている場合
        if hasattr(obj, 'ticket') and obj.ticket:
            return MyStudentItemTicketSerializer(obj.ticket).data

        # 2. コースがある場合はCourseTicketから取得
        if obj.course:
            from .models import CourseTicket
            course_ticket = CourseTicket.objects.filter(
                course=obj.course,
                deleted_at__isnull=True
            ).select_related('ticket').first()
            if course_ticket and course_ticket.ticket:
                return MyStudentItemTicketSerializer(course_ticket.ticket).data
        return None

    def get_status(self, obj):
        # StudentItemにはステータスがないので、常にactiveを返す
        return 'active'

    def get_endDate(self, obj):
        # StudentItemにはend_dateがないのでNone
        return None

    def get_dayOfWeek(self, obj):
        # StudentItemの曜日を取得（直接または契約から）
        if obj.day_of_week is not None:
            return obj.day_of_week
        if obj.contract and obj.contract.day_of_week is not None:
            return obj.contract.day_of_week
        return None

    def get_startTime(self, obj):
        # StudentItemの開始時間を取得（直接または契約から）
        if obj.start_time:
            return obj.start_time.strftime('%H:%M:%S')
        if obj.contract and obj.contract.start_time:
            return obj.contract.start_time.strftime('%H:%M:%S')
        return None

    def get_endTime(self, obj):
        # StudentItemの終了時間を取得（直接または契約から）
        if obj.end_time:
            return obj.end_time.strftime('%H:%M:%S')
        if obj.contract and obj.contract.end_time:
            return obj.contract.end_time.strftime('%H:%M:%S')
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
    tuitionPrice = serializers.SerializerMethodField()  # ProductPriceからの月額授業料（税込）

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

    def get_tuitionPrice(self, obj):
        """ProductPriceから月額授業料（税込）を取得"""
        from datetime import date
        from decimal import Decimal

        # CourseItemから授業料商品を探す
        for ci in obj.course_items.filter(is_active=True).select_related('product'):
            product = ci.product
            if product and product.is_active and product.item_type == Product.ItemType.TUITION:
                tax_rate = product.tax_rate or Decimal('0.1')
                # ProductPriceから現在の月の料金を取得
                try:
                    product_price = product.prices.filter(is_active=True).first()
                    if product_price:
                        current_month = date.today().month
                        price = product_price.get_enrollment_price(current_month)
                        if price is not None:
                            return int(Decimal(str(price)) * (1 + tax_rate))
                except Exception:
                    pass
                # フォールバック: base_price
                base_price = product.base_price or Decimal('0')
                return int(base_price * (1 + tax_rate))
        return 0

    def get_isMonthly(self, obj):
        # 月額コース判定：コース名に週回数やFreeが含まれる場合
        course_name = obj.course_name or ''
        monthly_patterns = ['週1回', '週2回', '週3回', '週4回', '週5回', '週6回', 'Free', '月2回', '月4回']
        return any(pattern in course_name for pattern in monthly_patterns)

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
    # コースに紐付くチケット情報（CourseTicketから取得）
    ticketId = serializers.SerializerMethodField()
    ticketCode = serializers.SerializerMethodField()
    ticketName = serializers.SerializerMethodField()

    def get_coursePrice(self, obj):
        return obj.course.get_price()

    def _get_first_ticket(self, obj):
        """コースに紐付く最初のチケットを取得"""
        course_ticket = obj.course.course_tickets.first()
        return course_ticket.ticket if course_ticket else None

    def get_ticketId(self, obj):
        ticket = self._get_first_ticket(obj)
        return str(ticket.id) if ticket else None

    def get_ticketCode(self, obj):
        ticket = self._get_first_ticket(obj)
        return ticket.ticket_code if ticket else None

    def get_ticketName(self, obj):
        ticket = self._get_first_ticket(obj)
        return ticket.ticket_name if ticket else None


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
