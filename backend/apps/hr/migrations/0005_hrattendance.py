"""
HRAttendance model for teacher/staff clock-in/out
"""
import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0004_alter_payroll_unique_together_and_more'),
        ('schools', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='HRAttendance',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('tenant_id', models.UUIDField(db_index=True, verbose_name='テナントID')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='削除日時')),
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID'
                    )
                ),
                ('date', models.DateField(db_index=True, verbose_name='日付')),
                ('clock_in', models.DateTimeField(blank=True, null=True, verbose_name='出勤時刻')),
                ('clock_out', models.DateTimeField(blank=True, null=True, verbose_name='退勤時刻')),
                ('break_minutes', models.PositiveIntegerField(default=0, verbose_name='休憩時間（分）')),
                ('work_minutes', models.PositiveIntegerField(default=0, verbose_name='勤務時間（分）')),
                ('overtime_minutes', models.PositiveIntegerField(default=0, verbose_name='残業時間（分）')),
                ('late_minutes', models.PositiveIntegerField(default=0, verbose_name='遅刻時間（分）')),
                ('early_leave_minutes', models.PositiveIntegerField(default=0, verbose_name='早退時間（分）')),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('working', '勤務中'),
                            ('completed', '退勤済'),
                            ('absent', '欠勤'),
                            ('leave', '休暇'),
                            ('holiday', '休日')
                        ],
                        default='working',
                        max_length=20,
                        verbose_name='ステータス'
                    )
                ),
                ('daily_report', models.TextField(blank=True, null=True, verbose_name='日報')),
                ('notes', models.TextField(blank=True, null=True, verbose_name='備考')),
                ('qr_code_used', models.BooleanField(default=False, verbose_name='QRコード打刻')),
                ('is_approved', models.BooleanField(default=False, verbose_name='承認済み')),
                ('approved_at', models.DateTimeField(blank=True, null=True, verbose_name='承認日時')),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='hr_attendances',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='ユーザー'
                    )
                ),
                (
                    'school',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='hr_attendances',
                        to='schools.school',
                        verbose_name='校舎'
                    )
                ),
                (
                    'approved_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='approved_hr_attendances',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='承認者'
                    )
                ),
            ],
            options={
                'verbose_name': '勤怠記録',
                'verbose_name_plural': '勤怠記録',
                'db_table': 't_hr_attendance',
                'ordering': ['-date', '-clock_in'],
            },
        ),
        migrations.AddConstraint(
            model_name='hrattendance',
            constraint=models.UniqueConstraint(fields=('user', 'date'), name='unique_user_date_attendance'),
        ),
        migrations.AddIndex(
            model_name='hrattendance',
            index=models.Index(fields=['user', 'date'], name='t_hr_attend_user_id_54d7ee_idx'),
        ),
        migrations.AddIndex(
            model_name='hrattendance',
            index=models.Index(fields=['tenant_id', 'date'], name='t_hr_attend_tenant__4f3b8e_idx'),
        ),
    ]
