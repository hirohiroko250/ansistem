"""
StudentItem & StudentDiscount Serializers - 生徒商品・割引シリアライザ
StudentItemSerializer, StudentDiscountSerializer
"""
from rest_framework import serializers
from ..models import StudentItem, StudentDiscount


class StudentItemSerializer(serializers.ModelSerializer):
    """生徒商品（請求明細）"""
    student_name = serializers.SerializerMethodField()
    student_no = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()
    product_code = serializers.SerializerMethodField()
    item_type = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    brand_name = serializers.SerializerMethodField()
    school_name = serializers.SerializerMethodField()
    course_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentItem
        fields = [
            'id', 'old_id',
            'student', 'student_name', 'student_no',
            'contract',
            'product', 'product_name', 'product_code', 'item_type', 'category_name',
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
        if obj.product:
            return obj.product.product_name
        # productがない場合はnotesをフォールバック（インポートデータ用）
        return obj.notes or None

    def get_product_code(self, obj):
        return obj.product.product_code if obj.product else None

    def get_item_type(self, obj):
        return obj.product.item_type if obj.product else None

    def get_category_name(self, obj):
        """item_typeからカテゴリ名を取得"""
        if not obj.product or not obj.product.item_type:
            return None
        item_type_map = {
            'tuition': '授業料',
            'monthly_fee': '月会費',
            'facility': '設備費',
            'textbook': '教材費',
            'material': '教材費',
            'enrollment': '入会金',
            'enrollment_tuition': '入会時授業料',
            'enrollment_monthly_fee': '入会時月会費',
            'enrollment_facility': '入会時設備費',
            'enrollment_textbook': '入会時教材費',
            'bag': 'バッグ代',
            'abacus': 'そろばん代',
        }
        return item_type_map.get(obj.product.item_type, obj.product.item_type)

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
    product_name = serializers.SerializerMethodField()
    discount_unit_display = serializers.CharField(source='get_discount_unit_display', read_only=True)
    end_condition_display = serializers.CharField(source='get_end_condition_display', read_only=True)

    class Meta:
        model = StudentDiscount
        fields = [
            'id', 'old_id',
            'student', 'student_name', 'student_no',
            'guardian', 'guardian_name',
            'contract', 'student_item', 'product_name',
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

    def get_product_name(self, obj):
        """関連する明細の商品名を取得"""
        if obj.student_item_id and obj.student_item:
            return obj.student_item.product.product_name if obj.student_item.product else None
        return None
