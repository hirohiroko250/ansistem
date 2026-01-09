"""
Friendship Models - 友達紹介・FS割引
FriendshipRegistration, FSDiscount
"""
import uuid
from django.db import models
from apps.core.models import TenantModel

from .guardian import Guardian


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
        from datetime import date

        # デフォルト割引設定（将来的にはシステム設定から取得）
        discount_type = cls.DiscountType.FIXED
        discount_value = 500  # 500円割引（毎月）

        today = date.today()
        # 有効期限なし（どちらかが退会するまで継続）
        valid_until = None

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
