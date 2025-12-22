"""
Students Models
T1: 生徒マスタ
T2: 保護者マスタ
T10: 生徒所属（校舎紐付け）
T11: 生徒保護者関連
"""
import uuid
from django.db import models
from apps.core.models import TenantModel


class Student(TenantModel):
    """T1: 生徒マスタ"""

    class Status(models.TextChoices):
        REGISTERED = 'registered', '登録のみ'
        TRIAL = 'trial', '体験'
        ENROLLED = 'enrolled', '入会'
        SUSPENDED = 'suspended', '休会'
        WITHDRAWN = 'withdrawn', '退会'

    class Gender(models.TextChoices):
        MALE = 'male', '男性'
        FEMALE = 'female', '女性'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student_no = models.CharField('生徒番号', max_length=20, blank=True)
    old_id = models.CharField('旧システムID', max_length=50, blank=True, db_index=True)

    @classmethod
    def generate_student_no(cls):
        """2で始まる7桁の生徒番号を自動生成（2XXXXXX）"""
        import random
        while True:
            # 2で始まる7桁の数字を生成（2000000〜2999999）
            student_no = str(random.randint(2000000, 2999999))
            # 既存の番号と旧システムIDの両方と重複しないかチェック
            if not cls.objects.filter(student_no=student_no).exists() and \
               not cls.objects.filter(old_id=student_no).exists():
                return student_no

    def save(self, *args, **kwargs):
        # 新規作成時にstudent_noが空なら自動発番
        if not self.student_no:
            self.student_no = self.generate_student_no()
        super().save(*args, **kwargs)

    # 基本情報
    last_name = models.CharField('姓', max_length=50)
    first_name = models.CharField('名', max_length=50)
    last_name_kana = models.CharField('姓（カナ）', max_length=50, blank=True)
    first_name_kana = models.CharField('名（カナ）', max_length=50, blank=True)
    last_name_roman = models.CharField('姓（ローマ字）', max_length=50, blank=True)
    first_name_roman = models.CharField('名（ローマ字）', max_length=50, blank=True)
    nickname = models.CharField('ニックネーム', max_length=50, blank=True)
    display_name = models.CharField('表示名', max_length=100, blank=True)

    # 連絡先
    email = models.EmailField('メールアドレス', blank=True)
    phone = models.CharField('電話番号', max_length=20, blank=True)
    phone2 = models.CharField('電話番号2', max_length=20, blank=True)
    line_id = models.CharField('LINE ID', max_length=50, blank=True)

    # 住所
    postal_code = models.CharField('郵便番号', max_length=8, blank=True)
    prefecture = models.CharField('都道府県', max_length=10, blank=True)
    city = models.CharField('市区町村', max_length=50, blank=True)
    address1 = models.CharField('住所1', max_length=100, blank=True)
    address2 = models.CharField('住所2', max_length=100, blank=True)

    # 属性
    birth_date = models.DateField('生年月日', null=True, blank=True)
    gender = models.CharField('性別', max_length=10, choices=Gender.choices, blank=True)
    profile_image_url = models.URLField('プロフィール画像URL', blank=True)

    # 学校情報
    school_name = models.CharField('在籍学校名', max_length=100, blank=True)
    school_type = models.CharField('学校種別', max_length=20, blank=True)  # 公立, 私立等
    grade = models.ForeignKey(
        'schools.Grade',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='students',
        verbose_name='学年マスタ'
    )
    grade_text = models.CharField('学年（テキスト）', max_length=50, blank=True)  # 小学3年生など
    grade_updated_at = models.DateField('学年更新日', null=True, blank=True)

    # 主所属（体験時に設定）
    primary_school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='primary_students',
        verbose_name='主所属校舎'
    )
    primary_brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='primary_students',
        verbose_name='主所属ブランド'
    )

    # 所属ブランド（複数、タグ形式）
    brands = models.ManyToManyField(
        'schools.Brand',
        blank=True,
        related_name='students',
        verbose_name='所属ブランド'
    )

    # ユーザーアカウント連携
    user = models.OneToOneField(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='student_profile',
        verbose_name='ユーザーアカウント'
    )

    # 主保護者（直接参照）
    guardian = models.ForeignKey(
        'Guardian',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='children',
        verbose_name='主保護者'
    )

    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.REGISTERED
    )
    contract_status = models.CharField('契約ステータス', max_length=10, blank=True)
    referrer_old_id = models.CharField('紹介者旧ID', max_length=50, blank=True)
    # ステータス日付
    registered_date = models.DateField('登録日', null=True, blank=True)
    trial_date = models.DateField('体験日', null=True, blank=True)
    enrollment_date = models.DateField('入会日', null=True, blank=True)
    suspended_date = models.DateField('休会日', null=True, blank=True)
    withdrawal_date = models.DateField('退会日', null=True, blank=True)
    withdrawal_reason = models.TextField('退会理由', blank=True)

    # メタ情報
    notes = models.TextField('備考', blank=True)
    tags = models.JSONField('タグ', default=list, blank=True)
    custom_fields = models.JSONField('カスタムフィールド', default=dict, blank=True)

    class Meta:
        db_table = 't02_students'
        verbose_name = 'T2_生徒'
        verbose_name_plural = 'T2_生徒'
        ordering = ['-created_at']
        unique_together = ['tenant_id', 'student_no']

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.student_no})"

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}"

    @property
    def full_name_kana(self):
        return f"{self.last_name_kana} {self.first_name_kana}"


