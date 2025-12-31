"""
Product Models - 商品マスタ
T03: 商品マスタ (Product)
T05: 商品料金マスタ (ProductPrice)
T06: 商品セット (ProductSet, ProductSetItem)
"""
import uuid
from decimal import Decimal
from django.db import models
from apps.core.models import TenantModel


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
        # まずProductPriceから取得を試みる
        price_record = self.prices.filter(is_active=True).first()
        if price_record:
            price = price_record.get_enrollment_price(enrollment_month)
            if price is not None and price > 0:
                return price

        # ProductPrice がない場合は Product 自体のenrollment_price フィールドから取得
        enrollment_price_map = {
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
        product_enrollment_price = enrollment_price_map.get(enrollment_month)
        if product_enrollment_price is not None and product_enrollment_price > 0:
            return product_enrollment_price

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
