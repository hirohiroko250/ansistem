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
    product_code = models.CharField('請求ID', max_length=50)
    product_name = models.CharField('明細表記', max_length=100)
    product_name_short = models.CharField('契約名', max_length=50, blank=True)

    # 商品種別
    item_type = models.CharField(
        '請求カテゴリ',
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
        verbose_name='契約ブランド名'
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
    base_price = models.DecimalField('保護者表示用金額', max_digits=10, decimal_places=0, default=0)
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

    # 初年度無料（年度ベース：4月〜翌3月）
    is_first_fiscal_year_free = models.BooleanField(
        '初年度無料',
        default=False,
        help_text='チェックすると入会年度末（3月）まで無料、翌年度4月から料金発生'
    )

    # 入会時授業料計算（月途中入会時の追加チケット計算用）
    is_enrollment_tuition = models.BooleanField(
        '入会時授業料',
        default=False,
        help_text='チェックすると入会日に基づいて追加チケット数を自動計算（フロント側）'
    )
    per_ticket_price = models.DecimalField(
        '単価',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        help_text='入会時授業料の場合、1チケットあたりの単価'
    )

    # マイル・割引
    mile = models.DecimalField('マイル', max_digits=10, decimal_places=0, default=0)
    discount_max = models.DecimalField('割引Max', max_digits=10, decimal_places=0, default=0)

    # 初月料金（入会月別）- 1月〜12月入会者
    enrollment_price_jan = models.DecimalField('1月入会者', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_feb = models.DecimalField('2月入会者', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_mar = models.DecimalField('3月入会者', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_apr = models.DecimalField('4月入会者', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_may = models.DecimalField('5月入会者', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_jun = models.DecimalField('6月入会者', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_jul = models.DecimalField('7月入会者', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_aug = models.DecimalField('8月入会者', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_sep = models.DecimalField('9月入会者', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_oct = models.DecimalField('10月入会者', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_nov = models.DecimalField('11月入会者', max_digits=10, decimal_places=0, null=True, blank=True)
    enrollment_price_dec = models.DecimalField('12月入会者', max_digits=10, decimal_places=0, null=True, blank=True)

    # 2ヶ月目以降料金（請求月別）- 1月〜12月
    billing_price_jan = models.DecimalField('1月', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_feb = models.DecimalField('2月', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_mar = models.DecimalField('3月', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_apr = models.DecimalField('4月', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_may = models.DecimalField('5月', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_jun = models.DecimalField('6月', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_jul = models.DecimalField('7月', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_aug = models.DecimalField('8月', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_sep = models.DecimalField('9月', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_oct = models.DecimalField('10月', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_nov = models.DecimalField('11月', max_digits=10, decimal_places=0, null=True, blank=True)
    billing_price_dec = models.DecimalField('12月', max_digits=10, decimal_places=0, null=True, blank=True)

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
        MILE = 'mile', 'マイル割引'
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
    is_visible = models.BooleanField(
        '保護者に表示',
        default=True,
        help_text='チェックを外すと保護者アプリに表示されません'
    )
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't08_courses'
        verbose_name = 'T08_金魚の糞付き'
        verbose_name_plural = 'T08_金魚の糞付き'
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
# T10: 追加チケット (AdditionalTicket) - 入会月用チケット
# =============================================================================
class AdditionalTicket(TenantModel):
    """T10: 当月分商品（追加チケット含む）

    月途中入会時の当月分商品を管理。
    授業チケットだけでなく、月会費・設備費なども回数割で計算。
    コースごとに管理し、対象日を明確に記録。
    """

    class Status(models.TextChoices):
        PENDING = 'pending', '購入待ち'
        PURCHASED = 'purchased', '購入済み'
        PARTIALLY_USED = 'partially_used', '一部使用'
        FULLY_USED = 'fully_used', '使用完了'
        EXPIRED = 'expired', '期限切れ'
        CANCELLED = 'cancelled', 'キャンセル'

    class ItemType(models.TextChoices):
        TICKET = 'ticket', '授業チケット'
        MONTHLY_FEE = 'monthly_fee', '当月分月会費'
        FACILITY = 'facility', '当月分設備費'
        TEXTBOOK = 'textbook', '当月分教材費'
        MANAGEMENT = 'management', '当月分総合指導管理費'
        EXPENSE = 'expense', '当月分諸経費'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 種別
    item_type = models.CharField(
        '種別',
        max_length=20,
        choices=ItemType.choices,
        default=ItemType.TICKET
    )

    # 対象生徒・コース
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='additional_tickets',
        verbose_name='生徒'
    )
    course = models.ForeignKey(
        'Course',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='additional_tickets',
        verbose_name='コース'
    )
    class_schedule = models.ForeignKey(
        'schools.ClassSchedule',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='additional_tickets',
        verbose_name='クラススケジュール'
    )

    # 購入情報
    purchase_date = models.DateField('購入日', null=True, blank=True)
    quantity = models.IntegerField('購入枚数', default=0)
    unit_price = models.DecimalField('単価', max_digits=10, decimal_places=0, default=0)
    total_price = models.DecimalField('合計金額', max_digits=10, decimal_places=0, default=0)

    # 消費状況
    used_count = models.IntegerField('使用済み数', default=0)

    @property
    def remaining(self):
        """残枚数"""
        return max(0, self.quantity - self.used_count)

    # 有効期限（入会月末）
    valid_until = models.DateField('有効期限', null=True, blank=True)

    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # 関連する契約・請求
    student_item = models.ForeignKey(
        'StudentItem',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='additional_tickets',
        verbose_name='生徒商品'
    )

    notes = models.TextField('備考', blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        db_table = 't10a_additional_tickets'
        verbose_name = 'T10a_追加チケット'
        verbose_name_plural = 'T10a_追加チケット'
        ordering = ['-purchase_date', 'student']

    def __str__(self):
        return f"{self.student} - {self.course} ({self.quantity}枚)"

    def use_ticket(self, count=1):
        """チケットを使用"""
        if self.remaining < count:
            raise ValueError('残チケットが不足しています')
        self.used_count += count
        if self.remaining == 0:
            self.status = self.Status.FULLY_USED
        else:
            self.status = self.Status.PARTIALLY_USED
        self.save()

    def check_expiry(self):
        """有効期限をチェック"""
        from django.utils import timezone
        if self.valid_until and timezone.now().date() > self.valid_until:
            if self.status not in [self.Status.FULLY_USED, self.Status.CANCELLED]:
                self.status = self.Status.EXPIRED
                self.save()
                return True
        return False


# =============================================================================
# T10b: 追加チケット対象日 (AdditionalTicketDate) - チケットの対象日
# =============================================================================
class AdditionalTicketDate(TenantModel):
    """T10b: 追加チケット対象日

    追加チケットの対象日を個別に管理。
    消費追跡・出席との紐づけに使用。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    additional_ticket = models.ForeignKey(
        AdditionalTicket,
        on_delete=models.CASCADE,
        related_name='target_dates',
        verbose_name='追加チケット'
    )
    target_date = models.DateField('対象日')

    # 消費状況
    is_used = models.BooleanField('使用済み', default=False)
    used_at = models.DateTimeField('使用日時', null=True, blank=True)

    # 出席との紐づけ
    attendance = models.ForeignKey(
        'lessons.Attendance',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='additional_ticket_dates',
        verbose_name='出席'
    )

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't10b_additional_ticket_dates'
        verbose_name = 'T10b_追加チケット対象日'
        verbose_name_plural = 'T10b_追加チケット対象日'
        ordering = ['target_date']
        unique_together = ['additional_ticket', 'target_date']

    def __str__(self):
        status = '済' if self.is_used else '未'
        return f"{self.target_date} ({status})"

    def mark_as_used(self, attendance=None):
        """使用済みにする"""
        from django.utils import timezone
        self.is_used = True
        self.used_at = timezone.now()
        if attendance:
            self.attendance = attendance
        self.save()
        # 親チケットの使用数を更新
        self.additional_ticket.use_ticket(1)


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
    old_id = models.CharField('旧システムID', max_length=50, blank=True, db_index=True)

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

    # 選択した教材（教材費の支払い方法選択用）
    selected_textbooks = models.ManyToManyField(
        'Product',
        blank=True,
        related_name='selected_in_contracts',
        verbose_name='選択教材',
        help_text='この契約で選択した教材費（月払い or 半年払い等）'
    )

    # 金額
    monthly_total = models.DecimalField('月額合計', max_digits=10, decimal_places=0, default=0)

    # マイル・割引関連
    mile_earn_monthly = models.IntegerField(
        '月間獲得マイル',
        default=0,
        help_text='この契約で毎月獲得するマイル数'
    )
    discount_applied = models.DecimalField(
        '適用割引額',
        max_digits=10,
        decimal_places=0,
        default=0,
        help_text='兄弟割引など適用されている割引額'
    )
    discount_type = models.CharField(
        '割引種別',
        max_length=50,
        blank=True,
        help_text='兄弟割引、キャンペーン等'
    )
    mile_discount_applied = models.DecimalField(
        'マイル割引額',
        max_digits=10,
        decimal_places=0,
        default=0,
        help_text='マイル使用による割引額'
    )
    mile_used = models.IntegerField(
        '使用マイル',
        default=0,
        help_text='この契約で使用したマイル数'
    )

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
    old_id = models.CharField('旧システムID', max_length=50, blank=True, db_index=True)

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
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
        null=True,
        blank=True,
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

    # 授業スケジュール
    day_of_week = models.IntegerField(
        '曜日',
        null=True,
        blank=True,
        help_text='1=月, 2=火, 3=水, 4=木, 5=金, 6=土, 7=日'
    )
    start_time = models.TimeField('開始時間', null=True, blank=True)
    end_time = models.TimeField('終了時間', null=True, blank=True)
    class_schedule = models.ForeignKey(
        'schools.ClassSchedule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_items',
        verbose_name='受講クラス',
        help_text='チケット購入時に選択したクラス'
    )

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
# T06: 生徒割引 (StudentDiscount) - 生徒に適用される割引
# =============================================================================
class StudentDiscount(TenantModel):
    """T06: 生徒割引（生徒に適用される割引明細）"""

    class DiscountUnit(models.TextChoices):
        YEN = 'yen', '円'
        PERCENT = 'percent', '%'

    class EndCondition(models.TextChoices):
        ONCE = 'once', '１回だけ'
        MONTHLY = 'monthly', '毎月'
        UNTIL_END_DATE = 'until_end_date', '終了日まで'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    old_id = models.CharField('旧システムID', max_length=50, blank=True, db_index=True)

    # 対象
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='student_discounts',
        verbose_name='生徒'
    )
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='student_discounts',
        verbose_name='保護者'
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='student_discounts',
        verbose_name='契約'
    )
    student_item = models.ForeignKey(
        StudentItem,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='student_discounts',
        verbose_name='請求項目'
    )
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='student_discounts',
        verbose_name='ブランド'
    )

    # 割引情報
    discount_name = models.CharField('割引名', max_length=200)
    amount = models.DecimalField('金額', max_digits=10, decimal_places=0, help_text='マイナス値で割引')
    discount_unit = models.CharField(
        '割引単位',
        max_length=10,
        choices=DiscountUnit.choices,
        default=DiscountUnit.YEN
    )

    # 適用期間
    start_date = models.DateField('開始日', null=True, blank=True)
    end_date = models.DateField('終了日', null=True, blank=True)

    # 繰り返し・自動適用
    is_recurring = models.BooleanField('繰り返し', default=False)
    is_auto = models.BooleanField('自動割引', default=False)
    end_condition = models.CharField(
        '終了条件',
        max_length=20,
        choices=EndCondition.choices,
        default=EndCondition.ONCE
    )

    # その他
    is_active = models.BooleanField('有効', default=True)
    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't06_student_discounts'
        verbose_name = 'T06_生徒割引'
        verbose_name_plural = 'T06_生徒割引'
        ordering = ['-start_date', 'student']

    def __str__(self):
        target = self.student or self.guardian
        return f"{target} - {self.discount_name} ({self.amount})"


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


# =============================================================================
# 契約履歴 (ContractHistory) - 契約変更履歴を記録
# =============================================================================
class ContractHistory(TenantModel):
    """契約履歴

    契約の変更（作成、更新、キャンセル等）を全て記録する。
    """

    class ActionType(models.TextChoices):
        CREATED = 'created', '新規作成'
        UPDATED = 'updated', '更新'
        CANCELLED = 'cancelled', '解約'
        PAUSED = 'paused', '休会'
        RESUMED = 'resumed', '再開'
        COURSE_CHANGED = 'course_changed', 'コース変更'
        SCHEDULE_CHANGED = 'schedule_changed', 'スケジュール変更'
        SCHOOL_CHANGED = 'school_changed', '校舎変更'
        PRICE_CHANGED = 'price_changed', '料金変更'
        DISCOUNT_APPLIED = 'discount_applied', '割引適用'
        MILE_APPLIED = 'mile_applied', 'マイル適用'
        PROMOTION = 'promotion', '進級'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='histories',
        verbose_name='契約'
    )

    # 変更種別
    action_type = models.CharField(
        '変更種別',
        max_length=30,
        choices=ActionType.choices
    )

    # 変更前後のデータ（JSON形式）
    before_data = models.JSONField(
        '変更前データ',
        null=True,
        blank=True,
        help_text='変更前の契約情報をJSON形式で保存'
    )
    after_data = models.JSONField(
        '変更後データ',
        null=True,
        blank=True,
        help_text='変更後の契約情報をJSON形式で保存'
    )

    # 変更内容の説明
    change_summary = models.CharField('変更概要', max_length=500)
    change_detail = models.TextField('変更詳細', blank=True)

    # 金額関連
    amount_before = models.DecimalField(
        '変更前金額',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True
    )
    amount_after = models.DecimalField(
        '変更後金額',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True
    )
    discount_amount = models.DecimalField(
        '割引額',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True
    )
    mile_used = models.IntegerField('使用マイル', null=True, blank=True)
    mile_discount = models.DecimalField(
        'マイル割引額',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True
    )

    # 適用日
    effective_date = models.DateField('適用日', null=True, blank=True)

    # 変更者
    changed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contract_histories',
        verbose_name='変更者'
    )
    changed_by_name = models.CharField('変更者名', max_length=100, blank=True)

    # システム変更フラグ
    is_system_change = models.BooleanField(
        'システム変更',
        default=False,
        help_text='自動処理による変更の場合True'
    )

    # IPアドレス（監査用）
    ip_address = models.GenericIPAddressField('IPアドレス', null=True, blank=True)

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 'contract_histories'
        verbose_name = '契約履歴'
        verbose_name_plural = '契約履歴'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['contract', '-created_at']),
            models.Index(fields=['action_type']),
        ]

    def __str__(self):
        return f"{self.contract.contract_no} - {self.get_action_type_display()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    @classmethod
    def log_change(cls, contract, action_type, change_summary,
                   before_data=None, after_data=None, user=None,
                   is_system=False, **kwargs):
        """契約変更をログに記録するヘルパーメソッド"""
        return cls.objects.create(
            tenant_id=contract.tenant_id,
            contract=contract,
            action_type=action_type,
            change_summary=change_summary,
            before_data=before_data,
            after_data=after_data,
            changed_by=user,
            changed_by_name=user.get_full_name() if user else 'システム',
            is_system_change=is_system,
            **kwargs
        )


# =============================================================================
# システム監査ログ (SystemAuditLog) - 全システム操作を記録
# =============================================================================
class SystemAuditLog(TenantModel):
    """システム監査ログ

    システム全体の操作履歴を記録する。
    契約だけでなく、生徒、保護者、請求など全てのエンティティの変更を追跡。
    """

    class EntityType(models.TextChoices):
        STUDENT = 'student', '生徒'
        GUARDIAN = 'guardian', '保護者'
        CONTRACT = 'contract', '契約'
        STUDENT_ITEM = 'student_item', '生徒商品'
        INVOICE = 'invoice', '請求書'
        PAYMENT = 'payment', '入金'
        MILE = 'mile', 'マイル'
        DISCOUNT = 'discount', '割引'
        SCHOOL = 'school', '校舎'
        COURSE = 'course', 'コース'
        CLASS_SCHEDULE = 'class_schedule', 'クラススケジュール'
        ENROLLMENT = 'enrollment', '受講登録'
        USER = 'user', 'ユーザー'
        OTHER = 'other', 'その他'

    class ActionType(models.TextChoices):
        CREATE = 'create', '作成'
        UPDATE = 'update', '更新'
        DELETE = 'delete', '削除'
        SOFT_DELETE = 'soft_delete', '論理削除'
        RESTORE = 'restore', '復元'
        LOGIN = 'login', 'ログイン'
        LOGOUT = 'logout', 'ログアウト'
        EXPORT = 'export', 'エクスポート'
        IMPORT = 'import', 'インポート'
        APPROVE = 'approve', '承認'
        REJECT = 'reject', '却下'
        CANCEL = 'cancel', 'キャンセル'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 対象エンティティ
    entity_type = models.CharField(
        'エンティティ種別',
        max_length=30,
        choices=EntityType.choices
    )
    entity_id = models.CharField('エンティティID', max_length=100)
    entity_name = models.CharField('エンティティ名', max_length=200, blank=True)

    # 操作種別
    action_type = models.CharField(
        '操作種別',
        max_length=30,
        choices=ActionType.choices
    )
    action_detail = models.CharField('操作詳細', max_length=500)

    # 変更データ
    before_data = models.JSONField('変更前データ', null=True, blank=True)
    after_data = models.JSONField('変更後データ', null=True, blank=True)
    changed_fields = models.JSONField(
        '変更フィールド',
        null=True,
        blank=True,
        help_text='変更されたフィールド名のリスト'
    )

    # 関連エンティティ（検索用）
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs',
        verbose_name='関連生徒'
    )
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs',
        verbose_name='関連保護者'
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs',
        verbose_name='関連契約'
    )

    # 操作者
    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs',
        verbose_name='操作者'
    )
    user_name = models.CharField('操作者名', max_length=100, blank=True)
    user_email = models.CharField('操作者メール', max_length=200, blank=True)

    # システム情報
    is_system_action = models.BooleanField('システム操作', default=False)
    ip_address = models.GenericIPAddressField('IPアドレス', null=True, blank=True)
    user_agent = models.TextField('ユーザーエージェント', blank=True)
    request_path = models.CharField('リクエストパス', max_length=500, blank=True)
    request_method = models.CharField('リクエストメソッド', max_length=10, blank=True)

    # 結果
    is_success = models.BooleanField('成功', default=True)
    error_message = models.TextField('エラーメッセージ', blank=True)

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 'system_audit_logs'
        verbose_name = 'システム監査ログ'
        verbose_name_plural = 'システム監査ログ'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['action_type']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['student']),
            models.Index(fields=['guardian']),
            models.Index(fields=['contract']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"[{self.entity_type}] {self.action_detail} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    @classmethod
    def log(cls, tenant_id, entity_type, entity_id, action_type, action_detail,
            user=None, before_data=None, after_data=None, request=None, **kwargs):
        """監査ログを記録するヘルパーメソッド"""
        log_data = {
            'tenant_id': tenant_id,
            'entity_type': entity_type,
            'entity_id': str(entity_id),
            'action_type': action_type,
            'action_detail': action_detail,
            'before_data': before_data,
            'after_data': after_data,
        }

        if user:
            log_data['user'] = user
            log_data['user_name'] = user.get_full_name() if hasattr(user, 'get_full_name') else str(user)
            log_data['user_email'] = getattr(user, 'email', '')

        if request:
            log_data['ip_address'] = cls._get_client_ip(request)
            log_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')[:500]
            log_data['request_path'] = request.path[:500]
            log_data['request_method'] = request.method

        log_data.update(kwargs)
        return cls.objects.create(**log_data)

    @staticmethod
    def _get_client_ip(request):
        """クライアントIPアドレスを取得"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


# =============================================================================
# 割引操作履歴 (DiscountOperationLog) - 割引変更を記録し、校舎負担分を追跡
# =============================================================================
class DiscountOperationLog(TenantModel):
    """割引操作履歴

    割引の追加・変更・削除を記録し、割引Max超過時の校舎負担分を追跡する。
    """

    class OperationType(models.TextChoices):
        ADD = 'add', '追加'
        UPDATE = 'update', '変更'
        DELETE = 'delete', '削除'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 対象
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='discount_logs',
        verbose_name='契約'
    )
    student_discount = models.ForeignKey(
        StudentDiscount,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='operation_logs',
        verbose_name='割引'
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='discount_logs',
        verbose_name='生徒'
    )

    # 操作種別
    operation_type = models.CharField(
        '操作種別',
        max_length=10,
        choices=OperationType.choices
    )

    # 割引情報
    discount_name = models.CharField('割引名', max_length=200)
    discount_amount = models.DecimalField(
        '割引額',
        max_digits=10,
        decimal_places=0,
        help_text='適用された割引額'
    )
    discount_unit = models.CharField(
        '割引単位',
        max_length=10,
        default='yen'
    )

    # 割引Max情報
    discount_max = models.DecimalField(
        '割引Max',
        max_digits=10,
        decimal_places=0,
        default=0,
        help_text='適用時点の商品の割引Max'
    )
    total_discount_before = models.DecimalField(
        '操作前の合計割引額',
        max_digits=10,
        decimal_places=0,
        default=0
    )
    total_discount_after = models.DecimalField(
        '操作後の合計割引額',
        max_digits=10,
        decimal_places=0,
        default=0
    )

    # 校舎負担分（割引Max超過分）
    excess_amount = models.DecimalField(
        '校舎負担分',
        max_digits=10,
        decimal_places=0,
        default=0,
        help_text='割引Maxを超過した金額（校舎負担）'
    )

    # 担当校舎（負担する校舎）
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='discount_excess_logs',
        verbose_name='担当校舎'
    )
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='discount_excess_logs',
        verbose_name='ブランド'
    )

    # 操作者
    operated_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='discount_operations',
        verbose_name='操作者'
    )
    operated_by_name = models.CharField('操作者名', max_length=100, blank=True)

    # IPアドレス（監査用）
    ip_address = models.GenericIPAddressField('IPアドレス', null=True, blank=True)

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 'discount_operation_logs'
        verbose_name = '割引操作履歴'
        verbose_name_plural = '割引操作履歴'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['contract', '-created_at']),
            models.Index(fields=['student', '-created_at']),
            models.Index(fields=['school', '-created_at']),
            models.Index(fields=['operated_by', '-created_at']),
        ]

    def __str__(self):
        return f"{self.contract.contract_no} - {self.get_operation_type_display()} {self.discount_name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    @classmethod
    def log_operation(cls, contract, operation_type, discount_name, discount_amount,
                      discount_unit='yen', discount_max=0, total_before=0, total_after=0,
                      user=None, school=None, brand=None, student_discount=None,
                      ip_address=None, notes=''):
        """割引操作をログに記録するヘルパーメソッド

        Args:
            contract: 契約
            operation_type: 操作種別 ('add', 'update', 'delete')
            discount_name: 割引名
            discount_amount: 割引額
            discount_unit: 割引単位 ('yen' or 'percent')
            discount_max: 割引Max
            total_before: 操作前の合計割引額
            total_after: 操作後の合計割引額
            user: 操作者
            school: 担当校舎
            brand: ブランド
            student_discount: StudentDiscountインスタンス
            ip_address: IPアドレス
            notes: 備考
        """
        # 校舎負担分（割引Max超過分）を計算
        excess_amount = max(0, total_after - discount_max) if discount_max > 0 else 0

        return cls.objects.create(
            tenant_id=contract.tenant_id,
            contract=contract,
            student_discount=student_discount,
            student=contract.student,
            operation_type=operation_type,
            discount_name=discount_name,
            discount_amount=discount_amount,
            discount_unit=discount_unit,
            discount_max=discount_max,
            total_discount_before=total_before,
            total_discount_after=total_after,
            excess_amount=excess_amount,
            school=school or contract.school,
            brand=brand or contract.brand,
            operated_by=user,
            operated_by_name=user.get_full_name() if user else '',
            ip_address=ip_address,
            notes=notes
        )
