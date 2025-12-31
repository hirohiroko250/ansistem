"""
Student Relations Models - 生徒関連モデル
StudentSchool, StudentEnrollment, StudentGuardian
"""
import uuid
from django.db import models
from apps.core.models import TenantModel

from .student import Student
from .guardian import Guardian


class StudentSchool(TenantModel):
    """T10: 生徒所属（校舎紐付け）"""

    class EnrollmentStatus(models.TextChoices):
        ACTIVE = 'active', '在籍中'
        TRANSFERRED = 'transferred', '転籍'
        ENDED = 'ended', '終了'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='school_enrollments',
        verbose_name='生徒'
    )
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='student_enrollments',
        verbose_name='校舎'
    )
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.CASCADE,
        related_name='student_enrollments',
        verbose_name='ブランド'
    )

    enrollment_status = models.CharField(
        '在籍状況',
        max_length=20,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ACTIVE
    )
    start_date = models.DateField('開始日')
    end_date = models.DateField('終了日', null=True, blank=True)
    is_primary = models.BooleanField('主所属', default=False)
    notes = models.TextField('備考', blank=True)

    # 授業スケジュール情報
    class_schedule = models.ForeignKey(
        'schools.ClassSchedule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_school_enrollments',
        verbose_name='クラススケジュール'
    )
    day_of_week = models.IntegerField(
        '曜日',
        null=True,
        blank=True,
        choices=[(1, '月'), (2, '火'), (3, '水'), (4, '木'), (5, '金'), (6, '土'), (7, '日')]
    )
    start_time = models.TimeField('開始時間', null=True, blank=True)
    end_time = models.TimeField('終了時間', null=True, blank=True)

    class Meta:
        db_table = 't10_student_schools'
        verbose_name = '生徒所属'
        verbose_name_plural = '生徒所属'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.student} - {self.school}"

    @property
    def day_of_week_display(self):
        """曜日の表示用"""
        days = {1: '月', 2: '火', 3: '水', 4: '木', 5: '金', 6: '土', 7: '日'}
        return days.get(self.day_of_week, '')


