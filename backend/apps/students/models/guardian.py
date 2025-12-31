"""
Guardian Model - 保護者マスタ
"""
import uuid
from django.db import models
from apps.core.models import TenantModel


class Guardian(TenantModel):
    """T2: 保護者マスタ"""

    class Relationship(models.TextChoices):
        FATHER = 'father', '父'
        MOTHER = 'mother', '母'
        GRANDFATHER = 'grandfather', '祖父'
        GRANDMOTHER = 'grandmother', '祖母'
        SIBLING = 'sibling', '兄弟姉妹'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    guardian_no = models.CharField('保護者番号', max_length=20, blank=True)
    old_id = models.CharField('旧システムID', max_length=50, blank=True, db_index=True)

    @classmethod
    def generate_guardian_no(cls):
        """8で始まる8桁の保護者番号を自動生成（8XXXXXXX）"""
        import random
        while True:
            # 8で始まる8桁の数字を生成（80000000〜89999999）
            guardian_no = str(random.randint(80000000, 89999999))
            # 既存の番号と旧システムIDの両方と重複しないかチェック
            if not cls.objects.filter(guardian_no=guardian_no).exists() and \
               not cls.objects.filter(old_id=guardian_no).exists():
                return guardian_no

    def save(self, *args, **kwargs):
        # 新規作成時にguardian_noが空なら自動発番
        if not self.guardian_no:
            self.guardian_no = self.generate_guardian_no()
        super().save(*args, **kwargs)

    # 基本情報
    last_name = models.CharField('姓', max_length=50)
    first_name = models.CharField('名', max_length=50)
    last_name_kana = models.CharField('姓（カナ）', max_length=50, blank=True)
    first_name_kana = models.CharField('名（カナ）', max_length=50, blank=True)
    last_name_roman = models.CharField('姓（ローマ字）', max_length=50, blank=True)
    first_name_roman = models.CharField('名（ローマ字）', max_length=50, blank=True)
    birth_date = models.DateField('生年月日', null=True, blank=True)

    # 連絡先
    email = models.EmailField('メールアドレス', blank=True)
    phone = models.CharField('電話番号', max_length=20, blank=True)
    phone_mobile = models.CharField('携帯電話', max_length=20, blank=True)
    line_id = models.CharField('LINE ID', max_length=50, blank=True)

    # 住所
    postal_code = models.CharField('郵便番号', max_length=8, blank=True)
    prefecture = models.CharField('都道府県', max_length=10, blank=True)
    city = models.CharField('市区町村', max_length=50, blank=True)
    address1 = models.CharField('住所1', max_length=100, blank=True)
    address2 = models.CharField('住所2', max_length=100, blank=True)

    # 勤務先
    workplace = models.CharField('勤務先', max_length=100, blank=True)
    workplace_phone = models.CharField('勤務先電話番号', max_length=20, blank=True)
    workplace2 = models.CharField('勤務先2', max_length=100, blank=True)
    workplace_phone2 = models.CharField('勤務先2電話番号', max_length=20, blank=True)

    # 支払い情報（銀行口座）
    bank_name = models.CharField('金融機関名', max_length=100, blank=True)
    bank_code = models.CharField('金融機関コード', max_length=4, blank=True)
    branch_name = models.CharField('支店名', max_length=100, blank=True)
    branch_code = models.CharField('支店コード', max_length=3, blank=True)
    account_type = models.CharField(
        '口座種別',
        max_length=10,
        choices=[('ordinary', '普通'), ('current', '当座'), ('savings', '貯蓄')],
        default='ordinary',
        blank=True
    )
    account_number = models.CharField('口座番号', max_length=8, blank=True)
    account_holder = models.CharField('口座名義', max_length=100, blank=True)
    account_holder_kana = models.CharField('口座名義（カナ）', max_length=100, blank=True)

    # 引き落とし設定
    class PaymentProvider(models.TextChoices):
        JACCS = 'jaccs', 'JACCS'
        UFJ_FACTOR = 'ufjfactors', 'UFJファクター'
        CHUKYO_FINANCE = 'chukyo_finance', '中京ファイナンス'
        NONE = '', '未設定'

    payment_provider = models.CharField(
        '決済代行会社',
        max_length=20,
        choices=PaymentProvider.choices,
        default='',
        blank=True,
        help_text='口座振替の決済代行会社（JACCS/UFJファクター等）'
    )
    debit_start_date = models.CharField('引落開始月', max_length=10, blank=True, help_text='YYYY/MM形式')
    withdrawal_day = models.IntegerField('引き落とし日', null=True, blank=True)  # 毎月何日
    payment_registered = models.BooleanField('支払い方法登録済み', default=False)
    payment_registered_at = models.DateTimeField('支払い方法登録日時', null=True, blank=True)

    # ユーザーアカウント連携
    user = models.OneToOneField(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='guardian_profile',
        verbose_name='ユーザーアカウント'
    )

    # 登録時追加情報
    nearest_school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='nearby_guardians',
        verbose_name='最寄り校舎'
    )
    interested_brands = models.JSONField('興味のあるブランド', default=list, blank=True)
    referral_source = models.CharField('紹介元', max_length=50, blank=True)
    expectations = models.TextField('期待・要望', blank=True)

    # メタ情報
    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 't01_guardians'
        verbose_name = 'T1_保護者'
        verbose_name_plural = 'T1_保護者'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}"

    @property
    def full_name_kana(self):
        return f"{self.last_name_kana} {self.first_name_kana}".strip()

    @property
    def is_employee(self) -> bool:
        """この保護者が社員かどうか"""
        return hasattr(self, 'employees') and self.employees.filter(
            is_active=True, deleted_at__isnull=True
        ).exists()

    @property
    def employee(self):
        """紐付いている社員情報を取得（アクティブなもの）"""
        if hasattr(self, 'employees'):
            return self.employees.filter(
                is_active=True, deleted_at__isnull=True
            ).first()
        return None

    @property
    def employee_discount_info(self):
        """社員割引情報を取得"""
        emp = self.employee
        if emp and emp.discount_flag:
            return {
                'has_discount': True,
                'amount': emp.discount_amount,
                'unit': emp.discount_unit,
                'category_name': emp.discount_category_name,
                'category_code': emp.discount_category_code,
            }
        return {'has_discount': False}
