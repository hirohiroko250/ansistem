"""
Contracts Models - シンプル版

T03: 商品マスタ (Product)
T07: 割引マスタ (Discount)
T08: コース (Course)
T52: コース→商品紐づけ (CourseItem)
T11: 講習マスタ (Seminar)
T12: 検定マスタ (Certification)
T54: コース必須講習 (CourseRequiredSeminar)
T55: 講習申込 (SeminarEnrollment)
T56: 検定申込 (CertificationEnrollment)
契約 (Contract)
T04: 生徒商品 (StudentItem)
"""
import uuid
from decimal import Decimal
from django.db import models
from apps.core.models import TenantModel


# =============================================================================
# T03: 商品マスタ (Product)
# =============================================================================
class Product(TenantModel):
    """T03: 商品マスタ

    通常授業・教材費・諸経費をすべてここに統合
    """

    class ItemType(models.TextChoices):
        # 基本料金
        TUITION = 'tuition', '授業料'
        MONTHLY_FEE = 'monthly_fee', '月会費'
        FACILITY = 'facility', '設備費'
        TEXTBOOK = 'textbook', '教材費'
        EXPENSE = 'expense', '諸経費'
        ENROLLMENT = 'enrollment', '入会金'
        # 入会時料金
        ENROLLMENT_TUITION = 'enrollment_tuition', '入会時授業料'
        ENROLLMENT_MONTHLY_FEE = 'enrollment_monthly_fee', '入会時月会費'
        ENROLLMENT_FACILITY = 'enrollment_facility', '入会時設備費'
        ENROLLMENT_TEXTBOOK = 'enrollment_textbook', '入会時教材費'
        ENROLLMENT_EXPENSE = 'enrollment_expense', '入会時諸経費'
        ENROLLMENT_MANAGEMENT = 'enrollment_management', '入会時総合指導管理費'
        # 講習・テスト
        SEMINAR = 'seminar', '講習会'
        SEMINAR_SPRING = 'seminar_spring', '春期講習会'
        SEMINAR_SUMMER = 'seminar_summer', '夏期講習会'
        SEMINAR_WINTER = 'seminar_winter', '冬期講習会'
        REQUIRED_SEMINAR = 'required_seminar', '必須講習会'
        REQUIRED_COURSE = 'required_course', '必須講座'
        TEST_PREP = 'test_prep', 'テスト対策費'
        REQUIRED_TEST_PREP = 'required_test_prep', '必須テスト対策費'
        MOCK_EXAM = 'mock_exam', '模試代'
        REQUIRED_MOCK_EXAM = 'required_mock_exam', '必須模試代'
        EXAM_PREP = 'exam_prep', '入試対策費'
        REQUIRED_EXAM_PREP = 'required_exam_prep', '必須入試対策費'
        # 検定
        CERTIFICATION_FEE_1 = 'certification_fee_1', '検定料1'
        CERTIFICATION_FEE_2 = 'certification_fee_2', '検定料2'
        CERTIFICATION_FEE_3 = 'certification_fee_3', '検定料3'
        CERTIFICATION_FEE_4 = 'certification_fee_4', '検定料4'
        # 追加授業
        EXTRA_TUITION = 'extra_tuition', '追加授業料'
        INSTRUCTOR_FEE = 'instructor_fee', '講師指名料'
        # 備品・グッズ
        BAG = 'bag', 'バッグ'
        ABACUS = 'abacus', 'そろばん本体代'
        # 保育・学童
        SNACK = 'snack', 'おやつ'
        LUNCH = 'lunch', 'お弁当'
        CHILDCARE_TICKET = 'childcare_ticket', '保育回数券'
        CUSTODY = 'custody', '預り料'
        TRANSPORTATION = 'transportation', '送迎費'
        # 管理費
        MANAGEMENT = 'management', '総合指導管理費'
        RENT = 'rent', '家賃'
        # その他
        OTHER = 'other', 'その他'

    class TaxType(models.TextChoices):
        TAX_1 = '1', '1:税込'
        TAX_2 = '2', '2:税抜'
        TAX_3 = '3', '3:非課税'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_code = models.CharField('商品コード', max_length=50)
    product_name = models.CharField('商品名', max_length=100)
    product_name_short = models.CharField('商品名略称', max_length=50, blank=True)

    # 商品種別
    item_type = models.CharField(
        '商品種別',
        max_length=30,
        choices=ItemType.choices,
        default=ItemType.TUITION
    )

    # 関連
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='products',
        verbose_name='ブランド'
    )
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='products',
        verbose_name='教室'
    )
    grade = models.ForeignKey(
        'schools.Grade',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='products',
        verbose_name='対象学年'
    )

    # 価格
    base_price = models.DecimalField('基本価格', max_digits=10, decimal_places=0, default=0)
    tax_rate = models.DecimalField('税率', max_digits=5, decimal_places=2, default=Decimal('0.10'))
    tax_type = models.CharField(
        '税区分',
        max_length=20,
        choices=TaxType.choices,
        default=TaxType.TAX_1
    )

    # 一回きり（入会金・教材等）
    is_one_time = models.BooleanField('一回きり', default=False)

    # 1年目無料（プログラミング教材費など）
    is_first_year_free = models.BooleanField(
        '1年目無料',
        default=False,
        help_text='チェックすると契約から12ヶ月間は無料、13ヶ月目から料金発生'
    )

    # 入会時授業料計算（月途中入会時の追加チケット計算用）
    is_enrollment_tuition = models.BooleanField(
        '入会時授業料',
        default=False,
        help_text='チェックすると入会日に基づいて追加チケット数を自動計算（フロント側）'
    )
    per_ticket_price = models.DecimalField(
        '1チケット単価',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        help_text='入会時授業料の場合、1チケットあたりの単価'
    )

    # マイル・割引
    mile = models.DecimalField('マイル', max_digits=10, decimal_places=0, default=0)
    discount_max = models.DecimalField('割引Max', max_digits=10, decimal_places=0, default=0)

    # その他
    description = models.TextField('説明', blank=True)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't03_products'
        verbose_name = 'T03_契約全部'
        verbose_name_plural = 'T03_契約全部'
        ordering = ['sort_order', 'product_code']
        unique_together = ['tenant_id', 'product_code']

    def __str__(self):
        return f"{self.product_name} ({self.product_code})"

    def get_price_for_enrollment_month(self, enrollment_month):
        """入会月に応じた料金を取得"""
        price_record = self.prices.filter(is_active=True).first()
        if price_record:
            return price_record.get_enrollment_price(enrollment_month)
        return self.base_price

    def get_price_for_billing_month(self, billing_month):
        """請求月に応じた料金を取得"""
        price_record = self.prices.filter(is_active=True).first()
        if price_record:
            return price_record.get_billing_price(billing_month)
        return self.base_price

    def calculate_enrollment_tuition(self, enrollment_date, lessons_per_week=1):
        """入会日に基づいて入会時授業料を計算

        月途中入会の場合、残り週数 × 週あたりレッスン数 × 単価 で計算

        Args:
            enrollment_date: 入会日（date）
            lessons_per_week: 週あたりのレッスン回数

        Returns:
            (追加チケット数, 金額) のタプル
        """
        import calendar
        from datetime import date

        if not self.is_enrollment_tuition or not self.per_ticket_price:
            return (0, Decimal('0'))

        # 入会日が月初なら追加チケットなし
        if enrollment_date.day == 1:
            return (0, Decimal('0'))

        # その月の残り週数を計算（簡易版：残り日数 / 7）
        _, days_in_month = calendar.monthrange(enrollment_date.year, enrollment_date.month)
        remaining_days = days_in_month - enrollment_date.day + 1
        remaining_weeks = max(0, (remaining_days + 6) // 7)  # 切り上げ

        # 追加チケット数を計算
        additional_tickets = remaining_weeks * lessons_per_week

        # 金額を計算
        amount = Decimal(additional_tickets) * self.per_ticket_price

        return (additional_tickets, amount)


# =============================================================================
# T05: 商品料金マスタ (ProductPrice) - 入会月別・請求月別料金
# =============================================================================
class ProductPrice(TenantModel):
    """T05: 商品料金マスタ

    入会月別・請求月別の料金を管理
    - 入会月別料金: 入会した月によって初回料金が変わる（教材費など）
    - 請求月別料金: 請求月によって料金が変わる（季節講習など）
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='prices',
        verbose_name='商品'
    )

    # 入会月別料金（T5, T5.1〜T5.11 = 1月〜12月入会者）
    enrollment_price_jan = models.DecimalField('1月入会者料金', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_feb = models.DecimalField('2月入会者料金', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_mar = models.DecimalField('3月入会者料金', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_apr = models.DecimalField('4月入会者料金', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_may = models.DecimalField('5月入会者料金', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_jun = models.DecimalField('6月入会者料金', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_jul = models.DecimalField('7月入会者料金', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_aug = models.DecimalField('8月入会者料金', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_sep = models.DecimalField('9月入会者料金', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_oct = models.DecimalField('10月入会者料金', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_nov = models.DecimalField('11月入会者料金', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_dec = models.DecimalField('12月入会者料金', max_digits=10, decimal_places=0, null=True, blank=True)

    # 請求月別料金（1月〜12月 = 各月の請求料金）
    billing_price_jan = models.DecimalField('1月請求料金', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_feb = models.DecimalField('2月請求料金', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_mar = models.DecimalField('3月請求料金', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_apr = models.DecimalField('4月請求料金', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_may = models.DecimalField('5月請求料金', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_jun = models.DecimalField('6月請求料金', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_jul = models.DecimalField('7月請求料金', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_aug = models.DecimalField('8月請求料金', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_sep = models.DecimalField('9月請求料金', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_oct = models.DecimalField('10月請求料金', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_nov = models.DecimalField('11月請求料金', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_dec = models.DecimalField('12月請求料金', max_digits=10, decimal_places=0, null=True, blank=True)

    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't05_product_prices'
        verbose_name = 'T05_商品料金'
        verbose_name_plural = 'T05_商品料金'
        unique_together = ['tenant_id', 'product']

    def __str__(self):
        return f"{self.product.product_name} 料金設定"

    def get_enrollment_price(self, month):
        """入会月に応じた料金を取得（1〜12月）"""
        month_map = {
            1: self.enrollment_price_jan,
            2: self.enrollment_price_feb,
            3: self.enrollment_price_mar,
            4: self.enrollment_price_apr,
            5: self.enrollment_price_may,
            6: self.enrollment_price_jun,
            7: self.enrollment_price_jul,
            8: self.enrollment_price_aug,
            9: self.enrollment_price_sep,
            10: self.enrollment_price_oct,
            11: self.enrollment_price_nov,
            12: self.enrollment_price_dec,
        }
        price = month_map.get(month)
        return price if price is not None else self.product.base_price

    def get_billing_price(self, month):
        """請求月に応じた料金を取得（1〜12月）"""
        month_map = {
            1: self.billing_price_jan,
            2: self.billing_price_feb,
            3: self.billing_price_mar,
            4: self.billing_price_apr,
            5: self.billing_price_may,
            6: self.billing_price_jun,
            7: self.billing_price_jul,
            8: self.billing_price_aug,
            9: self.billing_price_sep,
            10: self.billing_price_oct,
            11: self.billing_price_nov,
            12: self.billing_price_dec,
        }
        price = month_map.get(month)
        return price if price is not None else self.product.base_price


# =============================================================================
# T06: 商品セット (ProductSet) - 商品の組み合わせ定義
# =============================================================================
class ProductSet(TenantModel):
    """T06: 商品セット

    入会金＋教材費＋授業料などの商品組み合わせを定義
    コースやパックから参照して使用
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    set_code = models.CharField('セットコード', max_length=50)
    set_name = models.CharField('セット名', max_length=100)

    # 関連
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='product_sets',
        verbose_name='ブランド'
    )

    description = models.TextField('説明', blank=True)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't06_product_sets'
        verbose_name = 'T06_商品セット'
        verbose_name_plural = 'T06_商品セット'
        ordering = ['sort_order', 'set_code']
        unique_together = ['tenant_id', 'set_code']

    def __str__(self):
        return f"{self.set_name} ({self.set_code})"

    def get_total_price(self):
        """セット内商品の合計金額を取得"""
        total = Decimal('0')
        for item in self.items.filter(is_active=True):
            total += item.get_price()
        return total

    def get_items_display(self):
        """セット内商品の一覧を表示用に取得"""
        items = self.items.filter(is_active=True).select_related('product')
        return ' + '.join([item.product.product_name for item in items])


