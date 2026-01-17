"""
Grade Admin - 学年・教科管理Admin
SchoolYearAdmin, GradeAdmin, SubjectAdmin
"""
import re
from django.contrib import admin
from django import forms
from apps.core.admin_csv import CSVImportExportMixin
from ..models import SchoolYear, Grade, GradeSchoolYear, Subject


class GradeSchoolYearInline(admin.TabularInline):
    """対象学年定義のインライン編集"""
    model = GradeSchoolYear
    extra = 1
    autocomplete_fields = ['school_year']


class GradeAdminForm(forms.ModelForm):
    """Grade用のAdminフォーム（自動入力機能付き）"""
    auto_populate_school_years = forms.BooleanField(
        label='学年自動入力',
        required=False,
        initial=False,
        help_text='チェックすると、学年名から対象学年を自動入力します（例：小1~ → 小1, 小2, 小3, 小4, 小5, 小6）。既存の単一学年は上書きされます。'
    )

    class Meta:
        model = Grade
        fields = '__all__'


@admin.register(SchoolYear)
class SchoolYearAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """単一学年マスタAdmin（T17a_単一学年）"""
    list_display = ['year_code', 'year_name', 'category', 'sort_order', 'is_active']
    list_filter = ['is_active', 'category']
    search_fields = ['year_code', 'year_name']
    ordering = ['sort_order', 'year_code']

    # CSV Import設定
    csv_import_fields = {
        '学年コード': 'year_code',
        '学年名': 'year_name',
        'カテゴリ': 'category',
        '有効': 'is_active',
        '並び順': 'sort_order',
    }
    csv_required_fields = ['学年コード', '学年名']
    csv_unique_fields = ['year_code']
    csv_export_fields = ['year_code', 'year_name', 'category', 'is_active', 'sort_order']
    csv_export_headers = {
        'year_code': '学年コード',
        'year_name': '学年名',
        'category': 'カテゴリ',
        'is_active': '有効',
        'sort_order': '並び順',
    }


