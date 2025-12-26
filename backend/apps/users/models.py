"""
User Models (T16)
"""
import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class UserManager(BaseUserManager):
    """カスタムユーザーマネージャー"""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('メールアドレスは必須です')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'SUPER_ADMIN')
        extra_fields.setdefault('user_type', 'ADMIN')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('スーパーユーザーはis_staff=Trueである必要があります')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('スーパーユーザーはis_superuser=Trueである必要があります')

        return self.create_user(email, password, **extra_fields)

    def for_tenant(self, tenant_id):
        """指定テナントのユーザーを取得"""
        return self.filter(tenant_id=tenant_id, deleted_at__isnull=True)

    def active(self):
        """有効なユーザーのみ取得"""
        return self.filter(is_active=True, deleted_at__isnull=True)


class User(AbstractBaseUser, PermissionsMixin):
    """カスタムユーザーモデル (T16)"""

    class UserType(models.TextChoices):
        STUDENT = 'STUDENT', '生徒'
        GUARDIAN = 'GUARDIAN', '保護者'
        TEACHER = 'TEACHER', '講師'
        STAFF = 'STAFF', 'スタッフ'
        ADMIN = 'ADMIN', '管理者'

    class Role(models.TextChoices):
        USER = 'USER', '一般ユーザー'
        TEACHER = 'TEACHER', '講師'
        SCHOOL_MANAGER = 'SCHOOL_MANAGER', '校舎管理者'
        ACCOUNTING = 'ACCOUNTING', '経理'
        ADMIN = 'ADMIN', '管理者'
        SUPER_ADMIN = 'SUPER_ADMIN', 'システム管理者'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    tenant_id = models.UUIDField(
        db_index=True,
        null=True,
        blank=True,
        verbose_name='会社ID'
    )

    # 認証情報
    email = models.EmailField(
        unique=True,
        verbose_name='メールアドレス'
    )
    is_email_verified = models.BooleanField(
        default=False,
        verbose_name='メール認証済み'
    )

    # 基本情報
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.STAFF,
        verbose_name='ユーザー種別'
    )
    user_no = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        verbose_name='ユーザー番号'
    )

    # 名前
    last_name = models.CharField(
        max_length=50,
        verbose_name='姓'
    )
    first_name = models.CharField(
        max_length=50,
        verbose_name='名'
    )
    last_name_kana = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='姓（カナ）'
    )
    first_name_kana = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='名（カナ）'
    )
    display_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='表示名'
    )

    # 連絡先
    phone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='電話番号'
    )
    line_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='LINE ID'
    )

    # プロフィール
    profile_image_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name='プロフィール画像URL'
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='生年月日'
    )
    gender = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name='性別'
    )

    # 親アカウント（保護者→生徒の階層構造用）
    parent_user = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='child_accounts',
        verbose_name='親アカウント'
    )

    # 関連
    student_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name='生徒ID'
    )
    staff_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name='スタッフID'
    )

    # 所属（主）
    primary_school_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name='主校舎ID'
    )
    primary_brand_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name='主ブランドID'
    )

    # 登録時情報（保護者向け）
    nearest_school_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name='最寄り校舎ID'
    )
    interested_brands = models.JSONField(
        default=list,
        blank=True,
        verbose_name='興味のあるブランド'
    )
    referral_source = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='流入経路'
    )
    expectations = models.TextField(
        null=True,
        blank=True,
        verbose_name='期待すること'
    )

    # 権限
    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.USER,
        verbose_name='ロール'
    )
    permissions = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='権限'
    )

    # ステータス
    is_active = models.BooleanField(
        default=True,
        verbose_name='有効'
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name='スタッフ権限'
    )
    last_login_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='最終ログイン'
    )

    # セキュリティ
    failed_login_count = models.IntegerField(
        default=0,
        verbose_name='ログイン失敗回数'
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='ロック解除日時'
    )
    password_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='パスワード変更日時'
    )
    must_change_password = models.BooleanField(
        default=False,
        verbose_name='パスワード変更必須'
    )

    # タイムスタンプ
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='作成日時'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新日時'
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='削除日時'
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['last_name', 'first_name']

    class Meta:
        db_table = 't16_users'
        verbose_name = 'ユーザー'
        verbose_name_plural = 'ユーザー'
        indexes = [
            models.Index(fields=['tenant_id', 'user_type']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.email} ({self.full_name})"

    @property
    def full_name(self):
        """フルネーム"""
        return f"{self.last_name} {self.first_name}"

    @property
    def full_name_kana(self):
        """フルネーム（カナ）"""
        if self.last_name_kana and self.first_name_kana:
            return f"{self.last_name_kana} {self.first_name_kana}"
        return None

    def get_display_name(self):
        """表示名を取得"""
        return self.display_name or self.full_name

    def is_locked(self):
        """アカウントがロックされているか"""
        if self.locked_until:
            return timezone.now() < self.locked_until
        return False

    def increment_failed_login(self):
        """ログイン失敗回数をインクリメント"""
        self.failed_login_count += 1
        if self.failed_login_count >= 5:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=30)
        self.save(update_fields=['failed_login_count', 'locked_until'])

    def reset_failed_login(self):
        """ログイン失敗回数をリセット"""
        self.failed_login_count = 0
        self.locked_until = None
        self.last_login_at = timezone.now()
        self.save(update_fields=['failed_login_count', 'locked_until', 'last_login_at'])

    def has_permission(self, permission_name):
        """特定の権限を持っているか"""
        return self.permissions.get(permission_name, False)

    def delete(self, using=None, keep_parents=False):
        """論理削除"""
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save(update_fields=['deleted_at', 'is_active', 'updated_at'])

    # 階層構造関連メソッド
    @property
    def is_parent_account(self):
        """親アカウント（保護者等）かどうか"""
        return self.child_accounts.exists()

    @property
    def is_child_account(self):
        """子アカウント（生徒等）かどうか"""
        return self.parent_user is not None

    def get_children(self):
        """子アカウント一覧を取得"""
        return self.child_accounts.filter(deleted_at__isnull=True, is_active=True)

    def get_all_accessible_users(self):
        """
        アクセス可能な全ユーザーを取得
        - 自分自身
        - 子アカウント（保護者の場合）
        """
        from django.db.models import Q
        if self.is_child_account:
            # 子アカウントの場合は自分のみ
            return User.objects.filter(id=self.id)
        else:
            # 親アカウントの場合は自分と子アカウント
            return User.objects.filter(
                Q(id=self.id) | Q(parent_user=self),
                deleted_at__isnull=True
            )

    def can_manage_user(self, target_user):
        """指定ユーザーを管理できるか"""
        if self.id == target_user.id:
            return True
        if target_user.parent_user_id == self.id:
            return True
        return False

    def switch_to_child(self, child_user_id):
        """
        子アカウントに切り替え可能か確認
        実際の切り替えはフロントエンドで管理（トークン再発行等）
        """
        try:
            child = self.child_accounts.get(id=child_user_id, is_active=True, deleted_at__isnull=True)
            return child
        except User.DoesNotExist:
            return None
