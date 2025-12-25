"""
Tenant Models
"""
import uuid
from django.db import models
from apps.core.models import TenantModel


class Tenant(models.Model):
    """会社（塾運営会社）- グループ企業対応"""

    class PlanType(models.TextChoices):
        FREE = 'FREE', 'フリー'
        STANDARD = 'STANDARD', 'スタンダード'
        PROFESSIONAL = 'PROFESSIONAL', 'プロフェッショナル'
        ENTERPRISE = 'ENTERPRISE', 'エンタープライズ'

    class TenantType(models.TextChoices):
        PARENT = 'parent', '親会社'
        CHILD = 'child', '子会社'
        STANDALONE = 'standalone', '単独'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='会社ID'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='親会社'
    )
    tenant_type = models.CharField(
        max_length=20,
        choices=TenantType.choices,
        default=TenantType.STANDALONE,
        verbose_name='会社種別'
    )
    tenant_code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='会社コード'
    )
    tenant_name = models.CharField(
        max_length=100,
        verbose_name='会社名'
    )
    contact_email = models.EmailField(
        null=True,
        blank=True,
        verbose_name='連絡先メール'
    )
    contact_phone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='連絡先電話番号'
    )
    settings = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='設定'
    )
    features = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='機能フラグ'
    )
    plan_type = models.CharField(
        max_length=30,
        choices=PlanType.choices,
        default=PlanType.STANDARD,
        verbose_name='プラン'
    )
    max_schools = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='最大校舎数'
    )
    max_users = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='最大ユーザー数'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='有効'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='作成日時'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新日時'
    )

    class Meta:
        db_table = 'tenants'
        verbose_name = '会社'
        verbose_name_plural = '会社'
        ordering = ['tenant_code']

    def __str__(self):
        return f"{self.tenant_code} - {self.tenant_name}"

    def get_setting(self, key, default=None):
        """設定値を取得"""
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        """設定値を設定"""
        self.settings[key] = value
        self.save(update_fields=['settings', 'updated_at'])

    def has_feature(self, feature_name):
        """機能が有効かどうか"""
        return self.features.get(feature_name, False)

    @property
    def is_parent(self):
        """親会社かどうか"""
        return self.tenant_type == self.TenantType.PARENT

    @property
    def is_child(self):
        """子会社かどうか"""
        return self.tenant_type == self.TenantType.CHILD

    def get_all_children(self):
        """全ての子テナントを取得"""
        return Tenant.objects.filter(parent=self)

    def get_group_tenants(self):
        """グループ全体のテナントを取得（自分含む）"""
        if self.is_parent:
            return Tenant.objects.filter(
                models.Q(id=self.id) | models.Q(parent=self)
            )
        elif self.parent:
            return Tenant.objects.filter(
                models.Q(id=self.parent.id) | models.Q(parent=self.parent)
            )
        return Tenant.objects.filter(id=self.id)

    def get_root_tenant(self):
        """最上位の親テナントを取得"""
        if self.parent:
            return self.parent.get_root_tenant()
        return self


class Position(TenantModel):
    """役職マスタ"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    position_code = models.CharField('役職コード', max_length=20, blank=True)
    position_name = models.CharField('役職名', max_length=50)
    rank = models.IntegerField('ランク', default=0, help_text='数字が大きいほど上位')

    # グローバル権限設定
    school_restriction = models.BooleanField('校舎制限', default=False, help_text='ONの場合、所属校舎のみ閲覧可能')
    brand_restriction = models.BooleanField('ブランド制限', default=False, help_text='ONの場合、所属ブランドのみ閲覧可能')
    bulk_email_restriction = models.BooleanField('メール一括送信制限', default=False, help_text='ONの場合、一括送信不可')
    email_approval_required = models.BooleanField('メール上長承認必要', default=False, help_text='ONの場合、メール送信に上長承認が必要')
    is_accounting = models.BooleanField('経理権限', default=False, help_text='経理系機能へのアクセス権限')

    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't20_positions'
        verbose_name = '役職'
        verbose_name_plural = '役職'
        ordering = ['-rank', 'position_name']

    def __str__(self):
        return self.position_name


class FeatureMaster(TenantModel):
    """機能マスタ - 権限設定可能な機能・画面一覧"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    feature_code = models.CharField('機能コード', max_length=20, unique=True, help_text='例: 1000, 2000, 10010')
    feature_name = models.CharField('機能名', max_length=100)
    parent_code = models.CharField('親機能コード', max_length=20, blank=True, help_text='サブ機能の場合、親の機能コード')
    category = models.CharField('カテゴリ', max_length=50, blank=True)
    description = models.TextField('説明', blank=True)
    display_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't21_feature_masters'
        verbose_name = '機能マスタ'
        verbose_name_plural = '機能マスタ'
        ordering = ['display_order', 'feature_code']

    def __str__(self):
        return f"{self.feature_code}: {self.feature_name}"


