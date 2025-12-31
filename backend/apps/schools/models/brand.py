"""
Brand Models - ブランド関連
BrandCategory, Brand, BrandSchool
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
        from .grade import SchoolYear

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
        'schools.School',
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
