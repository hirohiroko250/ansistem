"""
HR Attendance Models - 勤怠管理モデル
"""
import uuid
from django.db import models
from django.utils import timezone

from apps.core.models import TenantModel


class HRAttendance(TenantModel):
    """講師・スタッフ勤怠記録（出退勤管理）"""

    class AttendanceStatus(models.TextChoices):
        WORKING = 'working', '勤務中'
        COMPLETED = 'completed', '退勤済'
        ABSENT = 'absent', '欠勤'
        LEAVE = 'leave', '休暇'
        HOLIDAY = 'holiday', '休日'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='hr_attendances',
        verbose_name='ユーザー'
    )
    date = models.DateField(
        verbose_name='日付',
        db_index=True
    )
    clock_in = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='出勤時刻'
    )
    clock_out = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='退勤時刻'
    )
    break_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name='休憩時間（分）'
    )
    work_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name='勤務時間（分）'
    )
    overtime_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name='残業時間（分）'
    )
    late_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name='遅刻時間（分）'
    )
    early_leave_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name='早退時間（分）'
    )
    status = models.CharField(
        max_length=20,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.WORKING,
        verbose_name='ステータス'
    )
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hr_attendances',
        verbose_name='校舎'
    )
    daily_report = models.TextField(
        null=True,
        blank=True,
        verbose_name='日報'
    )
    notes = models.TextField(
        null=True,
        blank=True,
        verbose_name='備考'
    )
    # QRコード打刻時に記録
    qr_code_used = models.BooleanField(
        default=False,
        verbose_name='QRコード打刻'
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
        related_name='approved_hr_attendances',
        verbose_name='承認者'
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='承認日時'
    )

    class Meta:
        db_table = 't_hr_attendance'
        verbose_name = '勤怠記録'
        verbose_name_plural = '勤怠記録'
        ordering = ['-date', '-clock_in']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'date'],
                name='unique_user_date_attendance'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['tenant_id', 'date']),
        ]

    def __str__(self):
        return f"{self.user.full_name} - {self.date}"

    def calculate_work_minutes(self):
        """勤務時間を計算"""
        if self.clock_in and self.clock_out:
            delta = self.clock_out - self.clock_in
            total_minutes = int(delta.total_seconds() / 60)
            self.work_minutes = max(0, total_minutes - self.break_minutes)
        return self.work_minutes

    def save(self, *args, **kwargs):
        # 退勤時に勤務時間を自動計算
        if self.clock_out:
            self.calculate_work_minutes()
            if self.status == self.AttendanceStatus.WORKING:
                self.status = self.AttendanceStatus.COMPLETED
        super().save(*args, **kwargs)