class ProductSetItem(TenantModel):
    """T06b: 商品セット明細"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    product_set = models.ForeignKey(
        ProductSet,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='商品セット'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='in_sets',
        verbose_name='商品'
    )

    quantity = models.IntegerField('数量', default=1)
    price_override = models.DecimalField(
        '価格上書き',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        help_text='設定した場合、商品の基本価格ではなくこの価格を使用'
    )

    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't06b_product_set_items'
        verbose_name = 'T06b_商品セット明細'
        verbose_name_plural = 'T06b_商品セット明細'
        ordering = ['product_set', 'sort_order']
        unique_together = ['product_set', 'product']

    def __str__(self):
        return f"{self.product_set.set_name} ← {self.product.product_name}"

    def get_price(self):
        """この商品の価格を取得"""
        if self.price_override is not None:
            return self.price_override * self.quantity
        return self.product.base_price * self.quantity


# =============================================================================
# T07: 割引マスタ (Discount)
# =============================================================================
class Discount(TenantModel):
    """T07: 割引マスタ"""

    class DiscountType(models.TextChoices):
        SIBLING = 'sibling', '兄弟割引'
        MULTI_SUBJECT = 'multi_subject', '複数科目割引'
        CAMPAIGN = 'campaign', 'キャンペーン'
        OTHER = 'other', 'その他'

    class CalculationType(models.TextChoices):
        PERCENTAGE = 'percentage', '割合'
        FIXED = 'fixed', '固定金額'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    discount_code = models.CharField('割引コード', max_length=20)
    discount_name = models.CharField('割引名', max_length=100)
    discount_type = models.CharField(
        '割引種別',
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.OTHER
    )
    calculation_type = models.CharField(
        '計算種別',
        max_length=20,
        choices=CalculationType.choices,
        default=CalculationType.PERCENTAGE
    )
    value = models.DecimalField('値', max_digits=10, decimal_places=2)

    valid_from = models.DateField('適用開始日', null=True, blank=True)
    valid_until = models.DateField('適用終了日', null=True, blank=True)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't07_discounts'
        verbose_name = 'T07_割引'
        verbose_name_plural = 'T07_割引'
        ordering = ['discount_code']
        unique_together = ['tenant_id', 'discount_code']

    def __str__(self):
        return f"{self.discount_name} ({self.discount_code})"


# =============================================================================
# T08: コース (Course)
# =============================================================================
class Course(TenantModel):
    """T08: コースマスタ"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course_code = models.CharField('コースコード', max_length=50)
    course_name = models.CharField('コース名', max_length=100)

    # 関連
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='courses',
        verbose_name='ブランド'
    )
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='courses',
        verbose_name='教室'
    )
    grade = models.ForeignKey(
        'schools.Grade',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='courses',
        verbose_name='対象学年'
    )

    # 商品セット（入会金＋教材費＋授業料などの組み合わせ）
    product_set = models.ForeignKey(
        ProductSet,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='courses',
        verbose_name='商品セット',
        help_text='入会金＋教材費＋授業料などの商品組み合わせ'
    )

    # コース料金（設定した場合はこちらを使用）
    course_price = models.DecimalField(
        '授業料',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        help_text='設定した場合、商品積み上げではなくこの料金を使用'
    )

    # 学年進級時の昇格先コース
    promotion_course = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promotion_from',
        verbose_name='昇格先コース',
        help_text='学年が上がった際に自動で昇格するコース（例：RYellow→Red）'
    )

    description = models.TextField('説明', blank=True)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't08_courses'
        verbose_name = 'T08_コース'
        verbose_name_plural = 'T08_コース'
        ordering = ['sort_order', 'course_code']
        unique_together = ['tenant_id', 'course_code']

    def __str__(self):
        return f"{self.course_name} ({self.course_code})"

    def get_product_set_display(self):
        """商品セットの内容を表示"""
        if self.product_set:
            return self.product_set.get_items_display()
        return ""

    def get_price(self):
        """コースの料金を取得"""
        if self.course_price is not None:
            return self.course_price
        # 商品積み上げ
        total = Decimal('0')
        for item in self.course_items.filter(is_active=True):
            total += item.get_price() * item.quantity
        return total


