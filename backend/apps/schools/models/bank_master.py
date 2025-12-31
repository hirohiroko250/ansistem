"""
Bank Master Models - 金融機関マスタ
BankType, Bank, BankBranch
"""
import uuid
from django.db import models
from apps.core.models import TenantModel


class BankType(TenantModel):
    """金融機関種別マスタ"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type_code = models.CharField('種別コード', max_length=10)  # 00200, 01100 など
    type_name = models.CharField('種別名', max_length=50)  # 都市銀行, 信用金庫
    type_label = models.CharField('表示名', max_length=20)  # 都市銀行, 信金
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'bank_types'
        verbose_name = '金融機関種別'
        verbose_name_plural = '金融機関種別'
        ordering = ['sort_order']
        unique_together = ['tenant_id', 'type_code']

    def __str__(self):
        return f"{self.type_name} ({self.type_code})"


class Bank(TenantModel):
    """金融機関マスタ"""

    class AiueoRow(models.TextChoices):
        A = 'あ', 'あ行'
        KA = 'か', 'か行'
        SA = 'さ', 'さ行'
        TA = 'た', 'た行'
        NA = 'な', 'な行'
        HA = 'は', 'は行'
        MA = 'ま', 'ま行'
        YA = 'や', 'や行'
        RA = 'ら', 'ら行'
        WA = 'わ', 'わ行'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank_code = models.CharField('金融機関コード', max_length=10, db_index=True)
    bank_name = models.CharField('金融機関名', max_length=100)
    bank_name_kana = models.CharField('金融機関名カナ', max_length=100, blank=True)
    bank_name_half_kana = models.CharField('金融機関名半角カナ', max_length=100, blank=True)
    bank_name_hiragana = models.CharField('金融機関名ひらがな', max_length=100, blank=True)
    aiueo_row = models.CharField(
        'あいうえお行',
        max_length=2,
        choices=AiueoRow.choices,
        blank=True,
        db_index=True,
        help_text='頭文字の行（あ行、か行...）'
    )

    bank_type = models.ForeignKey(
        BankType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='banks',
        verbose_name='金融機関種別'
    )

    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'banks'
        verbose_name = '金融機関'
        verbose_name_plural = '金融機関'
        ordering = ['sort_order', 'bank_name_hiragana']
        unique_together = ['tenant_id', 'bank_code']

    def __str__(self):
        return f"{self.bank_name} ({self.bank_code})"

    def save(self, *args, **kwargs):
        """保存時にあいうえお行を自動設定"""
        if self.bank_name_hiragana and not self.aiueo_row:
            self.aiueo_row = self._get_aiueo_row(self.bank_name_hiragana)
        super().save(*args, **kwargs)

    @staticmethod
    def _get_aiueo_row(hiragana: str) -> str:
        """ひらがなの最初の文字からあいうえお行を判定"""
        if not hiragana:
            return ''
        first_char = hiragana[0]
        # 濁音・半濁音を清音に変換
        dakuon_map = {
            'が': 'か', 'ぎ': 'か', 'ぐ': 'か', 'げ': 'か', 'ご': 'か',
            'ざ': 'さ', 'じ': 'さ', 'ず': 'さ', 'ぜ': 'さ', 'ぞ': 'さ',
            'だ': 'た', 'ぢ': 'た', 'づ': 'た', 'で': 'た', 'ど': 'た',
            'ば': 'は', 'び': 'は', 'ぶ': 'は', 'べ': 'は', 'ぼ': 'は',
            'ぱ': 'は', 'ぴ': 'は', 'ぷ': 'は', 'ぺ': 'は', 'ぽ': 'は',
        }
        first_char = dakuon_map.get(first_char, first_char)

        if first_char in 'あいうえお':
            return 'あ'
        elif first_char in 'かきくけこ':
            return 'か'
        elif first_char in 'さしすせそ':
            return 'さ'
        elif first_char in 'たちつてと':
            return 'た'
        elif first_char in 'なにぬねの':
            return 'な'
        elif first_char in 'はひふへほ':
            return 'は'
        elif first_char in 'まみむめも':
            return 'ま'
        elif first_char in 'やゆよ':
            return 'や'
        elif first_char in 'らりるれろ':
            return 'ら'
        elif first_char in 'わをん':
            return 'わ'
        return ''


class BankBranch(TenantModel):
    """支店マスタ"""

    class AiueoRow(models.TextChoices):
        A = 'あ', 'あ行'
        KA = 'か', 'か行'
        SA = 'さ', 'さ行'
        TA = 'た', 'た行'
        NA = 'な', 'な行'
        HA = 'は', 'は行'
        MA = 'ま', 'ま行'
        YA = 'や', 'や行'
        RA = 'ら', 'ら行'
        WA = 'わ', 'わ行'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank = models.ForeignKey(
        Bank,
        on_delete=models.CASCADE,
        related_name='branches',
        verbose_name='金融機関'
    )
    branch_code = models.CharField('支店コード', max_length=10, db_index=True)
    branch_name = models.CharField('支店名', max_length=100)
    branch_name_kana = models.CharField('支店名カナ', max_length=100, blank=True)
    branch_name_half_kana = models.CharField('支店名半角カナ', max_length=100, blank=True)
    branch_name_hiragana = models.CharField('支店名ひらがな', max_length=100, blank=True)
    aiueo_row = models.CharField(
        'あいうえお行',
        max_length=2,
        choices=AiueoRow.choices,
        blank=True,
        db_index=True,
        help_text='頭文字の行（あ行、か行...）'
    )

    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'bank_branches'
        verbose_name = '金融機関支店'
        verbose_name_plural = '金融機関支店'
        ordering = ['sort_order', 'branch_name_hiragana']
        unique_together = ['bank', 'branch_code']

    def __str__(self):
        return f"{self.bank.bank_name} {self.branch_name} ({self.branch_code})"

    def save(self, *args, **kwargs):
        """保存時にあいうえお行を自動設定"""
        if self.branch_name_hiragana and not self.aiueo_row:
            self.aiueo_row = Bank._get_aiueo_row(self.branch_name_hiragana)
        super().save(*args, **kwargs)
