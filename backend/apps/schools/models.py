"""
Schools Models
T12: ブランドマスタ
T10: 校舎マスタ
T11: ルーム（教室）マスタ
T17: 学年マスタ
"""
import uuid
from django.db import models
from apps.core.models import TenantModel


class BrandCategory(TenantModel):
    """T12c: ブランドカテゴリマスタ（ブランドを統合するカテゴリ）"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category_code = models.CharField('カテゴリコード', max_length=20)
    category_name = models.CharField('カテゴリ名', max_length=100)
    category_name_short = models.CharField('カテゴリ名略称', max_length=50, blank=True)
    description = models.TextField('説明', blank=True)
    logo_url = models.URLField('ロゴURL', blank=True)
    color_primary = models.CharField('プライマリカラー', max_length=7, blank=True)  # #RRGGBB
    color_secondary = models.CharField('セカンダリカラー', max_length=7, blank=True)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't12c_brand_categories'
        verbose_name = 'T12c_ブランドカテゴリ'
        verbose_name_plural = 'T12c_ブランドカテゴリ'
        ordering = ['sort_order', 'category_code']
        unique_together = ['tenant_id', 'category_code']

    def __str__(self):
        return f"{self.category_name} ({self.category_code})"


class Brand(TenantModel):
    """T12: ブランドマスタ"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand_code = models.CharField('ブランドコード', max_length=20)
    brand_name = models.CharField('ブランド名', max_length=100)
    brand_name_short = models.CharField('ブランド名略称', max_length=50, blank=True)
    brand_type = models.CharField('ブランド種別', max_length=20, blank=True)  # 個別指導, 集団授業等
    # ブランドカテゴリ（統合表示用）
    category = models.ForeignKey(
        BrandCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='brands',
        verbose_name='ブランドカテゴリ'
    )
    description = models.TextField('説明', blank=True)
    logo_url = models.URLField('ロゴURL', blank=True)
    color_primary = models.CharField('プライマリカラー', max_length=7, blank=True)  # #RRGGBB
    color_secondary = models.CharField('セカンダリカラー', max_length=7, blank=True)

    # 学年更新設定
    grade_update_month = models.IntegerField(
        '学年更新月',
        default=4,
        help_text='学年が上がる月（1-12）。例：4月なら4'
    )
    grade_update_day = models.IntegerField(
        '学年更新日',
        default=1,
        help_text='学年が上がる日（1-31）。例：1日なら1'
    )

    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't12_brands'
        verbose_name = 'T12_ブランド'
        verbose_name_plural = 'T12_ブランド'
        ordering = ['sort_order', 'brand_code']
        unique_together = ['tenant_id', 'brand_code']

    def __str__(self):
        return f"{self.brand_name} ({self.brand_code})"

    def get_grade_update_date(self, year):
        """指定年の学年更新日を取得"""
        from datetime import date
        return date(year, self.grade_update_month, self.grade_update_day)

    def calculate_school_year(self, birth_date, target_date=None):
        """
        生年月日から現在の学年を計算

        Args:
            birth_date: 生年月日
            target_date: 判定日（デフォルト: 今日）

        Returns:
            SchoolYear オブジェクト or None
        """
        from datetime import date

        if target_date is None:
            target_date = date.today()

        if not birth_date:
            return None

        # 基準となる年度開始日（今年度 or 前年度）
        grade_update_this_year = self.get_grade_update_date(target_date.year)

        if target_date >= grade_update_this_year:
            # 今年度の更新日以降 → 今年度
            fiscal_year = target_date.year
        else:
            # 今年度の更新日より前 → 前年度
            fiscal_year = target_date.year - 1

        # 年度開始時点での年齢を計算
        grade_update_date = self.get_grade_update_date(fiscal_year)
        age_at_update = grade_update_date.year - birth_date.year

        # 誕生日がまだ来ていない場合は1歳引く
        if (grade_update_date.month, grade_update_date.day) < (birth_date.month, birth_date.day):
            age_at_update -= 1

        # 年齢から学年を判定
        # 6歳 → 小1, 7歳 → 小2, ...
        school_year_code = None
        if age_at_update < 1:
            school_year_code = 'Y01'  # 0-1歳児
        elif age_at_update < 2:
            school_year_code = 'Y02'  # 1-2歳児
        elif age_at_update < 3:
            school_year_code = 'Y03'  # 2-3歳児
        elif age_at_update < 4:
            school_year_code = 'Y04'  # 年少
        elif age_at_update < 5:
            school_year_code = 'Y05'  # 年中
        elif age_at_update < 6:
            school_year_code = 'Y06'  # 年長
        elif age_at_update < 7:
            school_year_code = 'Y07'  # 小１
        elif age_at_update < 8:
            school_year_code = 'Y08'  # 小２
        elif age_at_update < 9:
            school_year_code = 'Y09'  # 小３
        elif age_at_update < 10:
            school_year_code = 'Y10'  # 小４
        elif age_at_update < 11:
            school_year_code = 'Y11'  # 小５
        elif age_at_update < 12:
            school_year_code = 'Y12'  # 小６
        elif age_at_update < 13:
            school_year_code = 'Y13'  # 中１
        elif age_at_update < 14:
            school_year_code = 'Y14'  # 中２
        elif age_at_update < 15:
            school_year_code = 'Y15'  # 中３
        elif age_at_update < 16:
            school_year_code = 'Y16'  # 高１
        elif age_at_update < 17:
            school_year_code = 'Y17'  # 高２
        elif age_at_update < 18:
            school_year_code = 'Y18'  # 高３
        else:
            school_year_code = 'Y23'  # 社会人

        try:
            return SchoolYear.objects.get(
                tenant_id=self.tenant_id,
                year_code=school_year_code
            )
        except SchoolYear.DoesNotExist:
            return None


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