# =============================================================================
# T52: コース→商品紐づけ (CourseItem)
# =============================================================================
class CourseItem(TenantModel):
    """T52: コース商品構成"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='course_items',
        verbose_name='コース'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='in_courses',
        verbose_name='商品'
    )

    quantity = models.IntegerField('数量', default=1)
    price_override = models.DecimalField(
        '単価上書き',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True
    )

    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't52_course_items'
        verbose_name = 'T52_コース商品構成'
        verbose_name_plural = 'T52_コース商品構成'
        ordering = ['course', 'sort_order']
        unique_together = ['course', 'product']

    def __str__(self):
        return f"{self.course.course_name} ← {self.product.product_name}"

    def get_price(self):
        if self.price_override is not None:
            return self.price_override
        return self.product.base_price


# =============================================================================
# T11: 講習マスタ (Seminar)
# =============================================================================
class Seminar(TenantModel):
    """T11: 講習マスタ（買い切り）"""

    class SeminarType(models.TextChoices):
        SPRING = 'spring', '春期講習'
        SUMMER = 'summer', '夏期講習'
        AUTUMN = 'autumn', '秋期講習'
        WINTER = 'winter', '冬期講習'
        SPECIAL = 'special', '特別講習'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seminar_code = models.CharField('講習コード', max_length=50)
    seminar_name = models.CharField('講習名', max_length=200)

    seminar_type = models.CharField(
        '講習種別',
        max_length=20,
        choices=SeminarType.choices,
        default=SeminarType.OTHER
    )

    # 関連
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='seminars',
        verbose_name='ブランド'
    )
    grade = models.ForeignKey(
        'schools.Grade',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='seminars',
        verbose_name='対象学年'
    )

    # 期間
    year = models.IntegerField('年度')
    start_date = models.DateField('開始日', null=True, blank=True)
    end_date = models.DateField('終了日', null=True, blank=True)

    # 価格
    base_price = models.DecimalField('価格', max_digits=10, decimal_places=0, default=0)

    description = models.TextField('説明', blank=True)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't11_seminars'
        verbose_name = 'T11_講習'
        verbose_name_plural = 'T11_講習'
        ordering = ['year', 'seminar_type', 'sort_order']
        unique_together = ['tenant_id', 'seminar_code']

    def __str__(self):
        return f"{self.seminar_name} ({self.year})"


# =============================================================================
# T12: 検定マスタ (Certification)
# =============================================================================
class Certification(TenantModel):
    """T12: 検定マスタ（買い切り）"""

    class CertificationType(models.TextChoices):
        EIKEN = 'eiken', '英検'
        KANKEN = 'kanken', '漢検'
        SUKEN = 'suken', '数検'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    certification_code = models.CharField('検定コード', max_length=50)
    certification_name = models.CharField('検定名', max_length=200)

    certification_type = models.CharField(
        '検定種別',
        max_length=20,
        choices=CertificationType.choices,
        default=CertificationType.OTHER
    )

    level = models.CharField('級・レベル', max_length=50, blank=True)

    # 関連
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='certifications',
        verbose_name='ブランド'
    )

    # 試験日
    year = models.IntegerField('年度')
    exam_date = models.DateField('試験日', null=True, blank=True)

    # 価格
    exam_fee = models.DecimalField('検定料', max_digits=10, decimal_places=0, default=0)

    description = models.TextField('説明', blank=True)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't12_certifications'
        verbose_name = 'T12_検定'
        verbose_name_plural = 'T12_検定'
        ordering = ['year', 'certification_type']
        unique_together = ['tenant_id', 'certification_code']

    def __str__(self):
        return f"{self.certification_name} {self.level} ({self.year})"


# =============================================================================
# T07: チケット (Ticket)
# =============================================================================
class Ticket(TenantModel):
    """T07: チケットマスタ

    チケット情報を管理（T7_チケット情報.csvに対応）
    チケットID（Ch10000001等）でコースと紐づく
    """

    class TicketType(models.TextChoices):
        LESSON = '1', '1：授業'
        SEMINAR = '5', '5：講習会'
        MOCK_EXAM = '6', '6：模試'
        TEST_PREP = '7', '7:テスト対策'
        HOME_STUDY = '8', '8：自宅受講'
        OTHER = '0', 'その他'

    class TicketCategory(models.TextChoices):
        REGULAR = '1', '通常'
        MAKEUP = '2', '振替'
        CARRYOVER = '3', '年マタギ'
        OTHER = '0', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_code = models.CharField(
        'チケットコード',
        max_length=20,
        help_text='T10000001形式（Tプレフィックス）'
    )
    ticket_name = models.CharField('チケット名', max_length=200)

    # チケット種類
    ticket_type = models.CharField(
        'チケット種類',
        max_length=10,
        choices=TicketType.choices,
        default=TicketType.LESSON
    )
    ticket_category = models.CharField(
        'チケット区別',
        max_length=10,
        choices=TicketCategory.choices,
        default=TicketCategory.REGULAR
    )

    # 振替関連
    transfer_day = models.IntegerField(
        '振替曜日',
        null=True, blank=True,
        help_text='0=日, 1=月, 2=火, 3=水, 4=木, 5=金, 6=土'
    )
    transfer_group = models.CharField('振替Group', max_length=50, blank=True)
    consumption_symbol = models.CharField('消化記号', max_length=10, blank=True)

    # 年間/週と枚数
    annual_weekly = models.IntegerField(
        '年間/週',
        default=42,
        help_text='年間授業回数'
    )
    max_per_lesson = models.IntegerField(
        'Max値',
        default=1,
        help_text='1回あたりの消費チケット数'
    )
    total_tickets = models.IntegerField(
        'チケット枚数',
        default=42,
        help_text='年間合計チケット数'
    )

    # フラグ
    calendar_flag = models.IntegerField('カレンダーフラグ', default=2)
    year_carryover = models.BooleanField(
        '年マタギ利用',
        default=False,
        help_text='年度をまたいで利用可能か'
    )
    expiry_date = models.DateField('有効期限', null=True, blank=True)

    # 関連
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tickets',
        verbose_name='ブランド'
    )

    description = models.TextField('説明', blank=True)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't07_tickets'
        verbose_name = 'T07_チケット'
        verbose_name_plural = 'T07_チケット'
        ordering = ['ticket_code']
        unique_together = ['tenant_id', 'ticket_code']

    def __str__(self):
        return f"{self.ticket_name} ({self.ticket_code})"


# =============================================================================
# T08b: コース→チケット紐づけ (CourseTicket)
# =============================================================================
class CourseTicket(TenantModel):
    """T08b: コースチケット構成

    コースに紐づくチケットを定義
    T8_契約とチケット情報.xlsxに対応
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    course = models.ForeignKey(
        'Course',
        on_delete=models.CASCADE,
        related_name='course_tickets',
        verbose_name='コース'
    )
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='in_courses',
        verbose_name='チケット'
    )

    # チケット付与数
    quantity = models.IntegerField(
        '付与枚数',
        default=1,
        help_text='年間付与されるチケット枚数'
    )
    per_week = models.IntegerField(
        '週あたり',
        default=1,
        help_text='週あたりの授業回数'
    )

    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't08b_course_tickets'
        verbose_name = 'T08b_コースチケット'
        verbose_name_plural = 'T08b_コースチケット'
        ordering = ['course', 'sort_order']
        unique_together = ['course', 'ticket']

    def __str__(self):
        return f"{self.course.course_name} ← {self.ticket.ticket_name}"