class Guardian(TenantModel):
    """T2: 保護者マスタ"""

    class Relationship(models.TextChoices):
        FATHER = 'father', '父'
        MOTHER = 'mother', '母'
        GRANDFATHER = 'grandfather', '祖父'
        GRANDMOTHER = 'grandmother', '祖母'
        SIBLING = 'sibling', '兄弟姉妹'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    guardian_no = models.CharField('保護者番号', max_length=20, blank=True)
    old_id = models.CharField('旧システムID', max_length=50, blank=True, db_index=True)

    @classmethod
    def generate_guardian_no(cls):
        """8で始まる8桁の保護者番号を自動生成（8XXXXXXX）"""
        import random
        while True:
            # 8で始まる8桁の数字を生成（80000000〜89999999）
            guardian_no = str(random.randint(80000000, 89999999))
            # 既存の番号と旧システムIDの両方と重複しないかチェック
            if not cls.objects.filter(guardian_no=guardian_no).exists() and \
               not cls.objects.filter(old_id=guardian_no).exists():
                return guardian_no

    def save(self, *args, **kwargs):
        # 新規作成時にguardian_noが空なら自動発番
        if not self.guardian_no:
            self.guardian_no = self.generate_guardian_no()
        super().save(*args, **kwargs)

    # 基本情報
    last_name = models.CharField('姓', max_length=50)
    first_name = models.CharField('名', max_length=50)
    last_name_kana = models.CharField('姓（カナ）', max_length=50, blank=True)
    first_name_kana = models.CharField('名（カナ）', max_length=50, blank=True)
    last_name_roman = models.CharField('姓（ローマ字）', max_length=50, blank=True)
    first_name_roman = models.CharField('名（ローマ字）', max_length=50, blank=True)
    birth_date = models.DateField('生年月日', null=True, blank=True)

    # 連絡先
    email = models.EmailField('メールアドレス', blank=True)
    phone = models.CharField('電話番号', max_length=20, blank=True)
    phone_mobile = models.CharField('携帯電話', max_length=20, blank=True)
    line_id = models.CharField('LINE ID', max_length=50, blank=True)

    # 住所
    postal_code = models.CharField('郵便番号', max_length=8, blank=True)
    prefecture = models.CharField('都道府県', max_length=10, blank=True)
    city = models.CharField('市区町村', max_length=50, blank=True)
    address1 = models.CharField('住所1', max_length=100, blank=True)
    address2 = models.CharField('住所2', max_length=100, blank=True)

    # 勤務先
    workplace = models.CharField('勤務先', max_length=100, blank=True)
    workplace_phone = models.CharField('勤務先電話番号', max_length=20, blank=True)
    workplace2 = models.CharField('勤務先2', max_length=100, blank=True)
    workplace_phone2 = models.CharField('勤務先2電話番号', max_length=20, blank=True)

    # 支払い情報（銀行口座）
    bank_name = models.CharField('金融機関名', max_length=100, blank=True)
    bank_code = models.CharField('金融機関コード', max_length=4, blank=True)
    branch_name = models.CharField('支店名', max_length=100, blank=True)
    branch_code = models.CharField('支店コード', max_length=3, blank=True)
    account_type = models.CharField(
        '口座種別',
        max_length=10,
        choices=[('ordinary', '普通'), ('current', '当座'), ('savings', '貯蓄')],
        default='ordinary',
        blank=True
    )
    account_number = models.CharField('口座番号', max_length=8, blank=True)
    account_holder = models.CharField('口座名義', max_length=100, blank=True)
    account_holder_kana = models.CharField('口座名義（カナ）', max_length=100, blank=True)

    # 引き落とし設定
    withdrawal_day = models.IntegerField('引き落とし日', null=True, blank=True)  # 毎月何日
    payment_registered = models.BooleanField('支払い方法登録済み', default=False)
    payment_registered_at = models.DateTimeField('支払い方法登録日時', null=True, blank=True)

    # ユーザーアカウント連携
    user = models.OneToOneField(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='guardian_profile',
        verbose_name='ユーザーアカウント'
    )

    # 登録時追加情報
    nearest_school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='nearby_guardians',
        verbose_name='最寄り校舎'
    )
    interested_brands = models.JSONField('興味のあるブランド', default=list, blank=True)
    referral_source = models.CharField('紹介元', max_length=50, blank=True)
    expectations = models.TextField('期待・要望', blank=True)

    # メタ情報
    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't01_guardians'
        verbose_name = 'T1_保護者'
        verbose_name_plural = 'T1_保護者'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}"

    @property
    def full_name_kana(self):
        return f"{self.last_name_kana} {self.first_name_kana}".strip()


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