class BrandSchool(TenantModel):
    """T12a: ブランド開講校舎（ブランドごとの開講校舎を管理）"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name='brand_schools',
        verbose_name='ブランド'
    )
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='brand_schools',
        verbose_name='校舎'
    )
    is_main = models.BooleanField('メイン校舎', default=False, help_text='このブランドのメイン校舎かどうか')
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't12a_brand_schools'
        verbose_name = 'T12a_ブランド開講校舎'
        verbose_name_plural = 'T12a_ブランド開講校舎'
        ordering = ['brand', 'sort_order', 'school__school_name']
        unique_together = ['tenant_id', 'brand', 'school']

    def __str__(self):
        return f"{self.brand.brand_name} - {self.school.school_name}"


class SchoolYear(TenantModel):
    """T17a: 単一学年マスタ（0-1歳児、年少、小１、中１、高１、大１、社会人など23種類）"""

    class YearCategory(models.TextChoices):
        INFANT = 'infant', '乳幼児'
        PRESCHOOL = 'preschool', '未就学児'
        ELEMENTARY = 'elementary', '小学生'
        JUNIOR_HIGH = 'junior_high', '中学生'
        HIGH_SCHOOL = 'high_school', '高校生'
        UNIVERSITY = 'university', '大学生'
        ADULT = 'adult', '社会人'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    year_code = models.CharField('学年コード', max_length=10)
    year_name = models.CharField('学年名', max_length=20)
    category = models.CharField(
        'カテゴリ',
        max_length=20,
        choices=YearCategory.choices,
        default=YearCategory.ELEMENTARY
    )
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't17a_school_years'
        verbose_name = 'T17a_単一学年'
        verbose_name_plural = 'T17a_単一学年'
        ordering = ['sort_order']
        unique_together = ['tenant_id', 'year_code']

    def __str__(self):
        return self.year_name


class Grade(TenantModel):
    """T17: 対象学年定義（単一学年の組み合わせ）"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grade_code = models.CharField('学年コード', max_length=10)
    grade_name = models.CharField('対象学年名', max_length=50)
    grade_name_short = models.CharField('略称', max_length=20, blank=True)

    # 単一学年との多対多関係
    school_years = models.ManyToManyField(
        SchoolYear,
        through='GradeSchoolYear',
        related_name='grades',
        verbose_name='対象学年'
    )

    category = models.CharField('カテゴリ', max_length=20, blank=True)
    school_year = models.IntegerField('学校学年', null=True, blank=True)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't17_grades'
        verbose_name = 'T17_対象学年定義'
        verbose_name_plural = 'T17_対象学年定義'
        ordering = ['sort_order', 'grade_code']
        unique_together = ['tenant_id', 'grade_code']

    def __str__(self):
        return f"{self.grade_name} ({self.grade_code})"

    def get_school_year_names(self):
        """対象学年の一覧を取得"""
        return ', '.join([sy.year_name for sy in self.school_years.all()])


