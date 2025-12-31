"""
Bank Account Models - 銀行口座管理
BankAccount, BankAccountChangeRequest
"""
import uuid
from django.db import models
from apps.core.models import TenantModel

from .guardian import Guardian


class BankAccount(TenantModel):
    """T15: 銀行口座マスタ

    保護者の銀行口座情報を管理するモデル。
    承認済みの口座情報がGuardianモデルに反映される。
    """

    class AccountType(models.TextChoices):
        ORDINARY = 'ordinary', '普通'
        CURRENT = 'current', '当座'
        SAVINGS = 'savings', '貯蓄'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 保護者
    guardian = models.ForeignKey(
        Guardian,
        on_delete=models.CASCADE,
        related_name='bank_accounts',
        verbose_name='保護者'
    )

    # 銀行情報
    bank_name = models.CharField('金融機関名', max_length=100)
    bank_code = models.CharField('金融機関コード', max_length=4)
    branch_name = models.CharField('支店名', max_length=100)
    branch_code = models.CharField('支店コード', max_length=3)
    account_type = models.CharField(
        '口座種別',
        max_length=10,
        choices=AccountType.choices,
        default=AccountType.ORDINARY
    )
    account_number = models.CharField('口座番号', max_length=8)
    account_holder = models.CharField('口座名義', max_length=100)
    account_holder_kana = models.CharField('口座名義（カナ）', max_length=100)

    # ステータス
    is_primary = models.BooleanField('メイン口座', default=False)
    is_active = models.BooleanField('有効', default=True)
    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't15_bank_accounts'
        verbose_name = 'T15_銀行口座'
        verbose_name_plural = 'T15_銀行口座'
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"{self.guardian} - {self.bank_name} {self.branch_name} ({self.account_number})"

    def sync_to_guardian(self):
        """承認された口座情報をGuardianモデルに反映"""
        if self.is_primary:
            self.guardian.bank_name = self.bank_name
            self.guardian.bank_code = self.bank_code
            self.guardian.branch_name = self.branch_name
            self.guardian.branch_code = self.branch_code
            self.guardian.account_type = self.account_type
            self.guardian.account_number = self.account_number
            self.guardian.account_holder = self.account_holder
            self.guardian.account_holder_kana = self.account_holder_kana
            self.guardian.payment_registered = True
            from django.utils import timezone
            self.guardian.payment_registered_at = timezone.now()
            self.guardian.save()


