"""
Tenant Models
"""
import uuid
from django.db import models


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
