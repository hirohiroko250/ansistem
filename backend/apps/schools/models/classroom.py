"""
Classroom Models - 教室・時間帯
Classroom, TimeSlot
"""
import uuid
from django.db import models
from apps.core.models import TenantModel

from .school import School


class Classroom(TenantModel):
    """T11: ルーム（教室）マスタ"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='classrooms',
        verbose_name='校舎'
    )
    classroom_code = models.CharField('教室コード', max_length=20)
    classroom_name = models.CharField('教室名', max_length=50)
    capacity = models.IntegerField('Room定員', default=1)
    floor = models.CharField('階数', max_length=10, blank=True)
    room_type = models.CharField('教室種別', max_length=20, blank=True)  # 個別ブース, 集団教室等
    equipment = models.JSONField('設備', default=list, blank=True)  # ["PC", "プロジェクター"]
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't11_classrooms'
        verbose_name = 'T11_教室'
        verbose_name_plural = 'T11_教室'
        ordering = ['sort_order', 'classroom_code']
        unique_together = ['school', 'classroom_code']

    def __str__(self):
        return f"{self.school.school_name} - {self.classroom_name}"


class TimeSlot(TenantModel):
    """T13: 時間帯マスタ"""

    class DayOfWeek(models.IntegerChoices):
        MONDAY = 1, '月曜日'
        TUESDAY = 2, '火曜日'
        WEDNESDAY = 3, '水曜日'
        THURSDAY = 4, '木曜日'
        FRIDAY = 5, '金曜日'
        SATURDAY = 6, '土曜日'
        SUNDAY = 7, '日曜日'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        'School',
        on_delete=models.CASCADE,
        related_name='school_time_slots',
        verbose_name='校舎',
        null=True,
        blank=True,
    )
    day_of_week = models.IntegerField(
        '曜日',
        choices=DayOfWeek.choices,
        null=True,
        blank=True,
    )
    slot_code = models.CharField('時間帯コード', max_length=20)
    slot_name = models.CharField('時間帯名', max_length=50)  # 例: "1限", "A枠"
    start_time = models.TimeField('開始時刻')
    end_time = models.TimeField('終了時刻')
    duration_minutes = models.IntegerField('時間（分）', default=50)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't13_time_slots'
        verbose_name = 'T13_時間帯'
        verbose_name_plural = 'T13_時間帯'
        ordering = ['school', 'day_of_week', 'sort_order', 'start_time']

    def __str__(self):
        day_str = self.get_day_of_week_display() if self.day_of_week else ''
        school_str = self.school.school_name if self.school else ''
        return f"{school_str} {day_str} {self.slot_name} ({self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')})"
