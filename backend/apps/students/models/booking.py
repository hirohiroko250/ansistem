"""
Trial Booking Model - 体験予約
"""
import uuid
from django.db import models
from apps.core.models import TenantModel

from .student import Student
from .guardian import Guardian


class TrialBooking(TenantModel):
    """体験予約（日時指定・人数管理）"""

    class Status(models.TextChoices):
        PENDING = 'pending', '予約待ち'
        CONFIRMED = 'confirmed', '確定'
        CANCELLED = 'cancelled', 'キャンセル'
        COMPLETED = 'completed', '完了'
        NO_SHOW = 'no_show', '無断欠席'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 誰が予約
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='trial_bookings',
        verbose_name='生徒'
    )
    guardian = models.ForeignKey(
        Guardian,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='trial_bookings',
        verbose_name='保護者'
    )

    # どこで
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='trial_bookings',
        verbose_name='校舎'
    )
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.CASCADE,
        related_name='trial_bookings',
        verbose_name='ブランド'
    )

    # いつ（日時指定）
    trial_date = models.DateField('体験日')
    schedule = models.ForeignKey(
        'schools.SchoolSchedule',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='trial_bookings',
        verbose_name='スケジュール枠'
    )
    time_slot = models.ForeignKey(
        'schools.TimeSlot',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='trial_bookings',
        verbose_name='時間帯'
    )

    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # 追加情報
    notes = models.TextField('備考', blank=True)
    confirmed_at = models.DateTimeField('確定日時', null=True, blank=True)
    cancelled_at = models.DateTimeField('キャンセル日時', null=True, blank=True)
    cancellation_reason = models.TextField('キャンセル理由', blank=True)

    # 関連タスク（UUIDで参照、循環参照回避）
    task_id_ref = models.UUIDField('関連タスクID', null=True, blank=True)

    class Meta:
        db_table = 't03_trial_bookings'
        verbose_name = 'T3_体験予約'
        verbose_name_plural = 'T3_体験予約'
        ordering = ['trial_date', 'created_at']
        # 同じ生徒が同じ日時に複数予約できないようにする
        unique_together = ['student', 'trial_date', 'schedule']

    def __str__(self):
        return f"{self.student} - {self.trial_date} {self.school.school_name}"

    @classmethod
    def get_booked_count(cls, schedule_id, trial_date):
        """指定スケジュール・日付の予約数を取得"""
        return cls.objects.filter(
            schedule_id=schedule_id,
            trial_date=trial_date,
            status__in=[cls.Status.PENDING, cls.Status.CONFIRMED]
        ).count()

    @classmethod
    def is_available(cls, schedule_id, trial_date, trial_capacity):
        """指定スケジュール・日付が予約可能か確認"""
        booked = cls.get_booked_count(schedule_id, trial_date)
        return booked < trial_capacity


# 欠席・振替チケット（students admin用Proxyモデル）
# 循環インポートを避けるためここで定義
from apps.lessons.models import AbsenceTicket as LessonsAbsenceTicket


class AbsenceTicket(LessonsAbsenceTicket):
    """欠席・振替チケット（生徒管理用）

    lessonsアプリのAbsenceTicketを継承したProxyモデル。
    これによりstudents adminセクションに表示される。
    """
    class Meta:
        proxy = True
        app_label = 'students'
        verbose_name = '欠席・振替チケット'
        verbose_name_plural = '欠席・振替チケット'
