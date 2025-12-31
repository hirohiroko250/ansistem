"""
DiscountOperationLog Model - 割引操作履歴
"""
import uuid
from django.db import models
from apps.core.models import TenantModel


class DiscountOperationLog(TenantModel):
    """割引操作履歴

    割引の追加・変更・削除を記録し、割引Max超過時の校舎負担分を追跡する。
    """

    class OperationType(models.TextChoices):
        ADD = 'add', '追加'
        UPDATE = 'update', '変更'
        DELETE = 'delete', '削除'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 対象
    contract = models.ForeignKey(
        'contracts.Contract',
        on_delete=models.CASCADE,
        related_name='discount_logs',
        verbose_name='契約'
    )
    student_discount = models.ForeignKey(
        'contracts.StudentDiscount',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='operation_logs',
        verbose_name='割引'
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='discount_logs',
        verbose_name='生徒'
    )

    # 操作種別
    operation_type = models.CharField(
        '操作種別',
        max_length=10,
        choices=OperationType.choices
    )

    # 割引情報
    discount_name = models.CharField('割引名', max_length=200)
    discount_amount = models.DecimalField(
        '割引額',
        max_digits=10,
        decimal_places=0,
        help_text='適用された割引額'
    )
    discount_unit = models.CharField(
        '割引単位',
        max_length=10,
        default='yen'
    )

    # 割引Max情報
    discount_max = models.DecimalField(
        '割引Max',
        max_digits=10,
        decimal_places=0,
        default=0,
        help_text='適用時点の商品の割引Max'
    )
    total_discount_before = models.DecimalField(
        '操作前の合計割引額',
        max_digits=10,
        decimal_places=0,
        default=0
    )
    total_discount_after = models.DecimalField(
        '操作後の合計割引額',
        max_digits=10,
        decimal_places=0,
        default=0
    )

    # 校舎負担分（割引Max超過分）
    excess_amount = models.DecimalField(
        '校舎負担分',
        max_digits=10,
        decimal_places=0,
        default=0,
        help_text='割引Maxを超過した金額（校舎負担）'
    )

    # 担当校舎（負担する校舎）
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='discount_excess_logs',
        verbose_name='担当校舎'
    )
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='discount_excess_logs',
        verbose_name='ブランド'
    )

    # 操作者
    operated_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='discount_operations',
        verbose_name='操作者'
    )
    operated_by_name = models.CharField('操作者名', max_length=100, blank=True)

    # IPアドレス（監査用）
    ip_address = models.GenericIPAddressField('IPアドレス', null=True, blank=True)

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 'discount_operation_logs'
        verbose_name = '割引操作履歴'
        verbose_name_plural = '割引操作履歴'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['contract', '-created_at']),
            models.Index(fields=['student', '-created_at']),
            models.Index(fields=['school', '-created_at']),
            models.Index(fields=['operated_by', '-created_at']),
        ]

    def __str__(self):
        return f"{self.contract.contract_no} - {self.get_operation_type_display()} {self.discount_name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    @classmethod
    def log_operation(cls, contract, operation_type, discount_name, discount_amount,
                      discount_unit='yen', discount_max=0, total_before=0, total_after=0,
                      user=None, school=None, brand=None, student_discount=None,
                      ip_address=None, notes=''):
        """割引操作をログに記録するヘルパーメソッド

        Args:
            contract: 契約
            operation_type: 操作種別 ('add', 'update', 'delete')
            discount_name: 割引名
            discount_amount: 割引額
            discount_unit: 割引単位 ('yen' or 'percent')
            discount_max: 割引Max
            total_before: 操作前の合計割引額
            total_after: 操作後の合計割引額
            user: 操作者
            school: 担当校舎
            brand: ブランド
            student_discount: StudentDiscountインスタンス
            ip_address: IPアドレス
            notes: 備考
        """
        # 校舎負担分（割引Max超過分）を計算
        excess_amount = max(0, total_after - discount_max) if discount_max > 0 else 0

        return cls.objects.create(
            tenant_id=contract.tenant_id,
            contract=contract,
            student_discount=student_discount,
            student=contract.student,
            operation_type=operation_type,
            discount_name=discount_name,
            discount_amount=discount_amount,
            discount_unit=discount_unit,
            discount_max=discount_max,
            total_discount_before=total_before,
            total_discount_after=total_after,
            excess_amount=excess_amount,
            school=school or contract.school,
            brand=brand or contract.brand,
            operated_by=user,
            operated_by_name=user.get_full_name() if user else '',
            ip_address=ip_address,
            notes=notes
        )