class GradeSchoolYear(TenantModel):
    """T17b: 対象学年と単一学年の中間テーブル"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grade = models.ForeignKey(
        Grade,
        on_delete=models.CASCADE,
        related_name='grade_school_years',
        verbose_name='対象学年'
    )
    school_year = models.ForeignKey(
        SchoolYear,
        on_delete=models.CASCADE,
        related_name='grade_school_years',
        verbose_name='単一学年'
    )

    class Meta:
        db_table = 't17b_grade_school_years'
        verbose_name = 'T17b_対象学年_単一学年'
        verbose_name_plural = 'T17b_対象学年_単一学年'
        unique_together = ['tenant_id', 'grade', 'school_year']

    def __str__(self):
        return f"{self.grade.grade_name} - {self.school_year.year_name}"


class Subject(TenantModel):
    """教科マスタ"""

    class SubjectCategory(models.TextChoices):
        MAIN = 'main', '主要教科'
        SUB = 'sub', '副教科'
        SPECIAL = 'special', '特別講座'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject_code = models.CharField('教科コード', max_length=20)
    subject_name = models.CharField('教科名', max_length=50)
    subject_name_short = models.CharField('教科名略称', max_length=20, blank=True)
    category = models.CharField(
        '教科カテゴリ',
        max_length=20,
        choices=SubjectCategory.choices,
        default=SubjectCategory.MAIN
    )
    # ブランド紐付け
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name='subjects',
        verbose_name='ブランド',
        null=True,
        blank=True
    )
    color = models.CharField('表示色', max_length=7, blank=True)  # #RRGGBB
    icon = models.CharField('アイコン', max_length=50, blank=True)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'subjects'
        verbose_name = '教科'
        verbose_name_plural = '教科'
        ordering = ['sort_order', 'subject_code']
        unique_together = ['tenant_id', 'subject_code']

    def __str__(self):
        return f"{self.subject_name} ({self.subject_code})"


class Classroom(TenantModel):
    """T11: ルーム（教室）マスタ"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='classrooms',
        verbose_name='校舎'
    )
    classroom_code = models.CharField('教室コード', max_length=20)
    classroom_name = models.CharField('教室名', max_length=50)
    capacity = models.IntegerField('Room定員', default=1)
    floor = models.CharField('階数', max_length=10, blank=True)
    room_type = models.CharField('教室種別', max_length=20, blank=True)  # 個別ブース, 集団教室等
    equipment = models.JSONField('設備', default=list, blank=True)  # ["PC", "プロジェクター"]
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't11_classrooms'
        verbose_name = 'T11_教室'
        verbose_name_plural = 'T11_教室'
        ordering = ['sort_order', 'classroom_code']
        unique_together = ['school', 'classroom_code']

    def __str__(self):
        return f"{self.school.school_name} - {self.classroom_name}"


class TimeSlot(TenantModel):
    """T13: 時間帯マスタ"""

    class DayOfWeek(models.IntegerChoices):
        MONDAY = 1, '月曜日'
        TUESDAY = 2, '火曜日'
        WEDNESDAY = 3, '水曜日'
        THURSDAY = 4, '木曜日'
        FRIDAY = 5, '金曜日'
        SATURDAY = 6, '土曜日'
        SUNDAY = 7, '日曜日'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        'School',
        on_delete=models.CASCADE,
        related_name='school_time_slots',
        verbose_name='校舎',
        null=True,
        blank=True,
    )
    day_of_week = models.IntegerField(
        '曜日',
        choices=DayOfWeek.choices,
        null=True,
        blank=True,
    )
    slot_code = models.CharField('時間帯コード', max_length=20)
    slot_name = models.CharField('時間帯名', max_length=50)  # 例: "1限", "A枠"
    start_time = models.TimeField('開始時刻')
    end_time = models.TimeField('終了時刻')
    duration_minutes = models.IntegerField('時間（分）', default=50)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't13_time_slots'
        verbose_name = 'T13_時間帯'
        verbose_name_plural = 'T13_時間帯'
        ordering = ['school', 'day_of_week', 'sort_order', 'start_time']

    def __str__(self):
        day_str = self.get_day_of_week_display() if self.day_of_week else ''
        school_str = self.school.school_name if self.school else ''
        return f"{school_str} {day_str} {self.slot_name} ({self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')})"