class PositionPermission(TenantModel):
    """役職権限 - 役職ごとの機能アクセス権限"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    position = models.ForeignKey(
        Position,
        on_delete=models.CASCADE,
        related_name='permissions',
        verbose_name='役職'
    )
    feature = models.ForeignKey(
        FeatureMaster,
        on_delete=models.CASCADE,
        related_name='position_permissions',
        verbose_name='機能'
    )
    has_permission = models.BooleanField('権限あり', default=False)

    class Meta:
        db_table = 't22_position_permissions'
        verbose_name = '役職権限'
        verbose_name_plural = '役職権限'
        unique_together = ['tenant_ref', 'position', 'feature']
        ordering = ['position__rank', 'feature__display_order']

    def __str__(self):
        status = '○' if self.has_permission else '×'
        return f"{self.position.position_name} - {self.feature.feature_name}: {status}"


class Employee(TenantModel):
    """T19: 社員マスタ"""

    class DiscountUnit(models.TextChoices):
        PERCENT = '%', '%'
        YEN = 'yen', '円'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 社員番号（OZA側のID）
    employee_no = models.CharField(
        '社員番号',
        max_length=50,
        blank=True,
        db_index=True
    )

    # 保護者との紐付け（社員が保護者でもある場合）
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
        verbose_name='保護者'
    )

    # 対応校舎・ブランド
    schools = models.ManyToManyField(
        'schools.School',
        blank=True,
        related_name='employees',
        verbose_name='対応校舎'
    )
    brands = models.ManyToManyField(
        'schools.Brand',
        blank=True,
        related_name='employees',
        verbose_name='対応ブランド'
    )

    # 基本情報
    department = models.CharField('部署', max_length=100, blank=True)
    last_name = models.CharField('姓', max_length=50)
    first_name = models.CharField('名', max_length=50)
    email = models.EmailField('メールアドレス', blank=True)
    phone = models.CharField('電話番号', max_length=20, blank=True)
    position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
        verbose_name='役職'
    )
    position_text = models.CharField('役職（テキスト）', max_length=50, blank=True, help_text='マスタ未登録時の役職名')

    # 雇用情報
    hire_date = models.DateField('採用日', null=True, blank=True)
    termination_date = models.DateField('解雇日', null=True, blank=True)

    # 住所情報
    postal_code = models.CharField('郵便番号', max_length=10, blank=True)
    prefecture = models.CharField('都道府県', max_length=10, blank=True)
    city = models.CharField('市区町村', max_length=50, blank=True)
    address = models.CharField('住所', max_length=200, blank=True)
    nationality = models.CharField('国籍', max_length=50, blank=True, default='日本')

    # 社員割引情報
    discount_flag = models.BooleanField('社員割引フラグ', default=False)
    discount_amount = models.IntegerField('社員割引額', default=0)
    discount_unit = models.CharField(
        '社員割引額単位',
        max_length=10,
        choices=DiscountUnit.choices,
        default=DiscountUnit.PERCENT
    )
    discount_category_name = models.CharField(
        '社員割引請求カテゴリー名',
        max_length=50,
        blank=True
    )
    discount_category_code = models.IntegerField(
        '社員割引請求カテゴリー区分',
        default=0
    )

    # OZAWorks連携
    ozaworks_registered = models.BooleanField('OZAWorks登録', default=False)

    # ステータス
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't19_employees'
        verbose_name = 'T19_社員'
        verbose_name_plural = 'T19_社員'
        ordering = ['department', 'last_name', 'first_name']

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.department})"

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}"