@admin.register(Grade)
class GradeAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """対象学年定義Admin（T17_対象学年定義）"""
    form = GradeAdminForm
    list_display = ['grade_code', 'grade_name', 'get_school_years_display', 'category', 'is_active', 'tenant_ref']
    list_filter = ['tenant_ref', 'is_active', 'category']
    search_fields = ['grade_code', 'grade_name']
    ordering = ['sort_order', 'grade_code']
    inlines = [GradeSchoolYearInline]
    filter_horizontal = ['school_years']
    raw_id_fields = ['tenant_ref']

    @admin.display(description='対象学年')
    def get_school_years_display(self, obj):
        years = obj.school_years.all().order_by('sort_order')[:5]
        names = [y.year_name for y in years]
        total = obj.school_years.count()
        if total > 5:
            return f"{', '.join(names)}... (+{total - 5})"
        return ', '.join(names) if names else '-'

    def save_model(self, request, obj, form, change):
        """保存時に学年名から対象学年を自動入力"""
        super().save_model(request, obj, form, change)

        # 自動入力が有効な場合のみ処理
        if form.cleaned_data.get('auto_populate_school_years', False):
            self._auto_populate_school_years(obj)

    def _auto_populate_school_years(self, grade):
        """学年名のパターンから対象学年を自動入力する"""
        grade_name = grade.grade_name
        tenant_id = grade.tenant_id

        # 未就学児の学年コードマッピング（年少=1, 年中=2, 年長=3）
        preschool_codes = {'NS': 1, 'NC': 2, 'NL': 3}  # 年少、年中、年長
        preschool_names = {'年少': 'NS', '年中': 'NC', '年長': 'NL'}

        # 数字形式のパターン
        # 学年名 → (カテゴリ, 開始学年番号, 終了学年番号)
        number_patterns = [
            # 「小1~」形式 - 小学1年生以上
            (r'^小([1-6])[\~〜]$', 'elementary', lambda m: (int(m.group(1)), 6)),
            # 「小1-小3」形式 - 範囲指定
            (r'^小([1-6])[\-ー]小([1-6])$', 'elementary', lambda m: (int(m.group(1)), int(m.group(2)))),
            # 「中1~」形式 - 中学1年生以上
            (r'^中([1-3])[\~〜]$', 'junior_high', lambda m: (int(m.group(1)), 3)),
            # 「中1-中3」形式 - 範囲指定
            (r'^中([1-3])[\-ー]中([1-3])$', 'junior_high', lambda m: (int(m.group(1)), int(m.group(2)))),
            # 「高1~」形式 - 高校1年生以上
            (r'^高([1-3])[\~〜]$', 'high_school', lambda m: (int(m.group(1)), 3)),
            # 「高1-高3」形式 - 範囲指定
            (r'^高([1-3])[\-ー]高([1-3])$', 'high_school', lambda m: (int(m.group(1)), int(m.group(2)))),
            # 「小学生」形式 - 全小学生
            (r'^小学生(全体)?$', 'elementary', lambda m: (1, 6)),
            # 「中学生」形式 - 全中学生
            (r'^中学生(全体)?$', 'junior_high', lambda m: (1, 3)),
            # 「高校生」形式 - 全高校生
            (r'^高校生(全体)?$', 'high_school', lambda m: (1, 3)),
        ]

        # カテゴリ → year_codeプレフィックスマッピング
        category_prefix = {
            'elementary': 'E',  # E1-E6
            'junior_high': 'J',  # J1-J3
            'high_school': 'H',  # H1-H3
        }

        year_codes = []

        # 数字形式のパターンをチェック
        for pattern, category, range_func in number_patterns:
            match = re.match(pattern, grade_name)
            if match:
                start_num, end_num = range_func(match)
                prefix = category_prefix[category]
                year_codes = [f'{prefix}{i}' for i in range(start_num, end_num + 1)]
                break

        # 未就学児パターンをチェック
        if not year_codes:
            # 「年少~」形式 - 年少以上
            preschool_match = re.match(r'^(年少|年中|年長)[\~〜]$', grade_name)
            if preschool_match:
                start_name = preschool_match.group(1)
                start_code = preschool_names[start_name]
                start_order = preschool_codes[start_code]
                year_codes = [code for code, order in preschool_codes.items() if order >= start_order]

            # 「年少-年長」形式 - 範囲指定
            preschool_range_match = re.match(r'^(年少|年中|年長)[\-ー](年少|年中|年長)$', grade_name)
            if preschool_range_match:
                start_name = preschool_range_match.group(1)
                end_name = preschool_range_match.group(2)
                start_order = preschool_codes[preschool_names[start_name]]
                end_order = preschool_codes[preschool_names[end_name]]
                year_codes = [code for code, order in preschool_codes.items()
                              if start_order <= order <= end_order]

            # 「未就学児」「幼児」形式 - 全未就学児
            if re.match(r'^(未就学児|幼児)(全体)?$', grade_name):
                year_codes = list(preschool_codes.keys())

        if year_codes:
            school_years = SchoolYear.objects.filter(
                tenant_id=tenant_id,
                year_code__in=year_codes,
                is_active=True
            )

            # 既存のGradeSchoolYearを削除して再作成
            GradeSchoolYear.objects.filter(
                grade=grade,
                tenant_id=tenant_id
            ).delete()

            # 新しいGradeSchoolYearを作成
            for school_year in school_years:
                GradeSchoolYear.objects.create(
                    grade=grade,
                    school_year=school_year,
                    tenant_id=tenant_id
                )

    # CSV Import設定
    csv_import_fields = {
        '学年コード': 'grade_code',
        '学年名': 'grade_name',
        '学年略称': 'grade_name_short',
        'カテゴリ': 'category',
        '説明': 'description',
        '有効': 'is_active',
        '並び順': 'sort_order',
    }
    csv_required_fields = ['学年コード', '学年名']
    csv_unique_fields = ['grade_code']
    csv_export_fields = [
        'grade_code', 'grade_name', 'grade_name_short', 'category',
        'description', 'is_active', 'sort_order'
    ]
    csv_export_headers = {
        'grade_code': '学年コード',
        'grade_name': '学年名',
        'grade_name_short': '学年略称',
        'category': 'カテゴリ',
        'description': '説明',
        'is_active': '有効',
        'sort_order': '並び順',
    }


@admin.register(Subject)
class SubjectAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """教科マスタAdmin"""
    list_display = ['subject_code', 'subject_name', 'brand', 'category', 'is_active', 'tenant_ref']
    list_filter = ['tenant_ref', 'is_active', 'category', 'brand']
    search_fields = ['subject_code', 'subject_name']
    ordering = ['sort_order', 'subject_code']
    raw_id_fields = ['tenant_ref', 'brand']
    autocomplete_fields = ['brand']

    # CSV Import設定
    csv_import_fields = {
        '教科コード': 'subject_code',
        '教科名': 'subject_name',
        '教科略称': 'subject_short_name',
        'カテゴリ': 'category',
        '説明': 'description',
        'アイコン': 'icon',
        'カラー': 'color',
        '有効': 'is_active',
        '並び順': 'sort_order',
    }
    csv_required_fields = ['教科コード', '教科名']
    csv_unique_fields = ['subject_code']
    csv_export_fields = [
        'subject_code', 'subject_name', 'subject_short_name', 'category',
        'description', 'icon', 'color', 'is_active', 'sort_order'
    ]
    csv_export_headers = {
        'subject_code': '教科コード',
        'subject_name': '教科名',
        'subject_short_name': '教科略称',
        'category': 'カテゴリ',
        'description': '説明',
        'icon': 'アイコン',
        'color': 'カラー',
        'is_active': '有効',
        'sort_order': '並び順',
    }
