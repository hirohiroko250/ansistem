"""
SchoolSchedule Model - 校舎開講スケジュール
"""
import uuid
from django.db import models
from apps.core.models import TenantModel

from apps.schools.models.brand import Brand
from apps.schools.models.school import School
from apps.schools.models.classroom import TimeSlot


class SchoolSchedule(TenantModel):
    """T14: 校舎開講スケジュール（ブランド×校舎×曜日×時間帯で開講を管理）"""

    class DayOfWeek(models.IntegerChoices):
        MONDAY = 1, '月曜日'
        TUESDAY = 2, '火曜日'
        WEDNESDAY = 3, '水曜日'
        THURSDAY = 4, '木曜日'
        FRIDAY = 5, '金曜日'
        SATURDAY = 6, '土曜日'
        SUNDAY = 7, '日曜日'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='ブランド'
    )
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='校舎'
    )
    day_of_week = models.IntegerField(
        '曜日',
        choices=DayOfWeek.choices
    )
    time_slot = models.ForeignKey(
        TimeSlot,
        on_delete=models.PROTECT,
        related_name='schedules',
        verbose_name='時間帯'
    )
    # 席数管理
    capacity = models.IntegerField('定員（席数）', default=10)
    trial_capacity = models.IntegerField('体験受入可能数', default=2)
    reserved_seats = models.IntegerField('予約済み席数', default=0)  # キャッシュ用
    pause_seat_fee = models.DecimalField('休会時座席料金', max_digits=10, decimal_places=0, default=0)

    # カレンダーマスター参照（新規）
    calendar_master = models.ForeignKey(
        'schools.CalendarMaster',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='class_schedules',
        verbose_name='カレンダーマスター'
    )

    # カレンダーパターン（後方互換用）
    calendar_pattern = models.CharField(
        'カレンダーパターン',
        max_length=50,
        blank=True,
        help_text='例: 1001_AEC_A, 1002_AEC_B, 1003_AEC_P'
    )

    # 期間（年度や特定期間のみ開講の場合）
    valid_from = models.DateField('有効開始日', null=True, blank=True)
    valid_until = models.DateField('有効終了日', null=True, blank=True)

    notes = models.TextField('備考', blank=True)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't14_school_schedules'
        verbose_name = 'T14_校舎開講スケジュール'
        verbose_name_plural = 'T14_校舎開講スケジュール'
        ordering = ['school', 'day_of_week', 'time_slot__start_time']
        unique_together = ['brand', 'school', 'day_of_week', 'time_slot']

    def __str__(self):
        return f"{self.school.school_name} {self.get_day_of_week_display()} {self.time_slot.slot_name}"

    @property
    def available_seats(self):
        """空き席数"""
        return max(0, self.capacity - self.reserved_seats)

    def is_available(self):
        """予約可能かどうか"""
        return self.is_active and self.available_seats > 0
