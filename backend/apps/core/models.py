"""
Core Models - Base models for multi-tenant support
"""
import uuid
from django.db import models
from django.utils import timezone


class TenantManager(models.Manager):
    """会社フィルタリング用マネージャー"""

    def for_tenant(self, tenant):
        """指定会社の有効なレコードのみを取得"""
        # tenantはTenantオブジェクト or UUID
        if hasattr(tenant, 'id'):
            return self.filter(tenant_ref=tenant, deleted_at__isnull=True)
        return self.filter(tenant_id=tenant, deleted_at__isnull=True)

    def active(self):
        """論理削除されていないレコードのみを取得"""
        return self.filter(deleted_at__isnull=True)


class BaseModel(models.Model):
    """全モデルの基底クラス（UUID主キー、タイムスタンプ）"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
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
        abstract = True


class TenantModel(BaseModel):
    """マルチテナント対応の基底モデル"""
    # 既存のtenant_id（UUID）を維持
    tenant_id = models.UUIDField(
        db_index=True,
        verbose_name='会社ID'
    )
    # ForeignKeyでテナントを参照（Admin選択可能）
    tenant_ref = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_set',
        verbose_name='会社'
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='削除日時'
    )

    objects = TenantManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """保存時にtenant_idとtenant_refを同期"""
        # tenant_refから設定された場合、tenant_idを同期
        if self.tenant_ref and (not self.tenant_id or self.tenant_id != self.tenant_ref.id):
            self.tenant_id = self.tenant_ref.id
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """論理削除"""
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at', 'updated_at'])

    def hard_delete(self, using=None, keep_parents=False):
        """物理削除"""
        super().delete(using=using, keep_parents=keep_parents)

    @property
    def is_deleted(self):
        """削除済みかどうか"""
        return self.deleted_at is not None


class TimestampModel(models.Model):
    """タイムスタンプのみを持つ軽量な基底クラス"""
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='作成日時'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新日時'
    )

    class Meta:
        abstract = True