class SchoolSchedule(TenantModel):
    """T14: 校舎開講スケジュール（ブランド×校舎×曜日×時間帯で開講を管理）"""

    class DayOfWeek(models.IntegerChoices):
        MONDAY = 1, '月曜日'
        TUESDAY = 2, '火曜日'
        WEDNESDAY = 3, '水曜日'
        THURSDAY = 4, '木曜日'
        FRIDAY = 5, '金曜日'
        SATURDAY = 6, '土曜日'
        SUNDAY = 7, '日曜日'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='ブランド'
    )
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='校舎'
    )
    day_of_week = models.IntegerField(
        '曜日',
        choices=DayOfWeek.choices
    )
    time_slot = models.ForeignKey(
        TimeSlot,
        on_delete=models.PROTECT,
        related_name='schedules',
        verbose_name='時間帯'
    )
    # 席数管理
    capacity = models.IntegerField('定員（席数）', default=10)
    trial_capacity = models.IntegerField('体験受入可能数', default=2)
    reserved_seats = models.IntegerField('予約済み席数', default=0)  # キャッシュ用
    pause_seat_fee = models.DecimalField('休会時座席料金', max_digits=10, decimal_places=0, default=0)

    # カレンダーマスター参照（新規）
    calendar_master = models.ForeignKey(
        'CalendarMaster',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='class_schedules',
        verbose_name='カレンダーマスター'
    )

    # カレンダーパターン（後方互換用）
    calendar_pattern = models.CharField(
        'カレンダーパターン',
        max_length=50,
        blank=True,
        help_text='例: 1001_AEC_A, 1002_AEC_B, 1003_AEC_P'
    )

    # 期間（年度や特定期間のみ開講の場合）
    valid_from = models.DateField('有効開始日', null=True, blank=True)
    valid_until = models.DateField('有効終了日', null=True, blank=True)

    notes = models.TextField('備考', blank=True)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't14_school_schedules'
        verbose_name = 'T14_校舎開講スケジュール'
        verbose_name_plural = 'T14_校舎開講スケジュール'
        ordering = ['school', 'day_of_week', 'time_slot__start_time']
        unique_together = ['brand', 'school', 'day_of_week', 'time_slot']

    def __str__(self):
        return f"{self.school.school_name} {self.get_day_of_week_display()} {self.time_slot.slot_name}"

    @property
    def available_seats(self):
        """空き席数"""
        return max(0, self.capacity - self.reserved_seats)

    def is_available(self):
        """予約可能かどうか"""
        return self.is_active and self.available_seats > 0


