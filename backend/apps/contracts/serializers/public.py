"""
Public API Serializers - 公開API用シリアライザ（顧客向け）
PublicBrandSerializer, PublicCourseSerializer, PublicPackSerializer
"""
from rest_framework import serializers
from ..models import Product


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
    tuitionPrice = serializers.SerializerMethodField()

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

    # チケット情報
    ticketId = serializers.SerializerMethodField()
    ticketCode = serializers.SerializerMethodField()
    ticketName = serializers.SerializerMethodField()
    perWeek = serializers.SerializerMethodField()

    def _get_first_course_ticket(self, obj):
        """最初のコースチケットを取得（キャッシュ付き）"""
        cache_attr = '_cached_first_course_ticket'
        if not hasattr(obj, cache_attr):
            # prefetch済みのデータを使用（追加クエリなし）
            course_tickets = list(obj.course_tickets.all())
            setattr(obj, cache_attr, course_tickets[0] if course_tickets else None)
        return getattr(obj, cache_attr)

    def get_price(self, obj):
        return obj.get_price()

    def get_tuitionPrice(self, obj):
        """ProductPriceから月額授業料（税込）を取得"""
        from datetime import date
        from decimal import Decimal

        # prefetch済みのcourse_itemsを使用（追加クエリなし）
        for ci in obj.course_items.all():
            if not ci.is_active:
                continue
            product = ci.product
            if product and product.is_active and product.item_type == Product.ItemType.TUITION:
                tax_rate = product.tax_rate or Decimal('0.1')
                try:
                    # prefetch済みのpricesを使用
                    prices = list(product.prices.all())
                    product_price = next((p for p in prices if p.is_active), None)
                    if product_price:
                        current_month = date.today().month
                        price = product_price.get_enrollment_price(current_month)
                        if price is not None:
                            return int(Decimal(str(price)) * (1 + tax_rate))
                except Exception:
                    pass
                base_price = product.base_price or Decimal('0')
                return int(base_price * (1 + tax_rate))
        return 0

    def get_isMonthly(self, obj):
        course_name = obj.course_name or ''
        monthly_patterns = ['週1回', '週2回', '週3回', '週4回', '週5回', '週6回', 'Free', '月2回', '月4回']
        return any(pattern in course_name for pattern in monthly_patterns)

    def get_ticketId(self, obj):
        course_ticket = self._get_first_course_ticket(obj)
        if course_ticket and course_ticket.ticket:
            return str(course_ticket.ticket.id)
        return None

    def get_ticketCode(self, obj):
        course_ticket = self._get_first_course_ticket(obj)
        if course_ticket and course_ticket.ticket:
            return course_ticket.ticket.ticket_code
        return None

    def get_ticketName(self, obj):
        course_ticket = self._get_first_course_ticket(obj)
        if course_ticket and course_ticket.ticket:
            return course_ticket.ticket.ticket_name
        return None

    def get_perWeek(self, obj):
        """コースチケットの週あたり回数を取得"""
        course_ticket = self._get_first_course_ticket(obj)
        if course_ticket:
            return course_ticket.per_week
        return 1  # デフォルト値


class PublicPackCourseSerializer(serializers.Serializer):
    """公開パックコースシリアライザ"""
    courseId = serializers.UUIDField(source='course.id')
    courseName = serializers.CharField(source='course.course_name')
    courseCode = serializers.CharField(source='course.course_code')
    coursePrice = serializers.SerializerMethodField()
    ticketId = serializers.SerializerMethodField()
    ticketCode = serializers.SerializerMethodField()
    ticketName = serializers.SerializerMethodField()

    def get_coursePrice(self, obj):
        return obj.course.get_price()

    def _get_first_ticket(self, obj):
        """コースに紐付く最初のチケットを取得（キャッシュ付き）"""
        cache_attr = '_cached_first_ticket'
        if not hasattr(obj, cache_attr):
            # prefetch済みのデータを使用（追加クエリなし）
            course_tickets = list(obj.course.course_tickets.all())
            course_ticket = course_tickets[0] if course_tickets else None
            setattr(obj, cache_attr, course_ticket.ticket if course_ticket else None)
        return getattr(obj, cache_attr)

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

    # 含まれるチケット
    tickets = PublicPackTicketSerializer(source='pack_tickets', many=True, read_only=True)

    def get_price(self, obj):
        return obj.get_price()
