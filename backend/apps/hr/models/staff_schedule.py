"""
Staff Schedule Models - 社員スケジュール・空き時間管理
"""
import uuid
from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class StaffAvailability(TenantModel):
    """社員・講師の空き時間設定（予約可能枠）"""

    class SlotStatus(models.TextChoices):
        AVAILABLE = 'available', '空き'
        BOOKED = 'booked', '予約済'
        CANCELLED = 'cancelled', 'キャンセル'
        BLOCKED = 'blocked', 'ブロック'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    employee = models.ForeignKey(
        'tenants.Employee',
        on_delete=models.CASCADE,
        related_name='availabilities',
        verbose_name='社員'
    )
    date = models.DateField(
        verbose_name='日付',
        db_index=True
    )
    start_time = models.TimeField(
        verbose_name='開始時刻'
    )
    end_time = models.TimeField(
        verbose_name='終了時刻'
    )
    status = models.CharField(
        max_length=20,
        choices=SlotStatus.choices,
        default=SlotStatus.AVAILABLE,
        verbose_name='ステータス'
    )
    # 定員設定
    capacity = models.PositiveIntegerField(
        default=1,
        verbose_name='定員'
    )
    current_bookings = models.PositiveIntegerField(
        default=0,
        verbose_name='現在の予約数'
    )
    # キャンセルポリシー
    cancel_deadline_minutes = models.PositiveIntegerField(
        default=15,
        verbose_name='キャンセル期限（分前）',
        help_text='レッスン開始の何分前までキャンセル可能か'
    )
    # 場所設定
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_availabilities',
        verbose_name='校舎'
    )
    online_available = models.BooleanField(
        default=False,
        verbose_name='オンライン対応可'
    )
    meeting_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='ミーティングURL',
        help_text='Google Meet, Zoom等のURL'
    )
    # メモ
    notes = models.TextField(
        blank=True,
        verbose_name='備考'
    )
    # 繰り返し設定
    is_recurring = models.BooleanField(
        default=False,
        verbose_name='繰り返し'
    )
    recurring_pattern = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='繰り返しパターン',
        help_text='weekly, biweekly, monthly'
    )
    recurring_end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='繰り返し終了日'
    )
    # 作成日時
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='作成日時'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新日時'
    )

    class Meta:
        db_table = 't_staff_availability'
        verbose_name = '社員空き時間'
        verbose_name_plural = '社員空き時間'
        ordering = ['date', 'start_time']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['tenant_id', 'date', 'status']),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.date} {self.start_time}-{self.end_time}"

    @property
    def is_bookable(self):
        """予約可能かどうか"""
        if self.status != self.SlotStatus.AVAILABLE:
            return False
        if self.current_bookings >= self.capacity:
            return False
        return True

    @property
    def remaining_slots(self):
        """残り枠数"""
        return max(0, self.capacity - self.current_bookings)


class StaffAvailabilityBooking(TenantModel):
    """空き時間への予約"""

    class BookingStatus(models.TextChoices):
        PENDING = 'pending', '確認待ち'
        CONFIRMED = 'confirmed', '確定'
        CANCELLED = 'cancelled', 'キャンセル'
        COMPLETED = 'completed', '完了'
        NO_SHOW = 'no_show', '欠席'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    availability = models.ForeignKey(
        StaffAvailability,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='空き時間'
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='availability_bookings',
        verbose_name='生徒'
    )
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
        verbose_name='ステータス'
    )
    # 予約詳細
    request_message = models.TextField(
        blank=True,
        verbose_name='リクエストメッセージ'
    )
    staff_notes = models.TextField(
        blank=True,
        verbose_name='講師メモ'
    )
    # 使用契約（チケット）
    student_item = models.ForeignKey(
        'contracts.StudentItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='availability_bookings',
        verbose_name='使用契約'
    )
    # キャンセル情報
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='キャンセル日時'
    )
    cancelled_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_availability_bookings',
        verbose_name='キャンセル者'
    )
    cancel_reason = models.TextField(
        blank=True,
        verbose_name='キャンセル理由'
    )
    # 作成日時
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='作成日時'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新日時'
    )

    class Meta:
        db_table = 't_staff_availability_booking'
        verbose_name = '空き時間予約'
        verbose_name_plural = '空き時間予約'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.full_name} → {self.availability}"

    def can_cancel(self):
        """キャンセル可能かどうか"""
        if self.status in [self.BookingStatus.CANCELLED, self.BookingStatus.COMPLETED]:
            return False

        now = timezone.now()
        lesson_datetime = timezone.datetime.combine(
            self.availability.date,
            self.availability.start_time,
            tzinfo=now.tzinfo
        )
        deadline = lesson_datetime - timezone.timedelta(
            minutes=self.availability.cancel_deadline_minutes
        )
        return now < deadline


class StaffWorkSchedule(TenantModel):
    """社員の勤務スケジュール（出勤予定）"""

    class ScheduleType(models.TextChoices):
        REGULAR = 'regular', '通常勤務'
        SHIFT = 'shift', 'シフト'
        OVERTIME = 'overtime', '残業'
        REMOTE = 'remote', 'リモート'
        HOLIDAY_WORK = 'holiday_work', '休日出勤'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    employee = models.ForeignKey(
        'tenants.Employee',
        on_delete=models.CASCADE,
        related_name='work_schedules',
        verbose_name='社員'
    )
    date = models.DateField(
        verbose_name='日付',
        db_index=True
    )
    schedule_type = models.CharField(
        max_length=20,
        choices=ScheduleType.choices,
        default=ScheduleType.REGULAR,
        verbose_name='勤務種別'
    )
    planned_start = models.TimeField(
        verbose_name='予定開始時刻'
    )
    planned_end = models.TimeField(
        verbose_name='予定終了時刻'
    )
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_work_schedules',
        verbose_name='勤務校舎'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='備考'
    )
    # 承認関連
    is_approved = models.BooleanField(
        default=False,
        verbose_name='承認済み'
    )
    approved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_work_schedules',
        verbose_name='承認者'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='作成日時'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新日時'
    )

    class Meta:
        db_table = 't_staff_work_schedule'
        verbose_name = '勤務スケジュール'
        verbose_name_plural = '勤務スケジュール'
        ordering = ['date', 'planned_start']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['tenant_id', 'date']),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.date} {self.planned_start}-{self.planned_end}"
