"""
Confirmed Billing Models - 請求確定
"""
import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel


class ConfirmedBilling(TenantModel):
    """請求確定データ

    締日確定時に生徒ごとの請求データをスナップショットとして保存。
    元のStudentItemとは独立して管理され、監査証跡として機能する。
    """

    class Status(models.TextChoices):
        CONFIRMED = 'confirmed', '確定'
        UNPAID = 'unpaid', '未入金'
        PARTIAL = 'partial', '一部入金'
        PAID = 'paid', '入金済'
        CANCELLED = 'cancelled', '取消'

    class PaymentMethod(models.TextChoices):
        DIRECT_DEBIT = 'direct_debit', '口座振替'
        BANK_TRANSFER = 'bank_transfer', '振込'
        CASH = 'cash', '現金'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    billing_no = models.CharField(
        '請求番号',
        max_length=20,
        blank=True,
        db_index=True,
        help_text='例: CB202501-0001'
    )

    # 対象
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='confirmed_billings',
        verbose_name='生徒'
    )
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.PROTECT,
        related_name='confirmed_billings',
        verbose_name='保護者'
    )

    # 請求期間
    year = models.IntegerField('請求年')
    month = models.IntegerField('請求月')
    billing_deadline = models.ForeignKey(
        'billing.MonthlyBillingDeadline',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_billings',
        verbose_name='締日'
    )

    # 金額
    subtotal = models.DecimalField('小計', max_digits=12, decimal_places=0, default=0)
    discount_total = models.DecimalField('割引合計', max_digits=12, decimal_places=0, default=0)
    tax_amount = models.DecimalField('税額', max_digits=12, decimal_places=0, default=0)
    total_amount = models.DecimalField('合計金額', max_digits=12, decimal_places=0, default=0)

    # 入金情報
    paid_amount = models.DecimalField('入金済金額', max_digits=12, decimal_places=0, default=0)
    balance = models.DecimalField('残高', max_digits=12, decimal_places=0, default=0)

    # 繰越額（前月からの繰越）
    carry_over_amount = models.DecimalField(
        '繰越額',
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='前月からの繰越額（プラス=未払い繰越、マイナス=過払い繰越）'
    )

    # 過不足金（調整額）
    adjustment_amount = models.DecimalField(
        '過不足金',
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='過不足金（プラス=追加請求、マイナス=返金/相殺）'
    )
    adjustment_note = models.TextField(
        '過不足金備考',
        blank=True,
        help_text='過不足金の詳細説明'
    )

    # 明細スナップショット（JSON形式で保存）
    items_snapshot = models.JSONField('明細スナップショット', default=list)
    discounts_snapshot = models.JSONField('割引スナップショット', default=list)

    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.CONFIRMED
    )
    payment_method = models.CharField(
        '支払方法',
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.DIRECT_DEBIT
    )

    # 確定情報
    confirmed_at = models.DateTimeField('確定日時', auto_now_add=True)
    confirmed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_billings',
        verbose_name='確定者'
    )

    # 入金完了情報
    paid_at = models.DateTimeField('入金完了日時', null=True, blank=True)

    # メモ
    notes = models.TextField('備考', blank=True)

    # 退会日情報
    withdrawal_date = models.DateField('全退会日', null=True, blank=True, help_text='生徒の退会日')
    brand_withdrawal_dates = models.JSONField(
        'ブランド退会日',
        default=dict,
        blank=True,
        help_text='ブランドごとの退会日 {brand_id: "YYYY-MM-DD"}'
    )

    # 休会・復会日情報
    suspension_date = models.DateField('休会日', null=True, blank=True, help_text='生徒の休会日')
    return_date = models.DateField('復会日', null=True, blank=True, help_text='生徒の復会日')

    class Meta:
        db_table = 't_confirmed_billing'
        verbose_name = '請求確定'
        verbose_name_plural = '請求確定'
        ordering = ['guardian__last_name', 'guardian__first_name', 'student__last_name', 'student__first_name', 'billing_no']
        indexes = [
            models.Index(fields=['student', 'year', 'month']),
            models.Index(fields=['guardian', 'year', 'month']),
            models.Index(fields=['status']),
            models.Index(fields=['-confirmed_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tenant_id', 'student', 'year', 'month'],
                name='unique_confirmed_billing_per_student_month'
            )
        ]

    def __str__(self):
        student_name = self.student.full_name if self.student else '生徒なし'
        return f"{self.year}年{self.month}月分 - {student_name} ({self.total_amount:,}円)"

    def save(self, *args, **kwargs):
        if not self.billing_no:
            self.billing_no = self._generate_billing_no()
        super().save(*args, **kwargs)

    def _generate_billing_no(self):
        """請求番号を生成: CB202501-0001"""
        prefix = f"CB{self.year}{str(self.month).zfill(2)}"

        last = ConfirmedBilling.objects.filter(
            tenant_id=self.tenant_id,
            billing_no__startswith=prefix
        ).order_by('-billing_no').first()

        if last and last.billing_no:
            try:
                last_num = int(last.billing_no.split('-')[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1

        return f"{prefix}-{str(next_num).zfill(4)}"

    def update_payment_status(self):
        """入金状況に基づいてステータスを更新"""
        self.balance = self.total_amount - self.paid_amount
        if self.paid_amount >= self.total_amount:
            self.status = self.Status.PAID
            if not self.paid_at:
                self.paid_at = timezone.now()
        elif self.paid_amount > 0:
            self.status = self.Status.PARTIAL
        else:
            self.status = self.Status.UNPAID
        self.save()

    @classmethod
    def create_from_student_items(cls, tenant_id, student, guardian, year, month, user=None):
        """StudentItem（生徒商品）から請求確定データを作成

        インポート済みのStudentItemデータから明細を生成。
        未請求（is_billed=False）のStudentItemを全て集計し、
        確定後にis_billed=Trueに更新する。
        """
        from .billing_creation import (
            build_student_items_snapshot,
            build_seminar_items_snapshot,
            build_discounts_snapshot,
            get_withdrawal_info,
            update_confirmed_data,
        )
        from apps.contracts.models import StudentItem

        # 既存の確定データがあれば取得（更新用）
        confirmed, created = cls.objects.get_or_create(
            tenant_id=tenant_id,
            student=student,
            year=year,
            month=month,
            defaults={'guardian': guardian}
        )

        if not created and confirmed.status == cls.Status.PAID:
            return confirmed, False

        # StudentItemから明細スナップショットを作成（未請求アイテムのみ）
        items_snapshot, subtotal, student_item_ids = build_student_items_snapshot(
            tenant_id, student, year, month
        )

        # 講習申込を追加
        seminar_items, seminar_subtotal = build_seminar_items_snapshot(tenant_id, student, year, month)
        items_snapshot.extend(seminar_items)
        subtotal += seminar_subtotal

        # 割引スナップショットを作成
        discounts_snapshot, discount_total = build_discounts_snapshot(
            tenant_id, student, guardian, year, month, items_snapshot, subtotal
        )

        # 前月からの繰越額を取得
        carry_over = cls.get_previous_month_balance(tenant_id, student, year, month)

        # 退会日情報を取得
        withdrawal_info = get_withdrawal_info(tenant_id, student)

        # 確定データを更新
        update_confirmed_data(
            confirmed, guardian, subtotal, discount_total,
            items_snapshot, discounts_snapshot, withdrawal_info, carry_over, user
        )

        # StudentItemを請求済みとしてマーク
        if student_item_ids:
            StudentItem.objects.filter(id__in=student_item_ids).update(
                is_billed=True,
                confirmed_billing=confirmed
            )

        return confirmed, created

    @classmethod
    def create_from_contracts(cls, tenant_id, student, guardian, year, month, user=None):
        """Contract（契約）から請求確定データを作成

        有効な契約のCourseItem（商品構成）から明細を生成
        """
        from .billing_creation import (
            build_contract_items_snapshot,
            build_seminar_items_snapshot,
            build_discounts_snapshot,
            get_withdrawal_info,
            deduplicate_facility_items,
            update_confirmed_data,
        )

        # 既存の確定データがあれば取得（更新用）
        confirmed, created = cls.objects.get_or_create(
            tenant_id=tenant_id,
            student=student,
            year=year,
            month=month,
            defaults={'guardian': guardian}
        )

        if not created and confirmed.status == cls.Status.PAID:
            return confirmed, False

        # Contractから明細スナップショットを作成
        items_snapshot, subtotal = build_contract_items_snapshot(tenant_id, student, year, month)

        # 講習申込を追加
        seminar_items, seminar_subtotal = build_seminar_items_snapshot(tenant_id, student, year, month)
        items_snapshot.extend(seminar_items)
        subtotal += seminar_subtotal

        # 設備費の重複排除
        items_snapshot = deduplicate_facility_items(items_snapshot)

        # 小計を再計算
        subtotal = sum(Decimal(str(i.get('final_price', 0) or 0)) for i in items_snapshot)

        # 割引スナップショットを作成
        discounts_snapshot, discount_total = build_discounts_snapshot(
            tenant_id, student, guardian, year, month, items_snapshot, subtotal
        )

        # 前月からの繰越額を取得
        carry_over = cls.get_previous_month_balance(tenant_id, student, year, month)

        # 退会日情報を取得
        withdrawal_info = get_withdrawal_info(tenant_id, student)

        # 確定データを更新
        update_confirmed_data(
            confirmed, guardian, subtotal, discount_total,
            items_snapshot, discounts_snapshot, withdrawal_info, carry_over, user
        )

        return confirmed, created

    @classmethod
    def get_previous_month_balance(cls, tenant_id, student, year, month):
        """前月の残高（繰越額）を取得

        Returns:
            Decimal: 前月の残高
                プラス = 前月に未払いがあった（今月への繰越請求）
                マイナス = 前月に過払いがあった（今月への繰越クレジット）
                0 = 前月は精算済み or データなし
        """
        if month == 1:
            prev_year = year - 1
            prev_month = 12
        else:
            prev_year = year
            prev_month = month - 1

        prev_billing = cls.objects.filter(
            tenant_id=tenant_id,
            student=student,
            year=prev_year,
            month=prev_month
        ).first()

        if not prev_billing:
            return Decimal('0')

        return prev_billing.balance

    @classmethod
    def apply_carry_over(cls, tenant_id, student, year, month):
        """前月の残高を今月の繰越額として適用"""
        confirmed = cls.objects.filter(
            tenant_id=tenant_id,
            student=student,
            year=year,
            month=month
        ).first()

        if not confirmed:
            return None

        carry_over = cls.get_previous_month_balance(tenant_id, student, year, month)

        confirmed.carry_over_amount = carry_over
        confirmed.balance = confirmed.total_amount + carry_over - confirmed.paid_amount
        confirmed.save()

        if confirmed.balance <= 0 and confirmed.total_amount > 0:
            confirmed.status = cls.Status.PAID
            if not confirmed.paid_at:
                confirmed.paid_at = timezone.now()
            confirmed.save()

        return confirmed