class ClassSchedule(TenantModel):
    """T14c: 開講時間割（クラス登録・振替のベースとなるマスタ）

    エクセル「T14_開講時間割_ 時間割Group版」に対応
    校舎×ブランド×曜日×時限でクラスを定義
    """

    class DayOfWeek(models.IntegerChoices):
        MONDAY = 1, '月曜日'
        TUESDAY = 2, '火曜日'
        WEDNESDAY = 3, '水曜日'
        THURSDAY = 4, '木曜日'
        FRIDAY = 5, '金曜日'
        SATURDAY = 6, '土曜日'
        SUNDAY = 7, '日曜日'

    class ApprovalType(models.IntegerChoices):
        AUTO = 1, '自動承認'
        MANUAL = 2, '承認制'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 時間割ID（エクセルの「社内時間割ID」に対応）
    schedule_code = models.CharField(
        '時間割コード',
        max_length=50,
        help_text='例: 尾張旭月4_Ti10000025'
    )

    # 基本情報
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='class_schedules',
        verbose_name='校舎'
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name='class_schedules',
        verbose_name='ブランド'
    )
    brand_category = models.ForeignKey(
        BrandCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='class_schedules',
        verbose_name='ブランドカテゴリ'
    )

    # 曜日・時間
    day_of_week = models.IntegerField(
        '曜日',
        choices=DayOfWeek.choices
    )
    period = models.IntegerField(
        '時限',
        help_text='1, 2, 3...（V表示時限）'
    )
    start_time = models.TimeField('開始時間')
    duration_minutes = models.IntegerField(
        '授業時間（分）',
        default=50
    )
    end_time = models.TimeField('終了時間')
    break_time = models.TimeField(
        '休憩時間',
        null=True,
        blank=True,
        help_text='当日の休憩時間'
    )

    # クラス情報
    class_name = models.CharField(
        'クラス名',
        max_length=100,
        help_text='例: Purple ペア'
    )
    class_type = models.CharField(
        'クラス種名',
        max_length=50,
        blank=True,
        help_text='例: Purpleペア'
    )

    # 保護者向け表示
    display_course_name = models.CharField(
        '保護者用コース名',
        max_length=200,
        blank=True,
        help_text='例: ④小５以上(英語歴5年以上)'
    )
    display_pair_name = models.CharField(
        '保護者用ペア名',
        max_length=100,
        blank=True,
        help_text='例: Purple_ペア'
    )
    display_description = models.TextField(
        '保護者用説明',
        blank=True,
        help_text='例: 【通称】:Purpleクラス【対象】④小５以上...'
    )

    # チケット関連
    ticket_name = models.CharField(
        'チケット名',
        max_length=100,
        blank=True,
        help_text='例: Purple ペア　50分×週1回'
    )
    ticket_id = models.CharField(
        'チケットID',
        max_length=50,
        blank=True,
        help_text='例: Ti10000025'
    )

    # 振替・グループ
    transfer_group = models.CharField(
        '振替グループ',
        max_length=50,
        blank=True,
        help_text='同じグループ内で振替可能'
    )
    schedule_group = models.CharField(
        '時間割グループ',
        max_length=50,
        blank=True
    )

    # 席数・定員
    capacity = models.IntegerField('定員', default=12)
    trial_capacity = models.IntegerField('体験受入可能数', default=2)
    reserved_seats = models.IntegerField('予約済み席数', default=0)
    pause_seat_fee = models.DecimalField(
        '休会時座席料金',
        max_digits=10,
        decimal_places=0,
        default=0
    )

    # カレンダーマスター参照
    calendar_master = models.ForeignKey(
        'CalendarMaster',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='class_schedules_t14c',
        verbose_name='カレンダーマスター'
    )

    # カレンダーパターン（後方互換用）
    calendar_pattern = models.CharField(
        'カレンダーパターン',
        max_length=50,
        blank=True,
        help_text='例: 1003_AEC_P'
    )

    # 承認設定
    approval_type = models.IntegerField(
        '承認種別',
        choices=ApprovalType.choices,
        default=ApprovalType.AUTO
    )

    # 教室
    room = models.ForeignKey(
        Classroom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='class_schedules',
        verbose_name='教室'
    )
    room_name = models.CharField(
        '教室名',
        max_length=50,
        blank=True,
        help_text='Roomマスタにない場合の教室名'
    )

    # 期間
    display_start_date = models.DateField(
        '保護者表示開始日',
        null=True,
        blank=True
    )
    class_start_date = models.DateField(
        'クラス開始日',
        null=True,
        blank=True
    )
    class_end_date = models.DateField(
        'クラス終了日',
        null=True,
        blank=True
    )

    # 対象学年
    grade = models.ForeignKey(
        Grade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='class_schedules',
        verbose_name='対象学年'
    )

    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't14c_class_schedules'
        verbose_name = 'T14c_開講時間割'
        verbose_name_plural = 'T14c_開講時間割'
        ordering = ['school', 'brand_category', 'brand', 'day_of_week', 'period']
        unique_together = ['tenant_id', 'schedule_code']

    def __str__(self):
        return f"{self.school.school_name} {self.get_day_of_week_display()} {self.period}限 {self.class_name}"

    @property
    def available_seats(self):
        """空き席数"""
        return max(0, self.capacity - self.reserved_seats)

    def is_available(self):
        """予約可能かどうか"""
        return self.is_active and self.available_seats > 0

    def is_transfer_compatible(self, other):
        """振替可能かどうか（同じ振替グループ内）"""
        if not self.transfer_group or not other.transfer_group:
            return False
        return self.transfer_group == other.transfer_group


