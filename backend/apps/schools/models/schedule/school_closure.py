"""
SchoolClosure Model - 休講・休校マスタ
"""
import uuid
from django.db import models
from apps.core.models import TenantModel

from apps.schools.models.brand import Brand
from apps.schools.models.school import School
from .school_schedule import SchoolSchedule


class SchoolClosure(TenantModel):
    """T16: 休講・休校マスタ（特定日の休講を管理）"""

    class ClosureType(models.TextChoices):
        SCHOOL_CLOSED = 'school_closed', '校舎休校'  # 校舎全体が休み
        BRAND_CLOSED = 'brand_closed', 'ブランド休講'  # 特定ブランドだけ休み
        SCHEDULE_CLOSED = 'schedule_closed', '時間帯休講'  # 特定時間帯だけ休み
        HOLIDAY = 'holiday', '祝日休講'
        MAINTENANCE = 'maintenance', 'メンテナンス'
        WEATHER = 'weather', '天候不良'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 休講の範囲指定（上から優先度順にチェック）
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='closures',
        verbose_name='校舎',
        null=True,
        blank=True,
        help_text='指定しない場合は全校舎'
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name='closures',
        verbose_name='ブランド',
        null=True,
        blank=True,
        help_text='指定しない場合は全ブランド'
    )
    schedule = models.ForeignKey(
        SchoolSchedule,
        on_delete=models.CASCADE,
        related_name='closures',
        verbose_name='スケジュール',
        null=True,
        blank=True,
        help_text='特定の曜日・時間帯のみ休講の場合'
    )

    # 休講日
    closure_date = models.DateField('休講日')
    closure_type = models.CharField(
        '休講種別',
        max_length=20,
        choices=ClosureType.choices,
        default=ClosureType.OTHER
    )

    # 振替授業の設定
    has_makeup = models.BooleanField('振替あり', default=False)
    makeup_date = models.DateField('振替日', null=True, blank=True)
    makeup_schedule = models.ForeignKey(
        SchoolSchedule,
        on_delete=models.SET_NULL,
        related_name='makeup_closures',
        verbose_name='振替スケジュール',
        null=True,
        blank=True
    )

    reason = models.CharField('休講理由', max_length=200, blank=True)
    notes = models.TextField('備考', blank=True)
    notified_at = models.DateTimeField('通知日時', null=True, blank=True)

    class Meta:
        db_table = 't16_school_closures'
        verbose_name = 'T16_休講'
        verbose_name_plural = 'T16_休講'
        ordering = ['-closure_date']

    def __str__(self):
        school_name = self.school.school_name if self.school else '全校舎'
        return f"{self.closure_date} {school_name} {self.get_closure_type_display()}"

    @classmethod
    def is_closed(cls, school, brand, date, time_slot=None):
        """指定日時が休講かどうかを判定"""
        from django.db.models import Q

        closures = cls.objects.filter(
            closure_date=date,
            tenant_id=school.tenant_id
        ).filter(
            # 校舎全体休校 OR 指定校舎休校
            Q(school__isnull=True) | Q(school=school)
        ).filter(
            # 全ブランド休講 OR 指定ブランド休講
            Q(brand__isnull=True) | Q(brand=brand)
        )

        if time_slot:
            closures = closures.filter(
                Q(schedule__isnull=True) | Q(schedule__time_slot=time_slot)
            )

        return closures.exists()