class TrialBooking(TenantModel):
    """体験予約（日時指定・人数管理）"""

    class Status(models.TextChoices):
        PENDING = 'pending', '予約待ち'
        CONFIRMED = 'confirmed', '確定'
        CANCELLED = 'cancelled', 'キャンセル'
        COMPLETED = 'completed', '完了'
        NO_SHOW = 'no_show', '無断欠席'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 誰が予約
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='trial_bookings',
        verbose_name='生徒'
    )
    guardian = models.ForeignKey(
        Guardian,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='trial_bookings',
        verbose_name='保護者'
    )

    # どこで
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='trial_bookings',
        verbose_name='校舎'
    )
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.CASCADE,
        related_name='trial_bookings',
        verbose_name='ブランド'
    )

    # いつ（日時指定）
    trial_date = models.DateField('体験日')
    schedule = models.ForeignKey(
        'schools.SchoolSchedule',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='trial_bookings',
        verbose_name='スケジュール枠'
    )
    time_slot = models.ForeignKey(
        'schools.TimeSlot',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='trial_bookings',
        verbose_name='時間帯'
    )

    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # 追加情報
    notes = models.TextField('備考', blank=True)
    confirmed_at = models.DateTimeField('確定日時', null=True, blank=True)
    cancelled_at = models.DateTimeField('キャンセル日時', null=True, blank=True)
    cancellation_reason = models.TextField('キャンセル理由', blank=True)

    # 関連タスク（UUIDで参照、循環参照回避）
    task_id_ref = models.UUIDField('関連タスクID', null=True, blank=True)

    class Meta:
        db_table = 't03_trial_bookings'
        verbose_name = 'T3_体験予約'
        verbose_name_plural = 'T3_体験予約'
        ordering = ['trial_date', 'created_at']
        # 同じ生徒が同じ日時に複数予約できないようにする
        unique_together = ['student', 'trial_date', 'schedule']

    def __str__(self):
        return f"{self.student} - {self.trial_date} {self.school.school_name}"

    @classmethod
    def get_booked_count(cls, schedule_id, trial_date):
        """指定スケジュール・日付の予約数を取得"""
        return cls.objects.filter(
            schedule_id=schedule_id,
            trial_date=trial_date,
            status__in=[cls.Status.PENDING, cls.Status.CONFIRMED]
        ).count()

    @classmethod
    def is_available(cls, schedule_id, trial_date, trial_capacity):
        """指定スケジュール・日付が予約可能か確認"""
        booked = cls.get_booked_count(schedule_id, trial_date)
        return booked < trial_capacity


