"""
Lessons Models
授業スケジュール・出欠・振替管理
"""
import uuid
from django.db import models
from django.conf import settings
from apps.core.models import TenantModel


class TimeSlot(TenantModel):
    """T15: 時間割"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slot_code = models.CharField('時限コード', max_length=10)
    slot_name = models.CharField('時限名', max_length=50)
    start_time = models.TimeField('開始時刻')
    end_time = models.TimeField('終了時刻')
    duration_minutes = models.IntegerField('時間（分）', default=60)
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='time_slots',
        verbose_name='校舎',
        null=True,
        blank=True
    )
    day_of_week = models.IntegerField('曜日', null=True, blank=True)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't15_time_slots'
        verbose_name = '時間割'
        verbose_name_plural = '時間割'
        ordering = ['sort_order', 'start_time']

    def __str__(self):
        return f"{self.slot_name} ({self.start_time}-{self.end_time})"


class LessonSchedule(TenantModel):
    """T13: 授業スケジュール"""

    class LessonType(models.TextChoices):
        INDIVIDUAL = 'individual', '個別指導'
        GROUP = 'group', '集団授業'
        ONLINE = 'online', 'オンライン'
        SELF_STUDY = 'self_study', '自習'

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', '予定'
        CONFIRMED = 'confirmed', '確定'
        IN_PROGRESS = 'in_progress', '実施中'
        COMPLETED = 'completed', '完了'
        CANCELLED = 'cancelled', 'キャンセル'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='lesson_schedules',
        verbose_name='校舎'
    )
    classroom = models.ForeignKey(
        'schools.Classroom',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_schedules',
        verbose_name='教室'
    )
    subject = models.ForeignKey(
        'schools.Subject',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_schedules',
        verbose_name='教科'
    )
    lesson_type = models.CharField(
        '授業種別',
        max_length=20,
        choices=LessonType.choices,
        default=LessonType.INDIVIDUAL
    )
    date = models.DateField('日付')
    time_slot = models.ForeignKey(
        TimeSlot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_schedules',
        verbose_name='時間割'
    )
    start_time = models.TimeField('開始時刻')
    end_time = models.TimeField('終了時刻')
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_schedules_as_teacher',
        verbose_name='講師'
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='lesson_schedules',
        verbose_name='生徒'
    )
    contract = models.ForeignKey(
        'contracts.Contract',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_schedules',
        verbose_name='契約'
    )
    # 契約詳細へのリンク用UUIDフィールド (contract_detail_idとして保存)
    contract_detail_id = models.UUIDField(
        '契約詳細ID',
        null=True,
        blank=True
    )
    class_name = models.CharField('クラス名', max_length=100, blank=True)
    capacity = models.IntegerField('定員', null=True, blank=True)
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED
    )
    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't13_lesson_schedules'
        verbose_name = '授業スケジュール'
        verbose_name_plural = '授業スケジュール'
        ordering = ['date', 'start_time']

    def __str__(self):
        student_name = self.student.full_name if self.student else '未定'
        return f"{self.date} {self.start_time} - {student_name}"


class LessonRecord(TenantModel):
    """T14: 授業実績"""

    class EvaluationLevel(models.TextChoices):
        EXCELLENT = 'excellent', '優秀'
        GOOD = 'good', '良好'
        AVERAGE = 'average', '普通'
        BELOW_AVERAGE = 'below_average', 'やや不足'
        POOR = 'poor', '要改善'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule = models.OneToOneField(
        LessonSchedule,
        on_delete=models.CASCADE,
        related_name='record',
        verbose_name='スケジュール'
    )
    actual_start_time = models.TimeField('実開始時刻', null=True, blank=True)
    actual_end_time = models.TimeField('実終了時刻', null=True, blank=True)
    actual_duration_minutes = models.IntegerField('実時間（分）', null=True, blank=True)
    content = models.TextField('授業内容', blank=True)
    homework = models.TextField('宿題', blank=True)
    next_lesson_plan = models.TextField('次回予定', blank=True)
    understanding_level = models.CharField(
        '理解度',
        max_length=20,
        choices=EvaluationLevel.choices,
        blank=True
    )
    attitude_evaluation = models.CharField(
        '態度評価',
        max_length=20,
        choices=EvaluationLevel.choices,
        blank=True
    )
    homework_status = models.CharField(
        '宿題状況',
        max_length=20,
        choices=EvaluationLevel.choices,
        blank=True
    )
    teacher_comment = models.TextField('講師コメント', blank=True)
    internal_memo = models.TextField('内部メモ', blank=True)
    recorded_at = models.DateTimeField('記録日時', auto_now_add=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_records',
        verbose_name='記録者'
    )

    class Meta:
        db_table = 't14_lesson_records'
        verbose_name = '授業実績'
        verbose_name_plural = '授業実績'

    def __str__(self):
        return f"授業実績: {self.schedule}"


class Attendance(TenantModel):
    """T19: 出席記録"""

    class Status(models.TextChoices):
        PRESENT = 'present', '出席'
        ABSENT = 'absent', '欠席'
        LATE = 'late', '遅刻'
        EARLY_LEAVE = 'early_leave', '早退'
        ABSENT_NOTICE = 'absent_notice', '欠席（連絡あり）'
        MAKEUP = 'makeup', '振替'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule = models.ForeignKey(
        LessonSchedule,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name='スケジュール'
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name='生徒'
    )
    status = models.CharField(
        '出席状況',
        max_length=20,
        choices=Status.choices,
        default=Status.PRESENT
    )
    check_in_time = models.TimeField('入室時刻', null=True, blank=True)
    check_out_time = models.TimeField('退室時刻', null=True, blank=True)
    absence_reason = models.TextField('欠席理由', blank=True)
    absence_notified_at = models.DateTimeField('欠席連絡日時', null=True, blank=True)
    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't19_attendances'
        verbose_name = '出席記録'
        verbose_name_plural = '出席記録'
        unique_together = ['schedule', 'student']

    def __str__(self):
        return f"{self.student} - {self.schedule.date} - {self.get_status_display()}"


class MakeupLesson(TenantModel):
    """T20: 振替"""

    class Status(models.TextChoices):
        REQUESTED = 'requested', '申請中'
        APPROVED = 'approved', '承認'
        SCHEDULED = 'scheduled', '予定確定'
        COMPLETED = 'completed', '完了'
        REJECTED = 'rejected', '却下'
        CANCELLED = 'cancelled', 'キャンセル'
        EXPIRED = 'expired', '期限切れ'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_schedule = models.ForeignKey(
        LessonSchedule,
        on_delete=models.CASCADE,
        related_name='makeup_from',
        verbose_name='元スケジュール'
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='makeup_lessons',
        verbose_name='生徒'
    )
    makeup_schedule = models.ForeignKey(
        LessonSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='makeup_to',
        verbose_name='振替先スケジュール'
    )
    preferred_date = models.DateField('希望日', null=True, blank=True)
    preferred_time_slot = models.ForeignKey(
        TimeSlot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='makeup_requests',
        verbose_name='希望時間割'
    )
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.REQUESTED
    )
    valid_until = models.DateField('有効期限', null=True, blank=True)
    requested_at = models.DateTimeField('申請日時', auto_now_add=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='makeup_requests',
        verbose_name='申請者'
    )
    processed_at = models.DateTimeField('処理日時', null=True, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='makeup_processed',
        verbose_name='処理者'
    )
    reason = models.TextField('振替理由', blank=True)
    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't20_makeup_lessons'
        verbose_name = '振替'
        verbose_name_plural = '振替'
        ordering = ['-requested_at']

    def __str__(self):
        return f"振替: {self.student} - {self.original_schedule.date}"


class GroupLessonEnrollment(TenantModel):
    """T13a: 集団授業受講者"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule = models.ForeignKey(
        LessonSchedule,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name='スケジュール'
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='group_enrollments',
        verbose_name='生徒'
    )
    enrolled_at = models.DateTimeField('登録日時', auto_now_add=True)

    class Meta:
        db_table = 't13_group_enrollments'
        verbose_name = '集団授業受講者'
        verbose_name_plural = '集団授業受講者'
        unique_together = ['schedule', 'student']

    def __str__(self):
        return f"{self.student} - {self.schedule}"


