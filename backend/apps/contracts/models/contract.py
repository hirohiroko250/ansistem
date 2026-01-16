"""
Contract Models - 契約関連
契約 (Contract)
T04: 生徒商品 (StudentItem)
T06: 生徒割引 (StudentDiscount)
"""
import uuid
from django.db import models
from apps.core.models import TenantModel


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
        'contracts.Course',
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
        'contracts.Product',
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
        unique_together = ['tenant_id', 'contract_no', 'student']

    def __str__(self):
        return f"{self.contract_no} - {self.student}"


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
        'contracts.Product',
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
        'contracts.Course',
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
    billing_month = models.CharField(
        '対象月',
        max_length=7,
        help_text='サービス提供月（例: 2025-04）。表示用。'
    )
    quantity = models.IntegerField('数量', default=1)
    unit_price = models.DecimalField('単価', max_digits=10, decimal_places=0)
    discount_amount = models.DecimalField('割引額', max_digits=10, decimal_places=0, default=0)
    final_price = models.DecimalField('確定金額', max_digits=10, decimal_places=0)

    # 請求確定状態
    is_billed = models.BooleanField(
        '請求済み',
        default=False,
        help_text='確定ボタンで請求に含まれたらTrue'
    )
    confirmed_billing = models.ForeignKey(
        'billing.ConfirmedBilling',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_items',
        verbose_name='請求確定',
        help_text='どの請求確定に含まれたか'
    )

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't04_student_items'
        verbose_name = 'T04_生徒商品'
        verbose_name_plural = 'T04_生徒商品'
        ordering = ['-billing_month', 'student']

    def __str__(self):
        return f"{self.student} - {self.product} ({self.billing_month})"


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