# 欠席・振替チケット（students admin用Proxyモデル）
# 循環インポートを避けるためここで定義
from apps.lessons.models import AbsenceTicket as LessonsAbsenceTicket


class AbsenceTicket(LessonsAbsenceTicket):
    """欠席・振替チケット（生徒管理用）

    lessonsアプリのAbsenceTicketを継承したProxyモデル。
    これによりstudents adminセクションに表示される。
    """
    class Meta:
        proxy = True
        app_label = 'students'
        verbose_name = '欠席・振替チケット'
        verbose_name_plural = '欠席・振替チケット'


# =============================================================================
# 休会・退会申請 (SuspensionRequest, WithdrawalRequest)
# =============================================================================
# =============================================================================
# 銀行口座管理 (BankAccount, BankAccountChangeRequest)
# =============================================================================
class BankAccount(TenantModel):
    """T15: 銀行口座マスタ

    保護者の銀行口座情報を管理するモデル。
    承認済みの口座情報がGuardianモデルに反映される。
    """

    class AccountType(models.TextChoices):
        ORDINARY = 'ordinary', '普通'
        CURRENT = 'current', '当座'
        SAVINGS = 'savings', '貯蓄'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 保護者
    guardian = models.ForeignKey(
        Guardian,
        on_delete=models.CASCADE,
        related_name='bank_accounts',
        verbose_name='保護者'
    )

    # 銀行情報
    bank_name = models.CharField('金融機関名', max_length=100)
    bank_code = models.CharField('金融機関コード', max_length=4)
    branch_name = models.CharField('支店名', max_length=100)
    branch_code = models.CharField('支店コード', max_length=3)
    account_type = models.CharField(
        '口座種別',
        max_length=10,
        choices=AccountType.choices,
        default=AccountType.ORDINARY
    )
    account_number = models.CharField('口座番号', max_length=8)
    account_holder = models.CharField('口座名義', max_length=100)
    account_holder_kana = models.CharField('口座名義（カナ）', max_length=100)

    # ステータス
    is_primary = models.BooleanField('メイン口座', default=False)
    is_active = models.BooleanField('有効', default=True)
    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't15_bank_accounts'
        verbose_name = 'T15_銀行口座'
        verbose_name_plural = 'T15_銀行口座'
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"{self.guardian} - {self.bank_name} {self.branch_name} ({self.account_number})"

    def sync_to_guardian(self):
        """承認された口座情報をGuardianモデルに反映"""
        if self.is_primary:
            self.guardian.bank_name = self.bank_name
            self.guardian.bank_code = self.bank_code
            self.guardian.branch_name = self.branch_name
            self.guardian.branch_code = self.branch_code
            self.guardian.account_type = self.account_type
            self.guardian.account_number = self.account_number
            self.guardian.account_holder = self.account_holder
            self.guardian.account_holder_kana = self.account_holder_kana
            self.guardian.payment_registered = True
            from django.utils import timezone
            self.guardian.payment_registered_at = timezone.now()
            self.guardian.save()