# =============================================================================
# T09b: パック→チケット紐づけ (PackTicket)
# =============================================================================
class PackTicket(TenantModel):
    """T09b: パックチケット構成

    パックに直接紐づくチケットを定義
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    pack = models.ForeignKey(
        'Pack',
        on_delete=models.CASCADE,
        related_name='pack_tickets',
        verbose_name='パック'
    )
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='in_packs',
        verbose_name='チケット'
    )

    quantity = models.IntegerField('付与枚数', default=1)
    per_week = models.IntegerField('週あたり', default=1)

    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't09b_pack_tickets'
        verbose_name = 'T09b_パックチケット'
        verbose_name_plural = 'T09b_パックチケット'
        ordering = ['pack', 'sort_order']
        unique_together = ['pack', 'ticket']

    def __str__(self):
        return f"{self.pack.pack_name} ← {self.ticket.ticket_name}"


# =============================================================================
# T09: パック (Pack) - 複数コースのセット
# =============================================================================
class Pack(TenantModel):
    """T09: パックマスタ

    複数のコースをまとめたセット商品
    例：アンイングリッシュクラブ + そろばんコース
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pack_code = models.CharField('パックコード', max_length=50)
    pack_name = models.CharField('パック名', max_length=100)

    # 関連
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='packs',
        verbose_name='ブランド'
    )
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='packs',
        verbose_name='校舎'
    )
    grade = models.ForeignKey(
        'schools.Grade',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='packs',
        verbose_name='対象学年'
    )

    # 商品セット（入会金＋教材費＋授業料などの組み合わせ）
    product_set = models.ForeignKey(
        ProductSet,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='packs',
        verbose_name='商品セット',
        help_text='入会金＋教材費＋授業料などの商品組み合わせ'
    )

    # パック料金（設定した場合、各コースの合計ではなくこちらを使用）
    pack_price = models.DecimalField(
        '授業料',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        help_text='設定した場合、コース積み上げではなくこの料金を使用'
    )

    # 割引設定
    discount_type = models.CharField(
        '割引種別',
        max_length=20,
        choices=[
            ('none', '割引なし'),
            ('percentage', '割合割引'),
            ('fixed', '固定割引'),
        ],
        default='none'
    )
    discount_value = models.DecimalField(
        '割引値',
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='割合の場合は%、固定の場合は円'
    )

    description = models.TextField('説明', blank=True)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't09_packs'
        verbose_name = 'T09_パック'
        verbose_name_plural = 'T09_パック'
        ordering = ['sort_order', 'pack_code']
        unique_together = ['tenant_id', 'pack_code']

    def __str__(self):
        return f"{self.pack_name} ({self.pack_code})"

    def get_price(self):
        """パックの料金を取得"""
        if self.pack_price is not None:
            return self.pack_price

        # コース積み上げ
        total = Decimal('0')
        for item in self.pack_courses.filter(is_active=True):
            total += item.course.get_price()

        # 割引適用
        if self.discount_type == 'percentage':
            total = total * (1 - self.discount_value / 100)
        elif self.discount_type == 'fixed':
            total = total - self.discount_value

        return max(total, Decimal('0'))


