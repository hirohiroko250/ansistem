"""
Contract Serializers - 契約シリアライザ
ContractSimpleListSerializer, ContractListSerializer, ContractDetailSerializer, ContractCreateSerializer
"""
from rest_framework import serializers
from ..models import Contract, Product, StudentItem, StudentDiscount
from .student_item import StudentItemSerializer, StudentDiscountSerializer


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
    school_name = serializers.SerializerMethodField()
    brand_name = serializers.SerializerMethodField()
    course_name = serializers.SerializerMethodField()
    student_items = serializers.SerializerMethodField()
    monthly_total = serializers.SerializerMethodField()
    discounts = serializers.SerializerMethodField()
    discount_total = serializers.SerializerMethodField()
    discount_max = serializers.SerializerMethodField()
    day_of_week = serializers.SerializerMethodField()
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()
    enrollment_fees = serializers.SerializerMethodField()
    is_enrollment_month = serializers.SerializerMethodField()
    textbook_options = serializers.SerializerMethodField()
    selected_textbook_ids = serializers.SerializerMethodField()

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
            'discount_applied', 'discount_type',
            'discounts', 'discount_total', 'discount_max',
            'day_of_week', 'start_time', 'end_time',
            'student_items',
            'textbook_options', 'selected_textbook_ids',
            'enrollment_fees', 'is_enrollment_month',
            'created_at', 'updated_at',
        ]

    def _find_student_items(self, obj):
        """生徒に関連するStudentItemを検索"""
        from django.db.models import Q

        all_items = StudentItem.objects.filter(
            Q(contract_id=obj.id) |
            Q(student_id=obj.student_id, brand_id=obj.brand_id) |
            Q(student_id=obj.student_id, school_id=obj.school_id)
        ).select_related('product', 'school').distinct()

        if all_items.exists():
            return all_items

        student_items = StudentItem.objects.filter(
            student_id=obj.student_id,
        ).select_related('product', 'school')
        return student_items

    def get_school_name(self, obj):
        """校舎名を取得（StudentItemから優先、なければContractから）"""
        related_items = self._find_student_items(obj)
        if related_items:
            for item in related_items:
                if hasattr(item, 'school') and item.school:
                    return item.school.school_name
                elif hasattr(item, 'school_id') and item.school_id:
                    from apps.schools.models import School
                    try:
                        school = School.objects.get(id=item.school_id)
                        return school.school_name
                    except School.DoesNotExist:
                        pass

        if obj.school:
            return obj.school.school_name
        return None

    def get_student_items(self, obj):
        """契約に紐づく生徒商品を取得"""
        if obj.course:
            course_items = obj.course.course_items.filter(is_active=True).select_related('product')
            if course_items.exists():
                items = []
                selected_textbook_ids = set(obj.selected_textbooks.values_list('id', flat=True))

                for ci in course_items:
                    if not ci.product:
                        continue

                    if ci.product.item_type == Product.ItemType.TEXTBOOK:
                        if ci.product_id not in selected_textbook_ids:
                            continue

                    items.append({
                        'id': str(ci.id),
                        'product_id': str(ci.product_id),
                        'product_name': ci.product.product_name if ci.product else '',
                        'item_type': ci.product.item_type if ci.product else '',
                        'quantity': ci.quantity,
                        'unit_price': ci.get_price(),
                        'final_price': ci.get_price() * ci.quantity,
                        'billing_month': None,
                    })
                return items

        related_items = self._find_student_items(obj)
        if related_items:
            return StudentItemSerializer(related_items, many=True).data

        return []

    def get_textbook_options(self, obj):
        """コースで選択可能な教材費オプションを返す"""
        if not obj.course:
            return []

        textbook_items = obj.course.course_items.filter(
            is_active=True,
            product__item_type=Product.ItemType.TEXTBOOK
        ).select_related('product')

        enrollment_month = None
        if obj.start_date:
            enrollment_month = obj.start_date.month

        options = []
        for ci in textbook_items:
            if not ci.product:
                continue

            if enrollment_month:
                price = ci.product.get_price_for_enrollment_month(enrollment_month)
            else:
                price = ci.get_price()

            options.append({
                'id': str(ci.product_id),
                'product_name': ci.product.product_name,
                'price': float(price) if price else 0,
                'base_price': float(ci.product.base_price) if ci.product.base_price else 0,
                'enrollment_month': enrollment_month,
            })
        return options

    def get_selected_textbook_ids(self, obj):
        """選択された教材のIDリストを返す"""
        return [str(p.id) for p in obj.selected_textbooks.all()]

    def get_is_enrollment_month(self, obj):
        """入会月かどうかを判定"""
        if not obj.start_date:
            return False
        return True

    def get_enrollment_fees(self, obj):
        """入会時費用を計算して返す"""
        if not obj.start_date or not obj.course:
            return []

        from apps.pricing.calculations import calculate_enrollment_fees
        from apps.pricing.views import calculate_prorated_by_day_of_week

        day_of_week = None

        related_items = self._find_student_items(obj)
        if related_items:
            for item in related_items:
                if hasattr(item, 'day_of_week') and item.day_of_week:
                    day_of_week = item.day_of_week
                    break

        if not day_of_week:
            day_of_week = 1

        try:
            prorated_info = calculate_prorated_by_day_of_week(obj.start_date, day_of_week)
            additional_tickets = prorated_info.get('remaining_count', 0)
            total_classes_in_month = prorated_info.get('total_count', 4)

            enrollment_fees = calculate_enrollment_fees(
                course=obj.course,
                tenant_id=str(obj.tenant_id),
                enrollment_date=obj.start_date,
                additional_tickets=additional_tickets,
                total_classes_in_month=total_classes_in_month,
                student=obj.student,
                guardian=obj.guardian,
            )

            result = []
            for fee in enrollment_fees:
                result.append({
                    'productId': fee['product_id'],
                    'productCode': fee['product_code'],
                    'productName': fee['product_name'],
                    'itemType': fee['item_type'],
                    'basePrice': fee['base_price'],
                    'calculatedPrice': fee['calculated_price'],
                    'calculationDetail': fee['calculation_detail'],
                })
            return result

        except Exception as e:
            import sys
            print(f"[ContractListSerializer.get_enrollment_fees] Error: {e}", file=sys.stderr)
            return []

    def get_monthly_total(self, obj):
        """月額合計を計算"""
        if obj.course:
            from decimal import Decimal
            total = Decimal('0')
            selected_textbook_ids = set(obj.selected_textbooks.values_list('id', flat=True))

            for ci in obj.course.course_items.filter(is_active=True):
                if not ci.product:
                    continue

                if ci.product.item_type == Product.ItemType.TEXTBOOK:
                    if ci.product_id not in selected_textbook_ids:
                        continue

                total += ci.get_price() * ci.quantity

            return total

        related_items = self._find_student_items(obj)
        if related_items:
            return sum(item.final_price or 0 for item in related_items)

        return 0

    def get_discounts(self, obj):
        """生徒の割引情報を取得"""
        discounts = StudentDiscount.objects.filter(
            student_id=obj.student_id,
            is_active=True,
        ).select_related('brand')

        brand_discounts = discounts.filter(brand_id=obj.brand_id)
        general_discounts = discounts.filter(brand_id__isnull=True)

        all_discounts = list(brand_discounts) + list(general_discounts)
        return StudentDiscountSerializer(all_discounts, many=True).data

    def get_discount_total(self, obj):
        """割引合計を計算"""
        discounts = StudentDiscount.objects.filter(
            student_id=obj.student_id,
            is_active=True,
        )
        discounts = discounts.filter(
            brand_id__isnull=True
        ) | discounts.filter(brand_id=obj.brand_id)

        total = sum(abs(d.amount or 0) for d in discounts)
        return total

    def get_discount_max(self, obj):
        """割引Max取得"""
        discount_max = 0
        if obj.course:
            course_items = obj.course.course_items.filter(is_active=True).select_related('product')
            for ci in course_items:
                if ci.product and ci.product.discount_max:
                    discount_max = max(discount_max, ci.product.discount_max)
        related_items = self._find_student_items(obj)
        for si in related_items:
            if hasattr(si, 'product') and si.product and si.product.discount_max:
                discount_max = max(discount_max, si.product.discount_max)
        return discount_max

    def get_day_of_week(self, obj):
        """曜日を取得"""
        if obj.day_of_week is not None:
            return obj.day_of_week
        related_items = self._find_student_items(obj)
        for si in related_items:
            if hasattr(si, 'day_of_week') and si.day_of_week is not None:
                return si.day_of_week
        return None

    def get_start_time(self, obj):
        """開始時間を取得"""
        if obj.start_time is not None:
            return obj.start_time
        related_items = self._find_student_items(obj)
        for si in related_items:
            if hasattr(si, 'start_time') and si.start_time is not None:
                return si.start_time
        return None

    def get_end_time(self, obj):
        """終了時間を取得"""
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
            'discount_applied', 'discount_type',
            'discounts', 'discount_total', 'discount_max',
            'day_of_week', 'start_time', 'end_time',
            'student_items',
            'textbook_options', 'selected_textbook_ids',
            'enrollment_fees', 'is_enrollment_month',
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
