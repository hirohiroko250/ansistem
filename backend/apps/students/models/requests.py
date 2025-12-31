"""
Request Models - 休会・退会申請
SuspensionRequest, WithdrawalRequest
"""
import uuid
from django.db import models
from apps.core.models import TenantModel

from .student import Student
from .relations import StudentSchool, StudentEnrollment


class SuspensionRequest(TenantModel):
    """T13: 休会申請

    保護者からの休会申請を管理するモデル。
    申請後、スタッフが承認処理を行う。
    """

    class Status(models.TextChoices):
        PENDING = 'pending', '申請中'
        APPROVED = 'approved', '承認済'
        REJECTED = 'rejected', '却下'
        CANCELLED = 'cancelled', '取消'
        RESUMED = 'resumed', '復会済'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 対象生徒
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='suspension_requests',
        verbose_name='生徒'
    )

    # 対象ブランド・校舎
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.CASCADE,
        related_name='suspension_requests',
        verbose_name='ブランド'
    )
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='suspension_requests',
        verbose_name='校舎'
    )

    # 休会期間
    suspend_from = models.DateField('休会開始日')
    suspend_until = models.DateField('休会終了予定日', null=True, blank=True,
                                     help_text='未定の場合は空欄')

    # オプション
    keep_seat = models.BooleanField('座席保持', default=False,
                                    help_text='休会中も座席を確保する')
    monthly_fee_during_suspension = models.DecimalField(
        '休会中月会費',
        max_digits=10,
        decimal_places=0,
        null=True, blank=True,
        help_text='座席保持の場合の月会費'
    )

    # 理由
    reason = models.CharField(
        '休会理由',
        max_length=50,
        choices=[
            ('travel', '旅行・帰省'),
            ('illness', '病気・怪我'),
            ('exam', '受験準備'),
            ('schedule', 'スケジュール都合'),
            ('financial', '経済的理由'),
            ('other', 'その他'),
        ],
        default='other'
    )
    reason_detail = models.TextField('理由詳細', blank=True)

    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # 申請者情報
    requested_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='suspension_requests',
        verbose_name='申請者'
    )
    requested_at = models.DateTimeField('申請日時', auto_now_add=True)

    # 処理者情報
    processed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='processed_suspension_requests',
        verbose_name='処理者'
    )
    processed_at = models.DateTimeField('処理日時', null=True, blank=True)
    process_notes = models.TextField('処理メモ', blank=True)

    # 復会情報
    resumed_at = models.DateField('復会日', null=True, blank=True)
    resumed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='resumed_suspension_requests',
        verbose_name='復会処理者'
    )

    class Meta:
        db_table = 't13_suspension_requests'
        verbose_name = 'T13_休会申請'
        verbose_name_plural = 'T13_休会申請'
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.student} - {self.suspend_from} ({self.get_status_display()})"

    def approve(self, user, notes=''):
        """休会申請を承認"""
        from django.utils import timezone
        self.status = self.Status.APPROVED
        self.processed_by = user
        self.processed_at = timezone.now()
        self.process_notes = notes
        self.save()

        # 生徒ステータスを休会に変更
        self.student.status = Student.Status.SUSPENDED
        self.student.save()

        # StudentEnrollmentを休会に更新
        StudentEnrollment.objects.filter(
            student=self.student,
            brand=self.brand,
            end_date__isnull=True
        ).update(status=StudentEnrollment.Status.SUSPENDED)

    def resume(self, user, resume_date=None):
        """復会処理"""
        from datetime import date as date_cls
        self.status = self.Status.RESUMED
        self.resumed_at = resume_date or date_cls.today()
        self.resumed_by = user
        self.save()

        # 生徒ステータスを在籍に戻す
        self.student.status = Student.Status.ENROLLED
        self.student.save()

        # StudentEnrollmentを在籍に更新
        StudentEnrollment.objects.filter(
            student=self.student,
            brand=self.brand,
            status=StudentEnrollment.Status.SUSPENDED
        ).update(status=StudentEnrollment.Status.ENROLLED)


class WithdrawalRequest(TenantModel):
    """T14: 退会申請

    保護者からの退会申請を管理するモデル。
    申請後、スタッフが承認処理を行う。
    """

    class Status(models.TextChoices):
        PENDING = 'pending', '申請中'
        APPROVED = 'approved', '承認済'
        REJECTED = 'rejected', '却下'
        CANCELLED = 'cancelled', '取消'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 対象生徒
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='withdrawal_requests',
        verbose_name='生徒'
    )

    # 対象ブランド・校舎
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.CASCADE,
        related_name='withdrawal_requests',
        verbose_name='ブランド'
    )
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='withdrawal_requests',
        verbose_name='校舎'
    )

    # 退会日
    withdrawal_date = models.DateField('退会希望日')
    last_lesson_date = models.DateField('最終授業日', null=True, blank=True)

    # 理由
    reason = models.CharField(
        '退会理由',
        max_length=50,
        choices=[
            ('moving', '転居'),
            ('school_change', '学校変更'),
            ('graduation', '卒業'),
            ('schedule', 'スケジュール都合'),
            ('financial', '経済的理由'),
            ('satisfaction', '満足度'),
            ('other_school', '他塾への変更'),
            ('other', 'その他'),
        ],
        default='other'
    )
    reason_detail = models.TextField('理由詳細', blank=True)

    # 返金関連
    refund_amount = models.DecimalField(
        '返金額',
        max_digits=10,
        decimal_places=0,
        null=True, blank=True
    )
    refund_calculated = models.BooleanField('返金額計算済', default=False)
    remaining_tickets = models.IntegerField('残チケット数', null=True, blank=True)

    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # 申請者情報
    requested_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='withdrawal_requests',
        verbose_name='申請者'
    )
    requested_at = models.DateTimeField('申請日時', auto_now_add=True)

    # 処理者情報
    processed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='processed_withdrawal_requests',
        verbose_name='処理者'
    )
    processed_at = models.DateTimeField('処理日時', null=True, blank=True)
    process_notes = models.TextField('処理メモ', blank=True)

    class Meta:
        db_table = 't14_withdrawal_requests'
        verbose_name = 'T14_退会申請'
        verbose_name_plural = 'T14_退会申請'
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.student} - {self.withdrawal_date} ({self.get_status_display()})"

    def approve(self, user, notes=''):
        """退会申請を承認"""
        from django.utils import timezone
        self.status = self.Status.APPROVED
        self.processed_by = user
        self.processed_at = timezone.now()
        self.process_notes = notes
        self.save()

        # 生徒ステータスを退会に変更
        self.student.status = Student.Status.WITHDRAWN
        self.student.save()

        # StudentEnrollmentを退会に更新
        StudentEnrollment.objects.filter(
            student=self.student,
            brand=self.brand,
            end_date__isnull=True
        ).update(
            status=StudentEnrollment.Status.WITHDRAWN,
            end_date=self.withdrawal_date
        )

        # StudentSchoolを終了に更新
        StudentSchool.objects.filter(
            student=self.student,
            brand=self.brand,
            enrollment_status=StudentSchool.EnrollmentStatus.ACTIVE
        ).update(
            enrollment_status=StudentSchool.EnrollmentStatus.ENDED,
            end_date=self.withdrawal_date
        )
