"""
Calendar Models - カレンダー関連
CalendarMaster, LessonCalendar, CalendarOperationLog
"""
import uuid
from django.db import models
from apps.core.models import TenantModel

from .brand import Brand
from .school import School


class CalendarMaster(TenantModel):
    """T13m: カレンダーマスター（カレンダーコードの定義）

    カレンダーコードの命名規則:
    - {校舎番号}_{ブランドコード}_{パターン}: 例 1001_SKAEC_A, 1003_AEC_P
    - {特殊コード}: 例 Int_24（インターナショナル）
    """

    class LessonType(models.TextChoices):
        TYPE_A = 'A', 'Aパターン（外国人講師あり）'
        TYPE_B = 'B', 'Bパターン（日本人講師のみ）'
        TYPE_P = 'P', 'Pパターン（ペア）'
        TYPE_Y = 'Y', 'Yパターン（インター）'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    code = models.CharField(
        'カレンダーコード',
        max_length=50,
        db_index=True,
        help_text='例: 1001_SKAEC_A, 1003_AEC_P, Int_24'
    )
    name = models.CharField('カレンダー名', max_length=100, blank=True)

    # ブランド紐付け
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='calendar_masters',
        verbose_name='ブランド'
    )

    # パターン
    lesson_type = models.CharField(
        '授業タイプ',
        max_length=10,
        choices=LessonType.choices,
        default=LessonType.TYPE_A
    )

    description = models.TextField('説明', blank=True)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't13m_calendar_masters'
        verbose_name = 'T13m_カレンダーマスター'
        verbose_name_plural = 'T13m_カレンダーマスター'
        ordering = ['sort_order', 'code']
        unique_together = ['tenant_id', 'code']

    def __str__(self):
        return f"{self.code} - {self.name or self.get_lesson_type_display()}"

    @classmethod
    def get_or_create_from_code(cls, tenant_id, code, brand=None):
        """カレンダーコードからマスターを取得または作成"""
        if not code:
            return None

        master, created = cls.objects.get_or_create(
            tenant_id=tenant_id,
            code=code,
            defaults={
                'brand': brand,
                'lesson_type': cls._detect_lesson_type(code),
                'name': code,
            }
        )
        return master

    @staticmethod
    def _detect_lesson_type(code):
        """コードからパターンを推測"""
        code_upper = code.upper()
        if code_upper.endswith('_A') or '_A_' in code_upper:
            return CalendarMaster.LessonType.TYPE_A
        elif code_upper.endswith('_B') or '_B_' in code_upper:
            return CalendarMaster.LessonType.TYPE_B
        elif code_upper.endswith('_P') or '_P_' in code_upper:
            return CalendarMaster.LessonType.TYPE_P
        elif 'INT' in code_upper or code_upper.endswith('_Y'):
            return CalendarMaster.LessonType.TYPE_Y
        return CalendarMaster.LessonType.OTHER


class LessonCalendar(TenantModel):
    """T13: 開講カレンダー（日別の開講情報を管理）

    テナント単位で管理（全校舎共通）
    カレンダーコードでパターンを識別:
    - 1001_SKAEC_A: Aパターン（外国人講師あり）
    - 1002_SKAEC_B: Bパターン（日本人講師のみ）
    - 1003_AEC_P: Pパターン（ペアクラス等）
    - Int_24: インターナショナル
    """

    class LessonType(models.TextChoices):
        TYPE_A = 'A', 'Aパターン（外国人講師あり）'
        TYPE_B = 'B', 'Bパターン（日本人講師のみ）'
        TYPE_P = 'P', 'Pパターン（ペア）'
        TYPE_Y = 'Y', 'Yパターン（インター）'
        CLOSED = 'closed', '休講'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # カレンダーマスター参照（新規）
    calendar_master = models.ForeignKey(
        CalendarMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_calendars',
        verbose_name='カレンダーマスター'
    )

    # カレンダー識別（後方互換用、calendar_masterから取得可能）
    calendar_code = models.CharField(
        'カレンダーコード',
        max_length=50,
        db_index=True,
        help_text='例: 1001_SKAEC_A, 1003_AEC_P, Int_24'
    )
    # ブランドは参照用（オプション）
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_calendars',
        verbose_name='ブランド'
    )
    # 校舎は不要（テナント全体で共通）だが後方互換性のため残す
    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_calendars',
        verbose_name='校舎（後方互換用）'
    )

    # 日付情報
    lesson_date = models.DateField('授業日')
    day_of_week = models.CharField('曜日', max_length=10)

    # 開講情報
    is_open = models.BooleanField('開講日', default=False)
    lesson_type = models.CharField(
        '授業タイプ',
        max_length=10,
        choices=LessonType.choices,
        default=LessonType.CLOSED
    )
    display_label = models.CharField(
        '保護者カレンダー表示',
        max_length=20,
        blank=True,
        help_text='例: 水A1, 木B2など'
    )

    # チケット情報
    ticket_type = models.CharField(
        'チケット券種',
        max_length=10,
        blank=True,
        help_text='A, Bなど'
    )
    ticket_sequence = models.IntegerField(
        'チケット番号',
        null=True,
        blank=True,
        help_text='月内の何回目か'
    )

    # 振替関連
    is_makeup_allowed = models.BooleanField('振替許可', default=True, help_text='振替拒否の場合はFalse')
    rejection_reason = models.CharField('振替拒否理由', max_length=100, blank=True)

    # チケット発券
    ticket_issue_count = models.IntegerField('権利発券数', null=True, blank=True, help_text='発行するチケット数')

    # 有効期限（チケットの有効期限など）
    valid_days = models.IntegerField('有効日数', default=90)

    # メッセージ
    notice_message = models.TextField('お知らせ', blank=True)
    auto_send_notice = models.BooleanField('自動お知らせ送信', default=False)
    holiday_name = models.CharField('祝日名', max_length=50, blank=True)

    class Meta:
        db_table = 't13_lesson_calendars'
        verbose_name = 'T13_開講カレンダー'
        verbose_name_plural = 'T13_開講カレンダー'
        ordering = ['calendar_code', 'lesson_date']
        # カレンダーコード + 日付でユニーク（テナント単位）
        unique_together = ['tenant_id', 'calendar_code', 'lesson_date']

    def __str__(self):
        return f"{self.calendar_code} {self.lesson_date} {self.lesson_type}"

    @property
    def is_native_day(self):
        """外国人講師がいる日かどうか"""
        return self.lesson_type == self.LessonType.TYPE_A

    @property
    def is_japanese_only(self):
        """日本人講師のみの日かどうか"""
        return self.lesson_type == self.LessonType.TYPE_B

    @classmethod
    def get_calendar_for_month(cls, tenant_id, brand_id, school_id, year, month):
        """指定月のカレンダーを取得"""
        from datetime import date
        import calendar

        # 月の開始日と終了日
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        return cls.objects.filter(
            tenant_id=tenant_id,
            brand_id=brand_id,
            school_id=school_id,
            lesson_date__gte=first_day,
            lesson_date__lte=last_day
        ).order_by('lesson_date')

    @classmethod
    def get_available_dates(cls, tenant_id, brand_id, school_id, year, month):
        """指定月の予約可能日を取得"""
        return cls.get_calendar_for_month(
            tenant_id, brand_id, school_id, year, month
        ).filter(is_open=True)