class StudentEnrollment(TenantModel):
    """T12: 生徒受講履歴（クラス・曜日変更の履歴管理）

    生徒の入会、クラス変更、曜日変更、休会、退会などの履歴を追跡するためのモデル。
    チケット購入時やクラス変更時に新しいレコードが作成される。
    現在有効なレコードはend_dateがNULLのもの。
    """

    class Status(models.TextChoices):
        TRIAL = 'trial', '体験'
        ENROLLED = 'enrolled', '入会中'
        SUSPENDED = 'suspended', '休会中'
        WITHDRAWN = 'withdrawn', '退会'

    class ChangeType(models.TextChoices):
        NEW_ENROLLMENT = 'new', '新規入会'
        TRIAL = 'trial', '体験'
        CLASS_CHANGE = 'class_change', 'クラス変更'
        SCHOOL_CHANGE = 'school_change', '校舎変更'
        SCHEDULE_CHANGE = 'schedule_change', '曜日・時間変更'
        SUSPEND = 'suspend', '休会'
        RESUME = 'resume', '復会'
        WITHDRAW = 'withdraw', '退会'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 生徒
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name='生徒'
    )

    # 所属情報
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='student_enrollments_history',
        verbose_name='校舎'
    )
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.CASCADE,
        related_name='student_enrollments_history',
        verbose_name='ブランド'
    )

    # クラス・スケジュール情報
    class_schedule = models.ForeignKey(
        'schools.ClassSchedule',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='student_enrollments',
        verbose_name='クラススケジュール'
    )

    # チケット関連（消化記号で振替判定）
    ticket = models.ForeignKey(
        'contracts.Ticket',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='student_enrollments',
        verbose_name='チケット'
    )

    # 曜日・時間帯（クラススケジュールから取得されるが、履歴として保存）
    day_of_week = models.IntegerField(
        '曜日',
        null=True, blank=True,
        help_text='0:月曜 〜 6:日曜'
    )
    start_time = models.TimeField('開始時間', null=True, blank=True)
    end_time = models.TimeField('終了時間', null=True, blank=True)

    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.ENROLLED
    )

    # 変更種別
    change_type = models.CharField(
        '変更種別',
        max_length=20,
        choices=ChangeType.choices,
        default=ChangeType.NEW_ENROLLMENT
    )

    # 有効期間
    effective_date = models.DateField('適用開始日')
    end_date = models.DateField('終了日', null=True, blank=True)

    # 前のレコードへの参照（変更履歴をチェーンする）
    previous_enrollment = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='next_enrollment',
        verbose_name='前の受講記録'
    )

    # 関連StudentItem（購入履歴との紐付け）
    student_item = models.ForeignKey(
        'contracts.StudentItem',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='enrollments',
        verbose_name='購入明細'
    )

    # メタ情報
    notes = models.TextField('備考', blank=True)
    metadata = models.JSONField('メタデータ', default=dict, blank=True)

    class Meta:
        db_table = 't12_student_enrollments'
        verbose_name = 'T12_生徒受講履歴'
        verbose_name_plural = 'T12_生徒受講履歴'
        ordering = ['-effective_date', '-created_at']
        indexes = [
            models.Index(fields=['student', 'end_date']),
            models.Index(fields=['school', 'brand']),
            models.Index(fields=['effective_date']),
        ]

    def __str__(self):
        return f"{self.student} - {self.school} ({self.get_change_type_display()})"

    @classmethod
    def get_current_enrollment(cls, student, brand=None):
        """生徒の現在有効な受講記録を取得"""
        queryset = cls.objects.filter(
            student=student,
            end_date__isnull=True,
            status__in=[cls.Status.ENROLLED, cls.Status.TRIAL]
        )
        if brand:
            queryset = queryset.filter(brand=brand)
        return queryset.first()

    @classmethod
    def create_enrollment(cls, student, school, brand, class_schedule=None,
                         ticket=None, change_type=None, effective_date=None,
                         student_item=None, notes='',
                         day_of_week_override=None, start_time_override=None, end_time_override=None):
        """新しい受講記録を作成し、前の記録を終了する

        Args:
            student: 生徒
            school: 校舎
            brand: ブランド
            class_schedule: クラススケジュール（optional）
            ticket: チケット（optional）
            change_type: 変更種別
            effective_date: 適用開始日
            student_item: 購入明細（optional）
            notes: 備考
            day_of_week_override: 曜日（class_scheduleがない場合に使用）
            start_time_override: 開始時間（class_scheduleがない場合に使用）
            end_time_override: 終了時間（class_scheduleがない場合に使用）
        """
        from datetime import date as date_cls
        effective_date = effective_date or date_cls.today()

        # 同じブランドの現在有効な記録を終了
        current = cls.get_current_enrollment(student, brand)
        if current:
            current.end_date = effective_date
            current.save()

        # 曜日・時間情報を取得（class_scheduleから取得、なければoverride値を使用）
        day_of_week = None
        start_time = None
        end_time = None
        if class_schedule:
            day_of_week = class_schedule.day_of_week
            if hasattr(class_schedule, 'time_slot') and class_schedule.time_slot:
                start_time = class_schedule.time_slot.start_time
                end_time = class_schedule.time_slot.end_time

        # class_scheduleがない場合、またはclass_scheduleから取得できなかった場合はoverride値を使用
        if day_of_week is None and day_of_week_override is not None:
            day_of_week = day_of_week_override
        if start_time is None and start_time_override is not None:
            start_time = start_time_override
        if end_time is None and end_time_override is not None:
            end_time = end_time_override

        return cls.objects.create(
            tenant_id=student.tenant_id,
            student=student,
            school=school,
            brand=brand,
            class_schedule=class_schedule,
            ticket=ticket,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            status=cls.Status.ENROLLED,
            change_type=change_type or cls.ChangeType.NEW_ENROLLMENT,
            effective_date=effective_date,
            previous_enrollment=current,
            student_item=student_item,
            notes=notes,
        )


class StudentGuardian(TenantModel):
    """T11: 生徒保護者関連"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='guardian_relations',
        verbose_name='生徒'
    )
    guardian = models.ForeignKey(
        Guardian,
        on_delete=models.CASCADE,
        related_name='student_relations',
        verbose_name='保護者'
    )
    relationship = models.CharField(
        '続柄',
        max_length=20,
        choices=Guardian.Relationship.choices,
        default=Guardian.Relationship.OTHER
    )
    is_primary = models.BooleanField('主保護者', default=False)
    is_emergency_contact = models.BooleanField('緊急連絡先', default=False)
    is_billing_target = models.BooleanField('請求先', default=False)
    contact_priority = models.IntegerField('連絡優先順位', default=1)
    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't11_student_guardians'
        verbose_name = '生徒保護者関連'
        verbose_name_plural = '生徒保護者関連'
        ordering = ['contact_priority']
        unique_together = ['student', 'guardian']

    def __str__(self):
        return f"{self.student} - {self.guardian} ({self.get_relationship_display()})"
