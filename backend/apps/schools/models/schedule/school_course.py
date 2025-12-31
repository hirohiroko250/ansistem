"""
SchoolCourse Model - 校舎別コース開講設定
"""
import uuid
from django.db import models
from apps.core.models import TenantModel

from apps.schools.models.school import School
from .school_schedule import SchoolSchedule


class SchoolCourse(TenantModel):
    """T15: 校舎別コース開講設定（どの校舎でどのコースを開講するか）"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='school_courses',
        verbose_name='校舎'
    )
    course = models.ForeignKey(
        'contracts.Course',
        on_delete=models.CASCADE,
        related_name='school_courses',
        verbose_name='コース'
    )
    # 開講曜日・時間帯
    schedule = models.ForeignKey(
        SchoolSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='courses',
        verbose_name='開講スケジュール'
    )
    # コース固有の席数（スケジュールと別に設定する場合）
    capacity_override = models.IntegerField('席数上書き', null=True, blank=True)

    # 期間
    valid_from = models.DateField('開講開始日', null=True, blank=True)
    valid_until = models.DateField('開講終了日', null=True, blank=True)

    notes = models.TextField('備考', blank=True)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't15_school_courses'
        verbose_name = 'T15_校舎別コース'
        verbose_name_plural = 'T15_校舎別コース'
        ordering = ['school', 'course']
        unique_together = ['school', 'course', 'schedule']

    def __str__(self):
        return f"{self.school.school_name} - {self.course.course_name}"

    @property
    def effective_capacity(self):
        """有効な席数（上書きがあればそちらを使用）"""
        if self.capacity_override is not None:
            return self.capacity_override
        if self.schedule:
            return self.schedule.capacity
        return None