# =============================================================================
# T53: パック→コース紐づけ (PackCourse)
# =============================================================================
class PackCourse(TenantModel):
    """T53: パックコース構成"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    pack = models.ForeignKey(
        Pack,
        on_delete=models.CASCADE,
        related_name='pack_courses',
        verbose_name='パック'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='in_packs',
        verbose_name='コース'
    )

    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't53_pack_courses'
        verbose_name = 'T53_パックコース構成'
        verbose_name_plural = 'T53_パックコース構成'
        ordering = ['pack', 'sort_order']
        unique_together = ['pack', 'course']

    def __str__(self):
        return f"{self.pack.pack_name} ← {self.course.course_name}"


# =============================================================================
# T52: パック→商品紐づけ (PackItem) - パック独自の商品構成
# =============================================================================
class PackItem(TenantModel):
    """T52: パック商品構成

    パックに直接紐づく商品（D列=4の商品）
    コースの商品構成（CourseItem）と同様の構造
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    pack = models.ForeignKey(
        Pack,
        on_delete=models.CASCADE,
        related_name='pack_items',
        verbose_name='パック'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='in_packs',
        verbose_name='商品'
    )

    quantity = models.IntegerField('数量', default=1)
    price_override = models.DecimalField(
        '価格上書き',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        help_text='設定した場合、商品の基本価格ではなくこの価格を使用'
    )

    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't52_pack_items'
        verbose_name = 'T52_パック商品構成'
        verbose_name_plural = 'T52_パック商品構成'
        ordering = ['pack', 'sort_order']
        unique_together = ['pack', 'product']

    def __str__(self):
        return f"{self.pack.pack_name} ← {self.product.product_name}"

    def get_price(self):
        """この商品の価格を取得"""
        if self.price_override is not None:
            return self.price_override
        return self.product.base_price * self.quantity


