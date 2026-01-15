"""
Student Model - 生徒マスタ
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

    # QRコード識別子（出席管理用）
    qr_code = models.UUIDField(
        'QRコード識別子',
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True
    )

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
        'students.Guardian',
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