class SchoolCourse(TenantModel):
    """T15: 校舎別コース開講設定（どの校舎でどのコースを開講するか）"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='school_courses',
        verbose_name='校舎'
    )
    course = models.ForeignKey(
        'contracts.Course',
        on_delete=models.CASCADE,
        related_name='school_courses',
        verbose_name='コース'
    )
    # 開講曜日・時間帯
    schedule = models.ForeignKey(
        SchoolSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='courses',
        verbose_name='開講スケジュール'
    )
    # コース固有の席数（スケジュールと別に設定する場合）
    capacity_override = models.IntegerField('席数上書き', null=True, blank=True)

    # 期間
    valid_from = models.DateField('開講開始日', null=True, blank=True)
    valid_until = models.DateField('開講終了日', null=True, blank=True)

    notes = models.TextField('備考', blank=True)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't15_school_courses'
        verbose_name = 'T15_校舎別コース'
        verbose_name_plural = 'T15_校舎別コース'
        ordering = ['school', 'course']
        unique_together = ['school', 'course', 'schedule']

    def __str__(self):
        return f"{self.school.school_name} - {self.course.course_name}"

    @property
    def effective_capacity(self):
        """有効な席数（上書きがあればそちらを使用）"""
        if self.capacity_override is not None:
            return self.capacity_override
        if self.schedule:
            return self.schedule.capacity
        return None


class SchoolClosure(TenantModel):
    """T16: 休講・休校マスタ（特定日の休講を管理）"""

    class ClosureType(models.TextChoices):
        SCHOOL_CLOSED = 'school_closed', '校舎休校'  # 校舎全体が休み
        BRAND_CLOSED = 'brand_closed', 'ブランド休講'  # 特定ブランドだけ休み
        SCHEDULE_CLOSED = 'schedule_closed', '時間帯休講'  # 特定時間帯だけ休み
        HOLIDAY = 'holiday', '祝日休講'
        MAINTENANCE = 'maintenance', 'メンテナンス'
        WEATHER = 'weather', '天候不良'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 休講の範囲指定（上から優先度順にチェック）
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='closures',
        verbose_name='校舎',
        null=True,
        blank=True,
        help_text='指定しない場合は全校舎'
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name='closures',
        verbose_name='ブランド',
        null=True,
        blank=True,
        help_text='指定しない場合は全ブランド'
    )
    schedule = models.ForeignKey(
        SchoolSchedule,
        on_delete=models.CASCADE,
        related_name='closures',
        verbose_name='スケジュール',
        null=True,
        blank=True,
        help_text='特定の曜日・時間帯のみ休講の場合'
    )

    # 休講日
    closure_date = models.DateField('休講日')
    closure_type = models.CharField(
        '休講種別',
        max_length=20,
        choices=ClosureType.choices,
        default=ClosureType.OTHER
    )

    # 振替授業の設定
    has_makeup = models.BooleanField('振替あり', default=False)
    makeup_date = models.DateField('振替日', null=True, blank=True)
    makeup_schedule = models.ForeignKey(
        SchoolSchedule,
        on_delete=models.SET_NULL,
        related_name='makeup_closures',
        verbose_name='振替スケジュール',
        null=True,
        blank=True
    )

    reason = models.CharField('休講理由', max_length=200, blank=True)
    notes = models.TextField('備考', blank=True)
    notified_at = models.DateTimeField('通知日時', null=True, blank=True)

    class Meta:
        db_table = 't16_school_closures'
        verbose_name = 'T16_休講'
        verbose_name_plural = 'T16_休講'
        ordering = ['-closure_date']

    def __str__(self):
        school_name = self.school.school_name if self.school else '全校舎'
        return f"{self.closure_date} {school_name} {self.get_closure_type_display()}"

    @classmethod
    def is_closed(cls, school, brand, date, time_slot=None):
        """指定日時が休講かどうかを判定"""
        from django.db.models import Q

        closures = cls.objects.filter(
            closure_date=date,
            tenant_id=school.tenant_id
        ).filter(
            # 校舎全体休校 OR 指定校舎休校
            Q(school__isnull=True) | Q(school=school)
        ).filter(
            # 全ブランド休講 OR 指定ブランド休講
            Q(brand__isnull=True) | Q(brand=brand)
        )

        if time_slot:
            closures = closures.filter(
                Q(schedule__isnull=True) | Q(schedule__time_slot=time_slot)
            )

        return closures.exists()


class CalendarMaster(TenantModel):
    """T13m: カレンダーマスター（カレンダーコードの定義）

    カレンダーコードの命名規則:
    - {校舎番号}_{ブランドコード}_{パターン}: 例 1001_SKAEC_A, 1003_AEC_P
    - {特殊コード}: 例 Int_24（インターナショナル）
    """

    class LessonType(models.TextChoices):
        TYPE_A = 'A', 'Aパターン（外国人講師あり）'
        TYPE_B = 'B', 'Bパターン（日本人講師のみ）'
        TYPE_P = 'P', 'Pパターン（ペア）'
        TYPE_Y = 'Y', 'Yパターン（インター）'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    code = models.CharField(
        'カレンダーコード',
        max_length=50,
        db_index=True,
        help_text='例: 1001_SKAEC_A, 1003_AEC_P, Int_24'
    )
    name = models.CharField('カレンダー名', max_length=100, blank=True)

    # ブランド紐付け
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='calendar_masters',
        verbose_name='ブランド'
    )

    # パターン
    lesson_type = models.CharField(
        '授業タイプ',
        max_length=10,
        choices=LessonType.choices,
        default=LessonType.TYPE_A
    )

    description = models.TextField('説明', blank=True)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't13m_calendar_masters'
        verbose_name = 'T13m_カレンダーマスター'
        verbose_name_plural = 'T13m_カレンダーマスター'
        ordering = ['sort_order', 'code']
        unique_together = ['tenant_id', 'code']

    def __str__(self):
        return f"{self.code} - {self.name or self.get_lesson_type_display()}"

    @classmethod
    def get_or_create_from_code(cls, tenant_id, code, brand=None):
        """カレンダーコードからマスターを取得または作成"""
        if not code:
            return None

        master, created = cls.objects.get_or_create(
            tenant_id=tenant_id,
            code=code,
            defaults={
                'brand': brand,
                'lesson_type': cls._detect_lesson_type(code),
                'name': code,
            }
        )
        return master

    @staticmethod
    def _detect_lesson_type(code):
        """コードからパターンを推測"""
        code_upper = code.upper()
        if code_upper.endswith('_A') or '_A_' in code_upper:
            return CalendarMaster.LessonType.TYPE_A
        elif code_upper.endswith('_B') or '_B_' in code_upper:
            return CalendarMaster.LessonType.TYPE_B
        elif code_upper.endswith('_P') or '_P_' in code_upper:
            return CalendarMaster.LessonType.TYPE_P
        elif 'INT' in code_upper or code_upper.endswith('_Y'):
            return CalendarMaster.LessonType.TYPE_Y
        return CalendarMaster.LessonType.OTHER


class LessonCalendar(TenantModel):
    """T13: 開講カレンダー（日別の開講情報を管理）

    テナント単位で管理（全校舎共通）
    カレンダーコードでパターンを識別:
    - 1001_SKAEC_A: Aパターン（外国人講師あり）
    - 1002_SKAEC_B: Bパターン（日本人講師のみ）
    - 1003_AEC_P: Pパターン（ペアクラス等）
    - Int_24: インターナショナル
    """

    class LessonType(models.TextChoices):
        TYPE_A = 'A', 'Aパターン（外国人講師あり）'
        TYPE_B = 'B', 'Bパターン（日本人講師のみ）'
        TYPE_P = 'P', 'Pパターン（ペア）'
        TYPE_Y = 'Y', 'Yパターン（インター）'
        CLOSED = 'closed', '休講'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # カレンダーマスター参照（新規）
    calendar_master = models.ForeignKey(
        CalendarMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_calendars',
        verbose_name='カレンダーマスター'
    )

    # カレンダー識別（後方互換用、calendar_masterから取得可能）
    calendar_code = models.CharField(
        'カレンダーコード',
        max_length=50,
        db_index=True,
        help_text='例: 1001_SKAEC_A, 1003_AEC_P, Int_24'
    )
    # ブランドは参照用（オプション）
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_calendars',
        verbose_name='ブランド'
    )
    # 校舎は不要（テナント全体で共通）だが後方互換性のため残す
    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_calendars',
        verbose_name='校舎（後方互換用）'
    )

    # 日付情報
    lesson_date = models.DateField('授業日')
    day_of_week = models.CharField('曜日', max_length=10)

    # 開講情報
    is_open = models.BooleanField('開講日', default=False)
    lesson_type = models.CharField(
        '授業タイプ',
        max_length=10,
        choices=LessonType.choices,
        default=LessonType.CLOSED
    )
    display_label = models.CharField(
        '保護者カレンダー表示',
        max_length=20,
        blank=True,
        help_text='例: 水A1, 木B2など'
    )

    # チケット情報
    ticket_type = models.CharField(
        'チケット券種',
        max_length=10,
        blank=True,
        help_text='A, Bなど'
    )
    ticket_sequence = models.IntegerField(
        'チケット番号',
        null=True,
        blank=True,
        help_text='月内の何回目か'
    )

    # 振替関連
    is_makeup_allowed = models.BooleanField('振替許可', default=True, help_text='振替拒否の場合はFalse')
    rejection_reason = models.CharField('振替拒否理由', max_length=100, blank=True)

    # チケット発券
    ticket_issue_count = models.IntegerField('権利発券数', null=True, blank=True, help_text='発行するチケット数')

    # 有効期限（チケットの有効期限など）
    valid_days = models.IntegerField('有効日数', default=90)

    # メッセージ
    notice_message = models.TextField('お知らせ', blank=True)
    auto_send_notice = models.BooleanField('自動お知らせ送信', default=False)
    holiday_name = models.CharField('祝日名', max_length=50, blank=True)

    class Meta:
        db_table = 't13_lesson_calendars'
        verbose_name = 'T13_開講カレンダー'
        verbose_name_plural = 'T13_開講カレンダー'
        ordering = ['calendar_code', 'lesson_date']
        # カレンダーコード + 日付でユニーク（テナント単位）
        unique_together = ['tenant_id', 'calendar_code', 'lesson_date']

    def __str__(self):
        return f"{self.calendar_code} {self.lesson_date} {self.lesson_type}"

    @property
    def is_native_day(self):
        """外国人講師がいる日かどうか"""
        return self.lesson_type == self.LessonType.TYPE_A

    @property
    def is_japanese_only(self):
        """日本人講師のみの日かどうか"""
        return self.lesson_type == self.LessonType.TYPE_B

    @classmethod
    def get_calendar_for_month(cls, tenant_id, brand_id, school_id, year, month):
        """指定月のカレンダーを取得"""
        from datetime import date
        import calendar

        # 月の開始日と終了日
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        return cls.objects.filter(
            tenant_id=tenant_id,
            brand_id=brand_id,
            school_id=school_id,
            lesson_date__gte=first_day,
            lesson_date__lte=last_day
        ).order_by('lesson_date')

    @classmethod
    def get_available_dates(cls, tenant_id, brand_id, school_id, year, month):
        """指定月の予約可能日を取得"""
        return cls.get_calendar_for_month(
            tenant_id, brand_id, school_id, year, month
        ).filter(is_open=True)


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


class CalendarOperationLog(TenantModel):
    """
    カレンダー操作ログ
    ABスワップ、休校設定などの操作履歴を記録
    """

    class OperationType(models.TextChoices):
        AB_SWAP = 'ab_swap', 'ABスワップ'
        SET_CLOSURE = 'set_closure', '休校設定'
        CANCEL_CLOSURE = 'cancel_closure', '休校解除'
        LESSON_TYPE_CHANGE = 'lesson_type_change', 'レッスンタイプ変更'
        SCHEDULE_CHANGE = 'schedule_change', 'スケジュール変更'
        STAFF_ABSENCE = 'staff_absence', 'スタッフ欠勤'
        NATIVE_ABSENCE = 'native_absence', '外国人欠勤'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    operation_type = models.CharField(
        '操作種別',
        max_length=30,
        choices=OperationType.choices
    )

    # 対象
    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operation_logs',
        verbose_name='校舎'
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operation_logs',
        verbose_name='ブランド'
    )
    schedule = models.ForeignKey(
        SchoolSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operation_logs',
        verbose_name='スケジュール'
    )
    lesson_calendar = models.ForeignKey(
        LessonCalendar,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operation_logs',
        verbose_name='開講カレンダー'
    )

    # 操作日時・対象日
    operation_date = models.DateField('対象日')
    operated_at = models.DateTimeField('操作日時', auto_now_add=True)

    # 操作者
    operated_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='calendar_operations',
        verbose_name='操作者'
    )

    # 変更内容
    old_value = models.CharField('変更前', max_length=100, blank=True)
    new_value = models.CharField('変更後', max_length=100, blank=True)
    reason = models.TextField('理由', blank=True)
    notes = models.TextField('備考', blank=True)

    # メタデータ
    metadata = models.JSONField('メタデータ', default=dict, blank=True)

    class Meta:
        db_table = 'calendar_operation_logs'
        verbose_name = 'カレンダー操作ログ'
        verbose_name_plural = 'カレンダー操作ログ'
        ordering = ['-operated_at']

    def __str__(self):
        return f"{self.get_operation_type_display()} - {self.operation_date} ({self.operated_at.strftime('%Y-%m-%d %H:%M')})"

    @classmethod
    def log_ab_swap(cls, tenant_id, school, brand, lesson_calendar, old_type, new_type, user=None, reason=''):
        """ABスワップをログに記録"""
        return cls.objects.create(
            tenant_id=tenant_id,
            operation_type=cls.OperationType.AB_SWAP,
            school=school,
            brand=brand,
            lesson_calendar=lesson_calendar,
            operation_date=lesson_calendar.lesson_date if lesson_calendar else None,
            operated_by=user,
            old_value=old_type,
            new_value=new_type,
            reason=reason,
            metadata={
                'calendar_code': lesson_calendar.calendar_code if lesson_calendar else None,
            }
        )

    @classmethod
    def log_closure(cls, tenant_id, closure, user=None):
        """休校設定をログに記録"""
        return cls.objects.create(
            tenant_id=tenant_id,
            operation_type=cls.OperationType.SET_CLOSURE,
            school=closure.school,
            brand=closure.brand,
            schedule=closure.schedule,
            operation_date=closure.closure_date,
            operated_by=user,
            new_value=closure.get_closure_type_display(),
            reason=closure.reason or '',
            metadata={
                'closure_id': str(closure.id),
                'closure_type': closure.closure_type,
            }
        )

    @classmethod
    def log_staff_absence(cls, tenant_id, school, brand, date, staff_type, user=None, reason=''):
        """スタッフ欠勤をログに記録"""
        op_type = cls.OperationType.NATIVE_ABSENCE if staff_type == 'native' else cls.OperationType.STAFF_ABSENCE
        return cls.objects.create(
            tenant_id=tenant_id,
            operation_type=op_type,
            school=school,
            brand=brand,
            operation_date=date,
            operated_by=user,
            reason=reason,
            metadata={
                'staff_type': staff_type,
            }
        )