# =============================================================================
# T54: コース必須講習 (CourseRequiredSeminar)
# =============================================================================
class CourseRequiredSeminar(TenantModel):
    """T54: コース必須講習"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='required_seminars',
        verbose_name='コース'
    )
    seminar = models.ForeignKey(
        Seminar,
        on_delete=models.CASCADE,
        related_name='required_by_courses',
        verbose_name='必須講習'
    )

    auto_enroll = models.BooleanField('自動申込', default=True)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't54_course_required_seminars'
        verbose_name = 'T54_コース必須講習'
        verbose_name_plural = 'T54_コース必須講習'
        unique_together = ['course', 'seminar']

    def __str__(self):
        return f"{self.course.course_name} → {self.seminar.seminar_name}"


# =============================================================================
# 契約 (Contract)
# =============================================================================
class Contract(TenantModel):
    """契約"""

    class Status(models.TextChoices):
        ACTIVE = 'active', '有効'
        PAUSED = 'paused', '休止中'
        CANCELLED = 'cancelled', '解約'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract_no = models.CharField('契約番号', max_length=30)

    # 契約者
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        related_name='contracts',
        verbose_name='生徒'
    )
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='contracts',
        verbose_name='契約保護者'
    )

    # 所属
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.PROTECT,
        related_name='contracts',
        verbose_name='校舎'
    )
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.PROTECT,
        related_name='contracts',
        verbose_name='ブランド'
    )

    # 契約コース
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='contracts',
        verbose_name='コース'
    )

    # 期間
    contract_date = models.DateField('契約日')
    start_date = models.DateField('開始日')
    end_date = models.DateField('終了日', null=True, blank=True)

    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    # 金額
    monthly_total = models.DecimalField('月額合計', max_digits=10, decimal_places=0, default=0)

    # 授業スケジュール
    day_of_week = models.IntegerField(
        '曜日',
        null=True,
        blank=True,
        help_text='0=日, 1=月, 2=火, 3=水, 4=木, 5=金, 6=土'
    )
    start_time = models.TimeField('開始時間', null=True, blank=True)
    end_time = models.TimeField('終了時間', null=True, blank=True)

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't03_contracts'
        verbose_name = '契約'
        verbose_name_plural = '契約'
        ordering = ['-contract_date']
        unique_together = ['tenant_id', 'contract_no']

    def __str__(self):
        return f"{self.contract_no} - {self.student}"


# =============================================================================
# T04: 生徒商品 (StudentItem) - 請求データ
# =============================================================================
class StudentItem(TenantModel):
    """T04: 生徒商品（請求対象）"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        related_name='student_items',
        verbose_name='生徒'
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='student_items',
        verbose_name='契約'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='student_items',
        verbose_name='商品'
    )

    # 購入時の情報（チケット購入時に選択した内容を直接保存）
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='student_items',
        verbose_name='ブランド'
    )
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='student_items',
        verbose_name='校舎'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='student_items',
        verbose_name='コース'
    )
    start_date = models.DateField('開始日', null=True, blank=True)

    # 請求情報
    billing_month = models.CharField('請求月', max_length=7, help_text='例: 2025-04')
    quantity = models.IntegerField('数量', default=1)
    unit_price = models.DecimalField('単価', max_digits=10, decimal_places=0)
    discount_amount = models.DecimalField('割引額', max_digits=10, decimal_places=0, default=0)
    final_price = models.DecimalField('確定金額', max_digits=10, decimal_places=0)

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't04_student_items'
        verbose_name = 'T04_生徒商品'
        verbose_name_plural = 'T04_生徒商品'
        ordering = ['-billing_month', 'student']

    def __str__(self):
        return f"{self.student} - {self.product} ({self.billing_month})"


