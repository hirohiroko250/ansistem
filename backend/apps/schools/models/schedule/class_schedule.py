"""
ClassSchedule Model - 開講時間割
"""
import uuid
from django.db import models
from apps.core.models import TenantModel

from apps.schools.models.brand import Brand, BrandCategory
from apps.schools.models.school import School
from apps.schools.models.grade import Grade
from apps.schools.models.classroom import Classroom


class ClassSchedule(TenantModel):
    """T14c: 開講時間割（クラス登録・振替のベースとなるマスタ）

    エクセル「T14_開講時間割_ 時間割Group版」に対応
    校舎×ブランド×曜日×時限でクラスを定義
    """

    class DayOfWeek(models.IntegerChoices):
        MONDAY = 1, '月曜日'
        TUESDAY = 2, '火曜日'
        WEDNESDAY = 3, '水曜日'
        THURSDAY = 4, '木曜日'
        FRIDAY = 5, '金曜日'
        SATURDAY = 6, '土曜日'
        SUNDAY = 7, '日曜日'

    class ApprovalType(models.IntegerChoices):
        AUTO = 1, '自動承認'
        MANUAL = 2, '承認制'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 時間割ID（エクセルの「社内時間割ID」に対応）
    schedule_code = models.CharField(
        '時間割コード',
        max_length=50,
        help_text='例: 尾張旭月4_Ti10000025'
    )

    # 基本情報
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='class_schedules',
        verbose_name='校舎'
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name='class_schedules',
        verbose_name='ブランド'
    )
    brand_category = models.ForeignKey(
        BrandCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='class_schedules',
        verbose_name='ブランドカテゴリ'
    )

    # 曜日・時間
    day_of_week = models.IntegerField(
        '曜日',
        choices=DayOfWeek.choices
    )
    period = models.IntegerField(
        '時限',
        help_text='1, 2, 3...（V表示時限）'
    )
    start_time = models.TimeField('開始時間')
    duration_minutes = models.IntegerField(
        '授業時間（分）',
        default=50
    )
    end_time = models.TimeField('終了時間')
    break_time = models.TimeField(
        '休憩時間',
        null=True,
        blank=True,
        help_text='当日の休憩時間'
    )

    # クラス情報
    class_name = models.CharField(
        'クラス名',
        max_length=100,
        help_text='例: Purple ペア'
    )
    class_type = models.CharField(
        'クラス種名',
        max_length=50,
        blank=True,
        help_text='例: Purpleペア'
    )

    # 保護者向け表示
    display_course_name = models.CharField(
        '保護者用コース名',
        max_length=200,
        blank=True,
        help_text='例: ④小５以上(英語歴5年以上)'
    )
    display_pair_name = models.CharField(
        '保護者用ペア名',
        max_length=100,
        blank=True,
        help_text='例: Purple_ペア'
    )
    display_description = models.TextField(
        '保護者用説明',
        blank=True,
        help_text='例: 【通称】:Purpleクラス【対象】④小５以上...'
    )

    # チケット関連
    ticket_name = models.CharField(
        'チケット名',
        max_length=100,
        blank=True,
        help_text='例: Purple ペア　50分×週1回'
    )
    ticket_id = models.CharField(
        'チケットID',
        max_length=50,
        blank=True,
        help_text='例: Ti10000025'
    )

    # 振替・グループ
    transfer_group = models.CharField(
        '振替グループ',
        max_length=50,
        blank=True,
        help_text='同じグループ内で振替可能'
    )
    schedule_group = models.CharField(
        '時間割グループ',
        max_length=50,
        blank=True
    )

    # 席数・定員
    capacity = models.IntegerField('定員', default=12)
    trial_capacity = models.IntegerField('体験受入可能数', default=2)
    reserved_seats = models.IntegerField('予約済み席数', default=0)
    pause_seat_fee = models.DecimalField(
        '休会時座席料金',
        max_digits=10,
        decimal_places=0,
        default=0
    )

    # カレンダーマスター参照
    calendar_master = models.ForeignKey(
        'schools.CalendarMaster',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='class_schedules_t14c',
        verbose_name='カレンダーマスター'
    )

    # カレンダーパターン（後方互換用）
    calendar_pattern = models.CharField(
        'カレンダーパターン',
        max_length=50,
        blank=True,
        help_text='例: 1003_AEC_P'
    )

    # 承認設定
    approval_type = models.IntegerField(
        '承認種別',
        choices=ApprovalType.choices,
        default=ApprovalType.AUTO
    )

    # 教室
    room = models.ForeignKey(
        Classroom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='class_schedules',
        verbose_name='教室'
    )
    room_name = models.CharField(
        '教室名',
        max_length=50,
        blank=True,
        help_text='Roomマスタにない場合の教室名'
    )

    # 期間
    display_start_date = models.DateField(
        '保護者表示開始日',
        null=True,
        blank=True
    )
    class_start_date = models.DateField(
        'クラス開始日',
        null=True,
        blank=True
    )
    class_end_date = models.DateField(
        'クラス終了日',
        null=True,
        blank=True
    )

    # 対象学年
    grade = models.ForeignKey(
        Grade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='class_schedules',
        verbose_name='対象学年'
    )

    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't14c_class_schedules'
        verbose_name = 'T14c_開講時間割'
        verbose_name_plural = 'T14c_開講時間割'
        ordering = ['school', 'brand_category', 'brand', 'day_of_week', 'period']
        unique_together = ['tenant_id', 'schedule_code']

    def __str__(self):
        return f"{self.school.school_name} {self.get_day_of_week_display()} {self.period}限 {self.class_name}"

    @property
    def active_student_count(self):
        """在籍中の生徒数（リアルタイム計算）"""
        from apps.students.models import StudentSchool
        return StudentSchool.objects.filter(
            class_schedule=self,
            enrollment_status=StudentSchool.EnrollmentStatus.ACTIVE
        ).count()

    @property
    def available_seats(self):
        """空き席数（リアルタイム計算）"""
        return max(0, self.capacity - self.active_student_count)

    def is_available(self):
        """予約可能かどうか"""
        return self.is_active and self.available_seats > 0

    def is_transfer_compatible(self, other):
        """振替可能かどうか（同じ振替グループ内）"""
        if not self.transfer_group or not other.transfer_group:
            return False
        return self.transfer_group == other.transfer_group