class BankAccountChangeRequest(TenantModel):
    """T16: 銀行口座変更申請

    保護者からの銀行口座登録・変更申請を管理するモデル。
    申請後、スタッフが承認処理を行う。
    """

    class RequestType(models.TextChoices):
        NEW = 'new', '新規登録'
        UPDATE = 'update', '変更'
        DELETE = 'delete', '削除'

    class Status(models.TextChoices):
        PENDING = 'pending', '申請中'
        APPROVED = 'approved', '承認済'
        REJECTED = 'rejected', '却下'
        CANCELLED = 'cancelled', '取消'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 保護者
    guardian = models.ForeignKey(
        Guardian,
        on_delete=models.CASCADE,
        related_name='bank_account_requests',
        verbose_name='保護者'
    )

    # 既存口座（変更・削除の場合）
    existing_account = models.ForeignKey(
        BankAccount,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='change_requests',
        verbose_name='既存口座'
    )

    # 申請種別
    request_type = models.CharField(
        '申請種別',
        max_length=10,
        choices=RequestType.choices,
        default=RequestType.NEW
    )

    # 新しい銀行情報（新規・変更の場合）
    bank_name = models.CharField('金融機関名', max_length=100, blank=True)
    bank_code = models.CharField('金融機関コード', max_length=4, blank=True)
    branch_name = models.CharField('支店名', max_length=100, blank=True)
    branch_code = models.CharField('支店コード', max_length=3, blank=True)
    account_type = models.CharField(
        '口座種別',
        max_length=10,
        choices=BankAccount.AccountType.choices,
        default=BankAccount.AccountType.ORDINARY,
        blank=True
    )
    account_number = models.CharField('口座番号', max_length=8, blank=True)
    account_holder = models.CharField('口座名義', max_length=100, blank=True)
    account_holder_kana = models.CharField('口座名義（カナ）', max_length=100, blank=True)
    is_primary = models.BooleanField('メイン口座にする', default=True)

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
        related_name='bank_account_requests',
        verbose_name='申請者'
    )
    requested_at = models.DateTimeField('申請日時', auto_now_add=True)
    request_notes = models.TextField('申請メモ', blank=True)

    # 処理者情報
    processed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='processed_bank_account_requests',
        verbose_name='処理者'
    )
    processed_at = models.DateTimeField('処理日時', null=True, blank=True)
    process_notes = models.TextField('処理メモ', blank=True)

    class Meta:
        db_table = 't16_bank_account_requests'
        verbose_name = 'T16_銀行口座変更申請'
        verbose_name_plural = 'T16_銀行口座変更申請'
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.guardian} - {self.get_request_type_display()} ({self.get_status_display()})"

    def approve(self, user, notes=''):
        """銀行口座申請を承認"""
        from django.utils import timezone

        self.status = self.Status.APPROVED
        self.processed_by = user
        self.processed_at = timezone.now()
        self.process_notes = notes
        self.save()

        if self.request_type == self.RequestType.NEW:
            # 新規登録
            if self.is_primary:
                # 他のメイン口座を解除
                BankAccount.objects.filter(
                    guardian=self.guardian,
                    is_primary=True
                ).update(is_primary=False)

            account = BankAccount.objects.create(
                tenant_id=self.tenant_id,
                guardian=self.guardian,
                bank_name=self.bank_name,
                bank_code=self.bank_code,
                branch_name=self.branch_name,
                branch_code=self.branch_code,
                account_type=self.account_type,
                account_number=self.account_number,
                account_holder=self.account_holder,
                account_holder_kana=self.account_holder_kana,
                is_primary=self.is_primary,
            )
            # メイン口座ならGuardianに反映
            if self.is_primary:
                account.sync_to_guardian()
            return account

        elif self.request_type == self.RequestType.UPDATE:
            # 変更
            if self.existing_account:
                if self.is_primary:
                    # 他のメイン口座を解除
                    BankAccount.objects.filter(
                        guardian=self.guardian,
                        is_primary=True
                    ).exclude(id=self.existing_account.id).update(is_primary=False)

                self.existing_account.bank_name = self.bank_name
                self.existing_account.bank_code = self.bank_code
                self.existing_account.branch_name = self.branch_name
                self.existing_account.branch_code = self.branch_code
                self.existing_account.account_type = self.account_type
                self.existing_account.account_number = self.account_number
                self.existing_account.account_holder = self.account_holder
                self.existing_account.account_holder_kana = self.account_holder_kana
                self.existing_account.is_primary = self.is_primary
                self.existing_account.save()

                # メイン口座ならGuardianに反映
                if self.is_primary:
                    self.existing_account.sync_to_guardian()
                return self.existing_account

        elif self.request_type == self.RequestType.DELETE:
            # 削除
            if self.existing_account:
                was_primary = self.existing_account.is_primary
                self.existing_account.is_active = False
                self.existing_account.is_primary = False
                self.existing_account.save()

                # メイン口座だった場合、Guardianの情報をクリア
                if was_primary:
                    self.guardian.bank_name = ''
                    self.guardian.bank_code = ''
                    self.guardian.branch_name = ''
                    self.guardian.branch_code = ''
                    self.guardian.account_type = 'ordinary'
                    self.guardian.account_number = ''
                    self.guardian.account_holder = ''
                    self.guardian.account_holder_kana = ''
                    self.guardian.payment_registered = False
                    self.guardian.payment_registered_at = None
                    self.guardian.save()

        return None

    def reject(self, user, notes=''):
        """銀行口座申請を却下"""
        from django.utils import timezone
        self.status = self.Status.REJECTED
        self.processed_by = user
        self.processed_at = timezone.now()
        self.process_notes = notes
        self.save()


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