# =============================================================================
# T55: 講習申込 (SeminarEnrollment)
# =============================================================================
class SeminarEnrollment(TenantModel):
    """T55: 講習申込"""

    class Status(models.TextChoices):
        APPLIED = 'applied', '申込済'
        CONFIRMED = 'confirmed', '確定'
        CANCELLED = 'cancelled', 'キャンセル'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        related_name='seminar_enrollments',
        verbose_name='生徒'
    )
    seminar = models.ForeignKey(
        Seminar,
        on_delete=models.PROTECT,
        related_name='enrollments',
        verbose_name='講習'
    )

    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.APPLIED
    )
    applied_at = models.DateTimeField('申込日時', auto_now_add=True)

    unit_price = models.DecimalField('単価', max_digits=10, decimal_places=0)
    discount_amount = models.DecimalField('割引額', max_digits=10, decimal_places=0, default=0)
    final_price = models.DecimalField('確定金額', max_digits=10, decimal_places=0)

    is_required = models.BooleanField('必須講習', default=False)
    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't55_seminar_enrollments'
        verbose_name = 'T55_講習申込'
        verbose_name_plural = 'T55_講習申込'
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.student} - {self.seminar}"


# =============================================================================
# T56: 検定申込 (CertificationEnrollment)
# =============================================================================
class CertificationEnrollment(TenantModel):
    """T56: 検定申込"""

    class Status(models.TextChoices):
        APPLIED = 'applied', '申込済'
        CONFIRMED = 'confirmed', '確定'
        CANCELLED = 'cancelled', 'キャンセル'
        PASSED = 'passed', '合格'
        FAILED = 'failed', '不合格'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        related_name='certification_enrollments',
        verbose_name='生徒'
    )
    certification = models.ForeignKey(
        Certification,
        on_delete=models.PROTECT,
        related_name='enrollments',
        verbose_name='検定'
    )

    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.APPLIED
    )
    applied_at = models.DateTimeField('申込日時', auto_now_add=True)

    exam_fee = models.DecimalField('検定料', max_digits=10, decimal_places=0)
    discount_amount = models.DecimalField('割引額', max_digits=10, decimal_places=0, default=0)
    final_price = models.DecimalField('確定金額', max_digits=10, decimal_places=0)

    score = models.IntegerField('スコア', null=True, blank=True)
    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't56_certification_enrollments'
        verbose_name = 'T56_検定申込'
        verbose_name_plural = 'T56_検定申込'
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.student} - {self.certification}"