class BankAccountChangeRequest(TenantModel):
    """T16: 銀行口座変更申請

    保護者からの銀行口座登録・変更申請を管理するモデル。
    申請後、スタッフが承認処理を行う。
    """

    class RequestType(models.TextChoices):
        NEW = 'new', '新規登録'
        UPDATE = 'update', '変更'
        DELETE = 'delete', '削除'

    class Status(models.TextChoices):
        PENDING = 'pending', '申請中'
        APPROVED = 'approved', '承認済'
        REJECTED = 'rejected', '却下'
        CANCELLED = 'cancelled', '取消'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 保護者
    guardian = models.ForeignKey(
        Guardian,
        on_delete=models.CASCADE,
        related_name='bank_account_requests',
        verbose_name='保護者'
    )

    # 既存口座（変更・削除の場合）
    existing_account = models.ForeignKey(
        BankAccount,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='change_requests',
        verbose_name='既存口座'
    )

    # 申請種別
    request_type = models.CharField(
        '申請種別',
        max_length=10,
        choices=RequestType.choices,
        default=RequestType.NEW
    )

    # 新しい銀行情報（新規・変更の場合）
    bank_name = models.CharField('金融機関名', max_length=100, blank=True)
    bank_code = models.CharField('金融機関コード', max_length=4, blank=True)
    branch_name = models.CharField('支店名', max_length=100, blank=True)
    branch_code = models.CharField('支店コード', max_length=3, blank=True)
    account_type = models.CharField(
        '口座種別',
        max_length=10,
        choices=BankAccount.AccountType.choices,
        default=BankAccount.AccountType.ORDINARY,
        blank=True
    )
    account_number = models.CharField('口座番号', max_length=8, blank=True)
    account_holder = models.CharField('口座名義', max_length=100, blank=True)
    account_holder_kana = models.CharField('口座名義（カナ）', max_length=100, blank=True)
    is_primary = models.BooleanField('メイン口座にする', default=True)

    # ステータス
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # 申請者情報
    requested_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='bank_account_requests',
        verbose_name='申請者'
    )
    requested_at = models.DateTimeField('申請日時', auto_now_add=True)
    request_notes = models.TextField('申請メモ', blank=True)

    # 処理者情報
    processed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='processed_bank_account_requests',
        verbose_name='処理者'
    )
    processed_at = models.DateTimeField('処理日時', null=True, blank=True)
    process_notes = models.TextField('処理メモ', blank=True)

    class Meta:
        db_table = 't16_bank_account_requests'
        verbose_name = 'T16_銀行口座変更申請'
        verbose_name_plural = 'T16_銀行口座変更申請'
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.guardian} - {self.get_request_type_display()} ({self.get_status_display()})"

    def approve(self, user, notes=''):
        """銀行口座申請を承認"""
        from django.utils import timezone

        self.status = self.Status.APPROVED
        self.processed_by = user
        self.processed_at = timezone.now()
        self.process_notes = notes
        self.save()

        if self.request_type == self.RequestType.NEW:
            # 新規登録
            if self.is_primary:
                # 他のメイン口座を解除
                BankAccount.objects.filter(
                    guardian=self.guardian,
                    is_primary=True
                ).update(is_primary=False)

            account = BankAccount.objects.create(
                tenant_id=self.tenant_id,
                guardian=self.guardian,
                bank_name=self.bank_name,
                bank_code=self.bank_code,
                branch_name=self.branch_name,
                branch_code=self.branch_code,
                account_type=self.account_type,
                account_number=self.account_number,
                account_holder=self.account_holder,
                account_holder_kana=self.account_holder_kana,
                is_primary=self.is_primary,
            )
            # メイン口座ならGuardianに反映
            if self.is_primary:
                account.sync_to_guardian()
            return account

        elif self.request_type == self.RequestType.UPDATE:
            # 変更
            if self.existing_account:
                if self.is_primary:
                    # 他のメイン口座を解除
                    BankAccount.objects.filter(
                        guardian=self.guardian,
                        is_primary=True
                    ).exclude(id=self.existing_account.id).update(is_primary=False)

                self.existing_account.bank_name = self.bank_name
                self.existing_account.bank_code = self.bank_code
                self.existing_account.branch_name = self.branch_name
                self.existing_account.branch_code = self.branch_code
                self.existing_account.account_type = self.account_type
                self.existing_account.account_number = self.account_number
                self.existing_account.account_holder = self.account_holder
                self.existing_account.account_holder_kana = self.account_holder_kana
                self.existing_account.is_primary = self.is_primary
                self.existing_account.save()

                # メイン口座ならGuardianに反映
                if self.is_primary:
                    self.existing_account.sync_to_guardian()
                return self.existing_account

        elif self.request_type == self.RequestType.DELETE:
            # 削除
            if self.existing_account:
                was_primary = self.existing_account.is_primary
                self.existing_account.is_active = False
                self.existing_account.is_primary = False
                self.existing_account.save()

                # メイン口座だった場合、Guardianの情報をクリア
                if was_primary:
                    self.guardian.bank_name = ''
                    self.guardian.bank_code = ''
                    self.guardian.branch_name = ''
                    self.guardian.branch_code = ''
                    self.guardian.account_type = 'ordinary'
                    self.guardian.account_number = ''
                    self.guardian.account_holder = ''
                    self.guardian.account_holder_kana = ''
                    self.guardian.payment_registered = False
                    self.guardian.payment_registered_at = None
                    self.guardian.save()

        return None

    def reject(self, user, notes=''):
        """銀行口座申請を却下"""
        from django.utils import timezone
        self.status = self.Status.REJECTED
        self.processed_by = user
        self.processed_at = timezone.now()
        self.process_notes = notes
        self.save()
