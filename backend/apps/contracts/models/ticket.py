"""
Ticket Models - チケットマスタ
T07: チケット (Ticket)
T08b: コース→チケット紐づけ (CourseTicket)
T10: 追加チケット (AdditionalTicket)
T10b: 追加チケット対象日 (AdditionalTicketDate)
"""
import uuid
from decimal import Decimal
from django.db import models
from apps.core.models import TenantModel


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


class CourseTicket(TenantModel):
    """T08b: コースチケット構成

    コースに紐づくチケットを定義
    T8_契約とチケット情報.xlsxに対応
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    course = models.ForeignKey(
        'contracts.Course',
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
        'contracts.Course',
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
        'contracts.StudentItem',
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
