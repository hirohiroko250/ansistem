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

    @classmethod
    def generate_student_no(cls):
        """8桁の生徒番号を自動生成"""
        import random
        while True:
            # 8桁の数字を生成（10000000〜99999999）
            student_no = str(random.randint(10000000, 99999999))
            # 既存の番号と重複しないかチェック
            if not cls.objects.filter(student_no=student_no).exists():
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
    display_name = models.CharField('表示名', max_length=100, blank=True)

    # 連絡先
    email = models.EmailField('メールアドレス', blank=True)
    phone = models.CharField('電話番号', max_length=20, blank=True)
    line_id = models.CharField('LINE ID', max_length=50, blank=True)

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

    @classmethod
    def generate_guardian_no(cls):
        """8桁の保護者番号を自動生成"""
        import random
        while True:
            # 8桁の数字を生成（10000000〜99999999）
            guardian_no = str(random.randint(10000000, 99999999))
            # 既存の番号と重複しないかチェック
            if not cls.objects.filter(guardian_no=guardian_no).exists():
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

    class Meta:
        db_table = 't10_student_schools'
        verbose_name = '生徒所属'
        verbose_name_plural = '生徒所属'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.student} - {self.school}"


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