class CalendarOperationLog(TenantModel):
    """
    カレンダー操作ログ
    ABスワップ、休校設定などの操作履歴を記録
    """

    class OperationType(models.TextChoices):
        AB_SWAP = 'ab_swap', 'ABスワップ'
        SET_CLOSURE = 'set_closure', '休校設定'
        CANCEL_CLOSURE = 'cancel_closure', '休校解除'
        LESSON_TYPE_CHANGE = 'lesson_type_change', 'レッスンタイプ変更'
        SCHEDULE_CHANGE = 'schedule_change', 'スケジュール変更'
        STAFF_ABSENCE = 'staff_absence', 'スタッフ欠勤'
        NATIVE_ABSENCE = 'native_absence', '外国人欠勤'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    operation_type = models.CharField(
        '操作種別',
        max_length=30,
        choices=OperationType.choices
    )

    # 対象
    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operation_logs',
        verbose_name='校舎'
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operation_logs',
        verbose_name='ブランド'
    )
    schedule = models.ForeignKey(
        'schools.SchoolSchedule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operation_logs',
        verbose_name='スケジュール'
    )
    lesson_calendar = models.ForeignKey(
        LessonCalendar,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operation_logs',
        verbose_name='開講カレンダー'
    )

    # 操作日時・対象日
    operation_date = models.DateField('対象日')
    operated_at = models.DateTimeField('操作日時', auto_now_add=True)

    # 操作者
    operated_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='calendar_operations',
        verbose_name='操作者'
    )

    # 変更内容
    old_value = models.CharField('変更前', max_length=100, blank=True)
    new_value = models.CharField('変更後', max_length=100, blank=True)
    reason = models.TextField('理由', blank=True)
    notes = models.TextField('備考', blank=True)

    # メタデータ
    metadata = models.JSONField('メタデータ', default=dict, blank=True)

    class Meta:
        db_table = 'calendar_operation_logs'
        verbose_name = 'カレンダー操作ログ'
        verbose_name_plural = 'カレンダー操作ログ'
        ordering = ['-operated_at']

    def __str__(self):
        return f"{self.get_operation_type_display()} - {self.operation_date} ({self.operated_at.strftime('%Y-%m-%d %H:%M')})"

    @classmethod
    def log_ab_swap(cls, tenant_id, school, brand, lesson_calendar, old_type, new_type, user=None, reason=''):
        """ABスワップをログに記録"""
        return cls.objects.create(
            tenant_id=tenant_id,
            operation_type=cls.OperationType.AB_SWAP,
            school=school,
            brand=brand,
            lesson_calendar=lesson_calendar,
            operation_date=lesson_calendar.lesson_date if lesson_calendar else None,
            operated_by=user,
            old_value=old_type,
            new_value=new_type,
            reason=reason,
            metadata={
                'calendar_code': lesson_calendar.calendar_code if lesson_calendar else None,
            }
        )

    @classmethod
    def log_closure(cls, tenant_id, closure, user=None):
        """休校設定をログに記録"""
        return cls.objects.create(
            tenant_id=tenant_id,
            operation_type=cls.OperationType.SET_CLOSURE,
            school=closure.school,
            brand=closure.brand,
            schedule=closure.schedule,
            operation_date=closure.closure_date,
            operated_by=user,
            new_value=closure.get_closure_type_display(),
            reason=closure.reason or '',
            metadata={
                'closure_id': str(closure.id),
                'closure_type': closure.closure_type,
            }
        )

    @classmethod
    def log_staff_absence(cls, tenant_id, school, brand, date, staff_type, user=None, reason=''):
        """スタッフ欠勤をログに記録"""
        op_type = cls.OperationType.NATIVE_ABSENCE if staff_type == 'native' else cls.OperationType.STAFF_ABSENCE
        return cls.objects.create(
            tenant_id=tenant_id,
            operation_type=op_type,
            school=school,
            brand=brand,
            operation_date=date,
            operated_by=user,
            reason=reason,
            metadata={
                'staff_type': staff_type,
            }
        )