# =============================================================================
# FS割引（友達紹介割引）
# =============================================================================
class FriendshipRegistration(TenantModel):
    """T17: 友達登録（FS登録）

    保護者間の友達関係を管理するモデル。
    両方向の関係が成立した場合にFS割引が適用される。
    """

    class Status(models.TextChoices):
        PENDING = 'pending', '申請中'
        ACCEPTED = 'accepted', '承認済'
        REJECTED = 'rejected', '拒否'
        CANCELLED = 'cancelled', '取消'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 申請者（友達登録を申請した保護者）
    requester = models.ForeignKey(
        Guardian,
        on_delete=models.CASCADE,
        related_name='friendship_requests_sent',
        verbose_name='申請者'
    )

    # 対象者（友達登録を受けた保護者）
    target = models.ForeignKey(
        Guardian,
        on_delete=models.CASCADE,
        related_name='friendship_requests_received',
        verbose_name='対象者'
    )

    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # 申請日時
    requested_at = models.DateTimeField('申請日時', auto_now_add=True)

    # 承認日時
    accepted_at = models.DateTimeField('承認日時', null=True, blank=True)

    # 友達コード（紹介コード）
    friend_code = models.CharField('友達コード', max_length=20, blank=True,
                                   help_text='紹介時に使用するコード')

    # 備考
    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't17_friendship_registrations'
        verbose_name = 'T17_友達登録'
        verbose_name_plural = 'T17_友達登録'
        ordering = ['-requested_at']
        # 同じペアの重複登録を防止
        unique_together = ['requester', 'target']

    def __str__(self):
        return f"{self.requester} → {self.target} ({self.get_status_display()})"

    def accept(self):
        """友達登録を承認"""
        from django.utils import timezone
        self.status = self.Status.ACCEPTED
        self.accepted_at = timezone.now()
        self.save()

        # 両者にFS割引を適用
        FSDiscount.apply_discount(self.requester, self)
        FSDiscount.apply_discount(self.target, self)

    def reject(self):
        """友達登録を拒否"""
        self.status = self.Status.REJECTED
        self.save()

    @classmethod
    def are_friends(cls, guardian1, guardian2):
        """2人の保護者が友達関係にあるか確認"""
        return cls.objects.filter(
            models.Q(requester=guardian1, target=guardian2) |
            models.Q(requester=guardian2, target=guardian1),
            status=cls.Status.ACCEPTED
        ).exists()

    @classmethod
    def get_friends(cls, guardian):
        """保護者の友達リストを取得"""
        # 承認済みの友達関係を取得
        sent = cls.objects.filter(
            requester=guardian,
            status=cls.Status.ACCEPTED
        ).values_list('target_id', flat=True)

        received = cls.objects.filter(
            target=guardian,
            status=cls.Status.ACCEPTED
        ).values_list('requester_id', flat=True)

        friend_ids = list(sent) + list(received)
        return Guardian.objects.filter(id__in=friend_ids)


