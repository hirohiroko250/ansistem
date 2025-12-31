"""
School Model - 校舎マスタ
"""
import uuid
from django.db import models
from apps.core.models import TenantModel


class School(TenantModel):
    """T10: 校舎マスタ"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_code = models.CharField('校舎コード', max_length=20)
    school_name = models.CharField('校舎名', max_length=100)
    school_name_romaji = models.CharField('校舎ローマ字名', max_length=100, blank=True)
    school_name_short = models.CharField('校舎名略称', max_length=50, blank=True)
    school_type = models.CharField('校舎種別', max_length=20, blank=True)  # 本校, 分校等

    # 連絡先
    postal_code = models.CharField('郵便番号', max_length=10, blank=True)
    prefecture = models.CharField('都道府県', max_length=10, blank=True)
    city = models.CharField('市区町村', max_length=50, blank=True)
    address1 = models.CharField('住所1', max_length=100, blank=True)
    address2 = models.CharField('住所2', max_length=100, blank=True)
    address3 = models.CharField('住所3', max_length=100, blank=True)
    address_en1 = models.CharField('住所英語1', max_length=200, blank=True)
    address_en2 = models.CharField('住所英語2', max_length=200, blank=True)
    phone = models.CharField('電話番号', max_length=20, blank=True)
    fax = models.CharField('FAX番号', max_length=20, blank=True)
    email = models.EmailField('メールアドレス', blank=True)

    # 位置情報
    latitude = models.DecimalField('緯度', max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField('経度', max_digits=10, decimal_places=7, null=True, blank=True)
    geofence_range = models.DecimalField('ジオフェンス範囲(km)', max_digits=5, decimal_places=2, null=True, blank=True)
    map_link = models.URLField('Map Link', blank=True)
    map_pin = models.URLField('MAP Pin', blank=True)

    # 地区情報
    district_name = models.CharField('地区名', max_length=50, blank=True)
    district_no = models.CharField('地区No', max_length=20, blank=True)

    # 部屋・駐車場情報
    room_count = models.IntegerField('部屋数', null=True, blank=True)
    teacher_parking = models.CharField('教師用駐車場', max_length=100, blank=True)
    customer_parking = models.CharField('顧客用駐車場', max_length=100, blank=True)

    # 建物情報
    building_ownership = models.CharField('建物所有権', max_length=50, blank=True)
    building_owner_info = models.TextField('建物オーナー情報', blank=True)
    management_company = models.TextField('管理会社', blank=True)
    key_number = models.CharField('キー番号', max_length=50, blank=True)
    padlock = models.CharField('パドロック', max_length=100, blank=True)

    # 営業情報
    capacity = models.IntegerField('定員', null=True, blank=True)
    opening_date = models.DateField('開校日', null=True, blank=True)
    transfer_date1 = models.DateField('校舎移転日1', null=True, blank=True)
    transfer_date2 = models.DateField('校舎移転日2', null=True, blank=True)
    transfer_date3 = models.DateField('校舎移転日3', null=True, blank=True)
    closing_date = models.DateField('閉校日', null=True, blank=True)

    # インターネット・PC情報
    internet_id = models.CharField('インターネットID', max_length=100, blank=True)
    internet_password = models.CharField('インターネットパスワード', max_length=100, blank=True)
    pc_account = models.CharField('PCアカウント', max_length=100, blank=True)
    pc_password = models.CharField('PCパスワード', max_length=100, blank=True)
    email_password = models.CharField('メールパスワード', max_length=100, blank=True)
    website = models.URLField('ウェブサイト', blank=True)

    # メモ・備考
    notes = models.TextField('メモ', blank=True)

    # 設定
    settings = models.JSONField('校舎設定', default=dict, blank=True)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't10_schools'
        verbose_name = 'T10_校舎'
        verbose_name_plural = 'T10_校舎'
        ordering = ['sort_order', 'school_code']
        unique_together = ['tenant_id', 'school_code']

    def __str__(self):
        return f"{self.school_name} ({self.school_code})"