# =============================================================================
# 契約変更申請 (ContractChangeRequest)
# =============================================================================
class ContractChangeRequest(TenantModel):
    """契約変更申請

    休会申請・退会申請を保護者が行うためのモデル
    """

    class RequestType(models.TextChoices):
        CLASS_CHANGE = 'class_change', 'クラス変更'
        SCHOOL_CHANGE = 'school_change', '校舎変更'
        SUSPENSION = 'suspension', '休会申請'
        CANCELLATION = 'cancellation', '退会申請'

    class Status(models.TextChoices):
        PENDING = 'pending', '申請中'
        APPROVED = 'approved', '承認済'
        REJECTED = 'rejected', '却下'
        CANCELLED = 'cancelled', '取消'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='change_requests',
        verbose_name='契約'
    )

    request_type = models.CharField(
        '申請種別',
        max_length=20,
        choices=RequestType.choices
    )

    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # クラス/校舎変更用
    new_school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='change_requests',
        verbose_name='新校舎'
    )
    new_day_of_week = models.IntegerField('新曜日', null=True, blank=True)
    new_start_time = models.TimeField('新開始時間', null=True, blank=True)
    new_class_schedule = models.ForeignKey(
        'schools.ClassSchedule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='change_requests',
        verbose_name='新クラススケジュール'
    )
    effective_date = models.DateField('適用日', null=True, blank=True)

    # 休会用
    suspend_from = models.DateField('休会開始日', null=True, blank=True)
    suspend_until = models.DateField('休会終了日', null=True, blank=True)
    keep_seat = models.BooleanField('座席保持', default=False)

    # 退会用
    cancel_date = models.DateField('退会日', null=True, blank=True)
    refund_amount = models.DecimalField(
        '相殺金額',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True
    )

    reason = models.TextField('理由', blank=True)

    # 申請者情報
    requested_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='contract_change_requests',
        verbose_name='申請者'
    )
    requested_at = models.DateTimeField('申請日時', auto_now_add=True)

    # 処理者情報
    processed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_contract_requests',
        verbose_name='処理者'
    )
    processed_at = models.DateTimeField('処理日時', null=True, blank=True)
    process_notes = models.TextField('処理メモ', blank=True)

    class Meta:
        db_table = 'contract_change_requests'
        verbose_name = '契約変更申請'
        verbose_name_plural = '契約変更申請'
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.contract} - {self.get_request_type_display()} ({self.get_status_display()})"