class FSDiscount(TenantModel):
    """T18: FS割引（友達紹介割引）

    友達登録が成立した保護者に適用される割引を管理するモデル。
    両者に同じ割引が適用される。
    """

    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', '割合割引'
        FIXED = 'fixed', '固定額割引'
        MONTHS_FREE = 'months_free', '月謝無料'

    class Status(models.TextChoices):
        ACTIVE = 'active', '有効'
        USED = 'used', '使用済'
        EXPIRED = 'expired', '期限切れ'
        CANCELLED = 'cancelled', '取消'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 対象保護者
    guardian = models.ForeignKey(
        Guardian,
        on_delete=models.CASCADE,
        related_name='fs_discounts',
        verbose_name='保護者'
    )

    # 関連する友達登録
    friendship = models.ForeignKey(
        FriendshipRegistration,
        on_delete=models.CASCADE,
        related_name='discounts',
        verbose_name='友達登録'
    )

    # 割引タイプ
    discount_type = models.CharField(
        '割引タイプ',
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.FIXED
    )

    # 割引値（タイプによって解釈が異なる）
    # percentage: 割引率（例: 10 = 10%OFF）
    # fixed: 割引額（例: 1000 = 1000円OFF）
    # months_free: 無料月数（例: 1 = 1ヶ月無料）
    discount_value = models.DecimalField(
        '割引値',
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    # 有効期限
    valid_from = models.DateField('有効開始日')
    valid_until = models.DateField('有効期限', null=True, blank=True)

    # 使用情報
    used_at = models.DateTimeField('使用日時', null=True, blank=True)
    used_invoice = models.ForeignKey(
        'billing.Invoice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fs_discounts',
        verbose_name='使用請求書'
    )

    # 割引額（実際に適用された金額）
    applied_amount = models.DecimalField(
        '適用額',
        max_digits=10,
        decimal_places=0,
        null=True, blank=True
    )

    # 備考
    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't18_fs_discounts'
        verbose_name = 'T18_FS割引'
        verbose_name_plural = 'T18_FS割引'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.guardian} - {self.get_discount_type_display()} ({self.get_status_display()})"

    @classmethod
    def apply_discount(cls, guardian, friendship):
        """友達登録成立時にFS割引を付与"""
        from datetime import date, timedelta

        # デフォルト割引設定（将来的にはシステム設定から取得）
        discount_type = cls.DiscountType.FIXED
        discount_value = 1000  # 1000円割引

        today = date.today()
        valid_until = today + timedelta(days=90)  # 90日間有効

        return cls.objects.create(
            tenant_id=guardian.tenant_id,
            guardian=guardian,
            friendship=friendship,
            discount_type=discount_type,
            discount_value=discount_value,
            status=cls.Status.ACTIVE,
            valid_from=today,
            valid_until=valid_until,
        )

    def use(self, invoice, applied_amount):
        """FS割引を使用"""
        from django.utils import timezone
        self.status = self.Status.USED
        self.used_at = timezone.now()
        self.used_invoice = invoice
        self.applied_amount = applied_amount
        self.save()

    @classmethod
    def get_available_discounts(cls, guardian):
        """保護者の利用可能なFS割引を取得"""
        from datetime import date
        today = date.today()
        return cls.objects.filter(
            guardian=guardian,
            status=cls.Status.ACTIVE,
            valid_from__lte=today,
        ).filter(
            models.Q(valid_until__isnull=True) | models.Q(valid_until__gte=today)
        )