class AbsenceTicket(TenantModel):
    """欠席チケット

    欠席登録時に発行され、振替予約に使用される。
    消化記号(consumption_symbol)を基準に振替可能なクラスを判定する。
    """

    class Status(models.TextChoices):
        ISSUED = 'issued', '発行済'
        USED = 'used', '使用済'
        EXPIRED = 'expired', '期限切れ'
        CANCELLED = 'cancelled', 'キャンセル'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='absence_tickets',
        verbose_name='生徒'
    )
    original_ticket = models.ForeignKey(
        'contracts.Ticket',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='absence_tickets',
        verbose_name='元チケット'
    )
    consumption_symbol = models.CharField(
        '消化記号',
        max_length=20,
        blank=True,
        help_text='振替対象を判定するための消化記号'
    )
    absence_date = models.DateField('欠席日')
    class_schedule = models.ForeignKey(
        'schools.ClassSchedule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='absence_tickets',
        verbose_name='欠席した授業'
    )
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.ISSUED
    )
    used_date = models.DateField('使用日', null=True, blank=True)
    used_class_schedule = models.ForeignKey(
        'schools.ClassSchedule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='used_absence_tickets',
        verbose_name='振替先授業'
    )
    valid_until = models.DateField('有効期限')
    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't_absence_tickets'
        verbose_name = '欠席チケット'
        verbose_name_plural = '欠席チケット'
        ordering = ['-absence_date']

    def __str__(self):
        return f"欠席チケット: {self.student} - {self.absence_date} ({self.get_status_display()})"
