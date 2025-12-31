"""
ContractHistory Model - 契約履歴
"""
import uuid
from django.db import models
from apps.core.models import TenantModel


class ContractHistory(TenantModel):
    """契約履歴

    契約の変更（作成、更新、キャンセル等）を全て記録する。
    """

    class ActionType(models.TextChoices):
        CREATED = 'created', '新規作成'
        UPDATED = 'updated', '更新'
        CANCELLED = 'cancelled', '解約'
        PAUSED = 'paused', '休会'
        RESUMED = 'resumed', '再開'
        COURSE_CHANGED = 'course_changed', 'コース変更'
        SCHEDULE_CHANGED = 'schedule_changed', 'スケジュール変更'
        SCHOOL_CHANGED = 'school_changed', '校舎変更'
        PRICE_CHANGED = 'price_changed', '料金変更'
        DISCOUNT_APPLIED = 'discount_applied', '割引適用'
        MILE_APPLIED = 'mile_applied', 'マイル適用'
        PROMOTION = 'promotion', '進級'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    contract = models.ForeignKey(
        'contracts.Contract',
        on_delete=models.CASCADE,
        related_name='histories',
        verbose_name='契約'
    )

    # 変更種別
    action_type = models.CharField(
        '変更種別',
        max_length=30,
        choices=ActionType.choices
    )

    # 変更前後のデータ（JSON形式）
    before_data = models.JSONField(
        '変更前データ',
        null=True,
        blank=True,
        help_text='変更前の契約情報をJSON形式で保存'
    )
    after_data = models.JSONField(
        '変更後データ',
        null=True,
        blank=True,
        help_text='変更後の契約情報をJSON形式で保存'
    )

    # 変更内容の説明
    change_summary = models.CharField('変更概要', max_length=500)
    change_detail = models.TextField('変更詳細', blank=True)

    # 金額関連
    amount_before = models.DecimalField(
        '変更前金額',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True
    )
    amount_after = models.DecimalField(
        '変更後金額',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True
    )
    discount_amount = models.DecimalField(
        '割引額',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True
    )
    mile_used = models.IntegerField('使用マイル', null=True, blank=True)
    mile_discount = models.DecimalField(
        'マイル割引額',
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True
    )

    # 適用日
    effective_date = models.DateField('適用日', null=True, blank=True)

    # 変更者
    changed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contract_histories',
        verbose_name='変更者'
    )
    changed_by_name = models.CharField('変更者名', max_length=100, blank=True)

    # システム変更フラグ
    is_system_change = models.BooleanField(
        'システム変更',
        default=False,
        help_text='自動処理による変更の場合True'
    )

    # IPアドレス（監査用）
    ip_address = models.GenericIPAddressField('IPアドレス', null=True, blank=True)

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 'contract_histories'
        verbose_name = '契約履歴'
        verbose_name_plural = '契約履歴'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['contract', '-created_at']),
            models.Index(fields=['action_type']),
        ]

    def __str__(self):
        return f"{self.contract.contract_no} - {self.get_action_type_display()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    @classmethod
    def log_change(cls, contract, action_type, change_summary,
                   before_data=None, after_data=None, user=None,
                   is_system=False, **kwargs):
        """契約変更をログに記録するヘルパーメソッド"""
        return cls.objects.create(
            tenant_id=contract.tenant_id,
            contract=contract,
            action_type=action_type,
            change_summary=change_summary,
            before_data=before_data,
            after_data=after_data,
            changed_by=user,
            changed_by_name=user.get_full_name() if user else 'システム',
            is_system_change=is_system,
            **kwargs
        )
