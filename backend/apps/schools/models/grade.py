"""
Grade Models - 学年・教科関連
SchoolYear, Grade, GradeSchoolYear, Subject
"""
import uuid
from django.db import models
from apps.core.models import TenantModel

from .brand import Brand


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
