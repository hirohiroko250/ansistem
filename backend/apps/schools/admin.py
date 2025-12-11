from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from apps.core.csv_utils import CSVImporter
from apps.tenants.models import Tenant
from .models import (
    Brand, BrandCategory, School, Grade, Subject, Classroom, SchoolYear, GradeSchoolYear, BrandSchool,
    TimeSlot, LessonCalendar, ClassSchedule
)


class SchoolCSVImporter(CSVImporter):
    """校舎用カスタムCSVインポーター（FK名前解決付き）"""

    def resolve_foreign_keys(self, data: dict) -> dict:
        """名前からForeignKeyを解決"""
        # ブランド（ブランド名で検索）
        brand_name = data.pop('brand_name', None)
        if brand_name:
            try:
                brand = Brand.objects.filter(brand_name=brand_name).first()
                if brand:
                    data['brand'] = brand
            except Exception:
                pass
        return data

    def import_csv(self, csv_file, update_existing: bool = True):
        """CSVインポート（FK解決付き）"""
        from django.db import transaction

        self.errors = []
        self.created_count = 0
        self.updated_count = 0
        self.skipped_count = 0

        rows = self.parse_csv(csv_file)

        with transaction.atomic():
            for row_num, row in enumerate(rows, start=2):
                if not self.validate_row(row, row_num):
                    self.skipped_count += 1
                    continue

                data = {}
                for csv_field, model_field in self.field_mapping.items():
                    if csv_field in row:
                        value = row[csv_field]
                        try:
                            field = self.model._meta.get_field(model_field)
                            field_type = type(field)
                        except Exception:
                            field_type = str
                        data[model_field] = self.convert_value(model_field, value, field_type)

                # FK解決
                data = self.resolve_foreign_keys(data)

                # テナントID設定
                if self.tenant_id and hasattr(self.model, 'tenant_id'):
                    data['tenant_id'] = self.tenant_id

                try:
                    instance, is_new = self.get_or_create_instance(data)

                    if not is_new and not update_existing:
                        self.skipped_count += 1
                        continue

                    for field_name, value in data.items():
                        if value is not None:
                            setattr(instance, field_name, value)

                    instance.save()

                    if is_new:
                        self.created_count += 1
                    else:
                        self.updated_count += 1

                except Exception as e:
                    self.errors.append({
                        'row': row_num,
                        'field': None,
                        'message': str(e)
                    })
                    self.skipped_count += 1

        return {
            'success': len(self.errors) == 0,
            'created': self.created_count,
            'updated': self.updated_count,
            'skipped': self.skipped_count,
            'errors': self.errors
        }


class ClassroomCSVImporter(CSVImporter):
    """教室用カスタムCSVインポーター（FK名前解決付き）"""

    def resolve_foreign_keys(self, data: dict) -> dict:
        """名前からForeignKeyを解決"""
        # 校舎（校舎名で検索）
        school_name = data.pop('school_name', None)
        if school_name:
            try:
                school = School.objects.filter(school_name=school_name).first()
                if school:
                    data['school'] = school
            except Exception:
                pass
        return data

    def import_csv(self, csv_file, update_existing: bool = True):
        """CSVインポート（FK解決付き）"""
        from django.db import transaction

        self.errors = []
        self.created_count = 0
        self.updated_count = 0
        self.skipped_count = 0

        rows = self.parse_csv(csv_file)

        with transaction.atomic():
            for row_num, row in enumerate(rows, start=2):
                if not self.validate_row(row, row_num):
                    self.skipped_count += 1
                    continue

                data = {}
                for csv_field, model_field in self.field_mapping.items():
                    if csv_field in row:
                        value = row[csv_field]
                        try:
                            field = self.model._meta.get_field(model_field)
                            field_type = type(field)
                        except Exception:
                            field_type = str
                        data[model_field] = self.convert_value(model_field, value, field_type)

                # FK解決
                data = self.resolve_foreign_keys(data)

                # テナントID設定
                if self.tenant_id and hasattr(self.model, 'tenant_id'):
                    data['tenant_id'] = self.tenant_id

                try:
                    instance, is_new = self.get_or_create_instance(data)

                    if not is_new and not update_existing:
                        self.skipped_count += 1
                        continue

                    for field_name, value in data.items():
                        if value is not None:
                            setattr(instance, field_name, value)

                    instance.save()

                    if is_new:
                        self.created_count += 1
                    else:
                        self.updated_count += 1

                except Exception as e:
                    self.errors.append({
                        'row': row_num,
                        'field': None,
                        'message': str(e)
                    })
                    self.skipped_count += 1

        return {
            'success': len(self.errors) == 0,
            'created': self.created_count,
            'updated': self.updated_count,
            'skipped': self.skipped_count,
            'errors': self.errors
        }


class BrandSchoolInline(admin.TabularInline):
    """ブランド開講校舎のインライン編集"""
    model = BrandSchool
    extra = 1
    autocomplete_fields = ['school']
    fields = ['school', 'is_main', 'sort_order', 'is_active']

    def save_new_objects(self, commit=True):
        """新規オブジェクト保存時にtenant_idを親から継承"""
        saved_instances = super().save_new_objects(commit=False)
        for instance in saved_instances:
            if hasattr(self, 'parent_instance') and self.parent_instance:
                instance.tenant_id = self.parent_instance.tenant_id
                instance.tenant_ref_id = self.parent_instance.tenant_ref_id
            if commit:
                instance.save()
        return saved_instances


class BrandInline(admin.TabularInline):
    """ブランドカテゴリに属するブランドのインライン編集"""
    model = Brand
    extra = 0
    fields = ['brand_code', 'brand_name', 'brand_type', 'is_active']
    show_change_link = True


@admin.register(BrandCategory)
class BrandCategoryAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """ブランドカテゴリマスタAdmin（T12c_ブランドカテゴリ）"""
    list_display = ['category_code', 'category_name', 'get_brand_count', 'sort_order', 'is_active', 'tenant_ref']
    list_filter = ['tenant_ref', 'is_active']
    search_fields = ['category_code', 'category_name']
    ordering = ['sort_order', 'category_code']
    raw_id_fields = ['tenant_ref']
    inlines = [BrandInline]

    fieldsets = (
        ('基本情報', {
            'fields': ('category_code', 'category_name', 'category_name_short', 'description')
        }),
        ('表示設定', {
            'fields': ('logo_url', 'color_primary', 'color_secondary', 'sort_order')
        }),
        ('ステータス', {
            'fields': ('is_active', 'tenant_ref')
        }),
    )

    # CSV Import設定
    csv_import_fields = {
        'カテゴリコード': 'category_code',
        'カテゴリ名': 'category_name',
        'カテゴリ略称': 'category_name_short',
        '説明': 'description',
        'ロゴURL': 'logo_url',
        'メインカラー': 'color_primary',
        'サブカラー': 'color_secondary',
        '並び順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['カテゴリコード', 'カテゴリ名']
    csv_unique_fields = ['category_code']
    csv_export_fields = [
        'category_code', 'category_name', 'category_name_short', 'description',
        'logo_url', 'color_primary', 'color_secondary', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'category_code': 'カテゴリコード',
        'category_name': 'カテゴリ名',
        'category_name_short': 'カテゴリ略称',
        'description': '説明',
        'logo_url': 'ロゴURL',
        'color_primary': 'メインカラー',
        'color_secondary': 'サブカラー',
        'sort_order': '並び順',
        'is_active': '有効',
    }

    @admin.display(description='ブランド数')
    def get_brand_count(self, obj):
        return obj.brands.filter(is_active=True).count()


@admin.register(Brand)
class BrandAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """ブランドマスタAdmin（T12_ブランド情報対応）"""
    list_display = ['brand_code', 'brand_name', 'category', 'brand_type', 'get_school_count', 'is_active', 'sort_order', 'tenant_ref']
    list_filter = ['tenant_ref', 'is_active', 'category', 'brand_type']
    search_fields = ['brand_code', 'brand_name']
    ordering = ['sort_order', 'brand_code']
    raw_id_fields = ['tenant_ref']
    autocomplete_fields = ['category']
    inlines = [BrandSchoolInline]

    @admin.display(description='開講校舎数')
    def get_school_count(self, obj):
        return obj.brand_schools.filter(is_active=True).count()

    def save_formset(self, request, form, formset, change):
        """インラインフォームセット保存時にtenant_idを親から継承"""
        instances = formset.save(commit=False)
        for instance in instances:
            # 親オブジェクト（Brand）からtenant_idを継承
            if hasattr(instance, 'tenant_id') and form.instance.tenant_id:
                instance.tenant_id = form.instance.tenant_id
            if hasattr(instance, 'tenant_ref_id') and form.instance.tenant_ref_id:
                instance.tenant_ref_id = form.instance.tenant_ref_id
            instance.save()
        formset.save_m2m()

    # CSV Import設定
    csv_import_fields = {
        'ブランドコード': 'brand_code',
        'ブランド名': 'brand_name',
        'ブランド略称': 'brand_short_name',
        'ブランドタイプ': 'brand_type',
        '説明': 'description',
        'ロゴURL': 'logo_url',
        'テーマカラー': 'theme_color',
        '有効': 'is_active',
        '並び順': 'sort_order',
    }
    csv_required_fields = ['ブランドコード', 'ブランド名']
    csv_unique_fields = ['brand_code']
    csv_export_fields = [
        'brand_code', 'brand_name', 'brand_short_name', 'brand_type',
        'description', 'logo_url', 'theme_color', 'is_active', 'sort_order'
    ]
    csv_export_headers = {
        'brand_code': 'ブランドコード',
        'brand_name': 'ブランド名',
        'brand_short_name': 'ブランド略称',
        'brand_type': 'ブランドタイプ',
        'description': '説明',
        'logo_url': 'ロゴURL',
        'theme_color': 'テーマカラー',
        'is_active': '有効',
        'sort_order': '並び順',
    }


@admin.register(School)
class SchoolAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """校舎マスタAdmin（T10_校舎情報対応）"""
    list_display = ['tenant_ref', 'school_code', 'school_name', 'prefecture', 'city', 'is_active']
    list_filter = ['tenant_ref', 'is_active', 'prefecture']
    search_fields = ['school_code', 'school_name', 'city']
    ordering = ['sort_order', 'school_code']
    raw_id_fields = ['tenant_ref']

    # カスタムインポーター使用
    csv_importer_class = SchoolCSVImporter

    # CSV Import設定
    csv_import_fields = {
        '校舎コード': 'school_code',
        '校舎名': 'school_name',
        '校舎略称': 'school_short_name',
        '郵便番号': 'postal_code',
        '都道府県': 'prefecture',
        '市区町村': 'city',
        '住所1': 'address_line1',
        '住所2': 'address_line2',
        '電話番号': 'phone',
        'FAX番号': 'fax',
        'メールアドレス': 'email',
        '営業開始時間': 'opening_time',
        '営業終了時間': 'closing_time',
        '最寄り駅': 'nearest_station',
        '駐車場': 'has_parking',
        '有効': 'is_active',
        '並び順': 'sort_order',
    }
    csv_required_fields = ['校舎コード', '校舎名']
    csv_unique_fields = ['school_code']
    csv_export_fields = [
        'school_code', 'school_name', 'school_name_short',
        'postal_code', 'prefecture', 'city', 'address1', 'address2',
        'phone', 'fax', 'email',
        'is_active', 'sort_order'
    ]
    csv_export_headers = {
        'school_code': '校舎コード',
        'school_name': '校舎名',
        'school_name_short': '校舎略称',
        'postal_code': '郵便番号',
        'prefecture': '都道府県',
        'city': '市区町村',
        'address1': '住所1',
        'address2': '住所2',
        'phone': '電話番号',
        'fax': 'FAX番号',
        'email': 'メールアドレス',
        'is_active': '有効',
        'sort_order': '並び順',
    }


class GradeSchoolYearInline(admin.TabularInline):
    """対象学年定義のインライン編集"""
    model = GradeSchoolYear
    extra = 1
    autocomplete_fields = ['school_year']


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


@admin.register(Classroom)
class ClassroomAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """教室マスタAdmin（T11_ルーム情報対応）"""
    list_display = ['classroom_code', 'classroom_name', 'school', 'capacity', 'is_active', 'tenant_ref']
    list_filter = ['tenant_ref', 'is_active', 'school']
    search_fields = ['classroom_code', 'classroom_name']
    ordering = ['school', 'sort_order', 'classroom_code']
    raw_id_fields = ['tenant_ref']

    # カスタムインポーター使用
    csv_importer_class = ClassroomCSVImporter

    # CSV Import設定
    csv_import_fields = {
        '教室コード': 'classroom_code',
        '教室名': 'classroom_name',
        '校舎': 'school_name',  # 名前で検索してFKにマッピング
        '定員': 'capacity',
        'フロア': 'floor',
        '設備': 'equipment',
        '説明': 'description',
        '有効': 'is_active',
        '並び順': 'sort_order',
    }
    csv_required_fields = ['教室コード', '教室名']
    csv_unique_fields = ['classroom_code']
    csv_export_fields = [
        'classroom_code', 'classroom_name', 'school.school_name',
        'capacity', 'floor', 'equipment', 'description', 'is_active', 'sort_order'
    ]
    csv_export_headers = {
        'classroom_code': '教室コード',
        'classroom_name': '教室名',
        'school.school_name': '校舎',
        'capacity': '定員',
        'floor': 'フロア',
        'equipment': '設備',
        'description': '説明',
        'is_active': '有効',
        'sort_order': '並び順',
    }


@admin.register(BrandSchool)
class BrandSchoolAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """ブランド開講校舎Admin（T12a_ブランド開講校舎）"""
    list_display = ['brand', 'school', 'get_school_location', 'is_main', 'sort_order', 'is_active', 'tenant_ref']
    list_filter = ['tenant_ref', 'is_active', 'brand', 'is_main']
    search_fields = ['brand__brand_name', 'school__school_name']
    ordering = ['brand', 'sort_order']
    autocomplete_fields = ['brand', 'school']
    raw_id_fields = ['tenant_ref']

    # CSV Import設定
    csv_import_fields = {
        'ブランドコード': 'brand__brand_code',
        '校舎コード': 'school__school_code',
        'メイン校舎': 'is_main',
        '並び順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['ブランドコード', '校舎コード']
    csv_unique_fields = []
    csv_export_fields = [
        'brand.brand_code', 'brand.brand_name', 'school.school_code', 'school.school_name',
        'is_main', 'sort_order', 'is_active'
    ]
    csv_export_headers = {
        'brand.brand_code': 'ブランドコード',
        'brand.brand_name': 'ブランド名',
        'school.school_code': '校舎コード',
        'school.school_name': '校舎名',
        'is_main': 'メイン校舎',
        'sort_order': '並び順',
        'is_active': '有効',
    }

    @admin.display(description='位置情報')
    def get_school_location(self, obj):
        if obj.school.latitude and obj.school.longitude:
            return f"({obj.school.latitude}, {obj.school.longitude})"
        return "未設定"


@admin.register(TimeSlot)
class TimeSlotAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """時間枠マスタAdmin"""
    list_display = ['slot_code', 'slot_name', 'start_time', 'end_time']
    ordering = ['sort_order', 'start_time']

    # CSV Import設定
    csv_import_fields = {
        '時間枠コード': 'slot_code',
        '時間枠名': 'slot_name',
        '開始時間': 'start_time',
        '終了時間': 'end_time',
        '時間（分）': 'duration_minutes',
        '並び順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['時間枠コード', '時間枠名', '開始時間', '終了時間']
    csv_unique_fields = ['slot_code']
    csv_export_fields = ['slot_code', 'slot_name', 'start_time', 'end_time', 'duration_minutes', 'sort_order', 'is_active']
    csv_export_headers = {
        'slot_code': '時間枠コード',
        'slot_name': '時間枠名',
        'start_time': '開始時間',
        'end_time': '終了時間',
        'duration_minutes': '時間（分）',
        'sort_order': '並び順',
        'is_active': '有効',
    }


# =============================================================================
# T13a/b: 開講カレンダー
# =============================================================================
class LessonCalendarCSVImporter(CSVImporter):
    """開講カレンダー用カスタムCSVインポーター（カレンダーIDからブランド・校舎自動解析）"""

    def resolve_foreign_keys(self, data: dict) -> dict:
        """カレンダーIDからブランド・校舎を自動解析してForeignKeyを解決

        カレンダーID形式: 1001_SKAEC_A = 校舎コード_ブランドコード_タイプ
        例: 1001_SKAEC_A → 校舎コード=1001, ブランドコード=SKAEC
        """
        calendar_code = data.get('calendar_code', '')

        if calendar_code and '_' in calendar_code:
            parts = calendar_code.split('_')
            if len(parts) >= 2:
                school_code = parts[0]  # 1001
                brand_code = parts[1]   # SKAEC

                # ブランド検索
                try:
                    brand = Brand.objects.filter(brand_code=brand_code).first()
                    if brand:
                        data['brand'] = brand
                except Exception:
                    pass

                # 校舎検索
                try:
                    school = School.objects.filter(school_code=school_code).first()
                    if school:
                        data['school'] = school
                except Exception:
                    pass

        return data

    def import_csv(self, csv_file, update_existing: bool = True):
        """CSVインポート（FK解決付き）"""
        from django.db import transaction

        self.errors = []
        self.created_count = 0
        self.updated_count = 0
        self.skipped_count = 0

        rows = self.parse_csv(csv_file)

        with transaction.atomic():
            for row_num, row in enumerate(rows, start=2):
                if not self.validate_row(row, row_num):
                    self.skipped_count += 1
                    continue

                data = {}
                for csv_field, model_field in self.field_mapping.items():
                    if csv_field in row:
                        value = row[csv_field]
                        try:
                            field = self.model._meta.get_field(model_field)
                            field_type = type(field)
                        except Exception:
                            field_type = str
                        data[model_field] = self.convert_value(model_field, value, field_type)

                # FK解決
                data = self.resolve_foreign_keys(data)

                # テナントID設定
                if self.tenant_id and hasattr(self.model, 'tenant_id'):
                    data['tenant_id'] = self.tenant_id

                try:
                    instance, is_new = self.get_or_create_instance(data)

                    if not is_new and not update_existing:
                        self.skipped_count += 1
                        continue

                    for field_name, value in data.items():
                        if value is not None:
                            setattr(instance, field_name, value)

                    instance.save()

                    if is_new:
                        self.created_count += 1
                    else:
                        self.updated_count += 1

                except Exception as e:
                    self.errors.append({
                        'row': row_num,
                        'field': None,
                        'message': str(e)
                    })
                    self.skipped_count += 1

        return {
            'success': len(self.errors) == 0,
            'created': self.created_count,
            'updated': self.updated_count,
            'skipped': self.skipped_count,
            'errors': self.errors
        }


@admin.register(LessonCalendar)
class LessonCalendarAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """開講カレンダーAdmin"""
    list_display = ['calendar_code', 'brand', 'school', 'lesson_date', 'day_of_week', 'is_open', 'display_label', 'ticket_type', 'tenant_ref']
    list_filter = ['tenant_ref', 'is_open', 'lesson_type', 'brand', 'school', 'is_makeup_allowed']
    search_fields = ['calendar_code', 'display_label', 'notice_message', 'holiday_name']
    raw_id_fields = ['brand', 'school', 'tenant_ref']
    date_hierarchy = 'lesson_date'
    ordering = ['lesson_date']

    # カスタムインポーター使用
    csv_importer_class = LessonCalendarCSVImporter

    # CSV Import設定（Excel T13_開講カレンダー準拠）
    # カレンダーIDから自動でブランド・校舎を解析
    # 形式: 1001_SKAEC_A = 校舎コード_ブランドコード_タイプ
    csv_import_fields = {
        'カレンダーID': 'calendar_code',
        '日付': 'lesson_date',
        '曜日': 'day_of_week',
        '保護者カレンダー表示': 'display_label',
        '開講日': 'is_open',
        '振替拒否': 'is_makeup_allowed',
        '消化・発行チケット券種': 'ticket_type',
        '権利発券数': 'ticket_issue_count',
        'チケット券種No': 'ticket_sequence',
        '有効期限': 'valid_days',
        'お知らせ': 'notice_message',
        '自動お知らせ送信': 'auto_send_notice',
        '拒否理由': 'rejection_reason',
        '祝日名': 'holiday_name',
    }
    csv_required_fields = ['カレンダーID', '日付']
    csv_unique_fields = ['calendar_code', 'lesson_date']
    csv_export_fields = [
        'calendar_code', 'brand.brand_code', 'school.school_code',
        'lesson_date', 'day_of_week', 'display_label', 'is_open',
        'is_makeup_allowed', 'ticket_type', 'ticket_issue_count', 'ticket_sequence',
        'valid_days', 'notice_message', 'auto_send_notice', 'rejection_reason', 'holiday_name'
    ]
    csv_export_headers = {
        'calendar_code': 'カレンダーID',
        'brand.brand_code': 'ブランドコード',
        'school.school_code': '校舎コード',
        'lesson_date': '日付',
        'day_of_week': '曜日',
        'display_label': '保護者カレンダー表示',
        'is_open': '開講日',
        'is_makeup_allowed': '振替拒否',
        'ticket_type': '消化・発行チケット券種',
        'ticket_issue_count': '権利発券数',
        'ticket_sequence': 'チケット券種No',
        'valid_days': '有効期限',
        'notice_message': 'お知らせ',
        'auto_send_notice': '自動お知らせ送信',
        'rejection_reason': '拒否理由',
        'holiday_name': '祝日名',
    }


# =============================================================================
# T14c: 開講時間割
# =============================================================================
@admin.register(ClassSchedule)
class ClassScheduleAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """開講時間割Admin（T14c_開講時間割）

    クラス登録・振替のベースとなるマスタ
    """
    list_display = [
        'schedule_code', 'school', 'brand_category', 'brand',
        'get_day_of_week_display', 'period', 'start_time', 'class_name',
        'capacity', 'reserved_seats', 'is_active'
    ]
    list_filter = [
        'is_active', 'brand_category', 'brand', 'school',
        'day_of_week', 'approval_type'
    ]
    search_fields = [
        'schedule_code', 'class_name', 'class_type',
        'ticket_name', 'transfer_group', 'calendar_pattern'
    ]
    ordering = ['school', 'brand_category', 'brand', 'day_of_week', 'period']
    autocomplete_fields = ['brand', 'brand_category', 'school', 'room']
    date_hierarchy = 'class_start_date'

    fieldsets = (
        ('基本情報', {
            'fields': (
                'schedule_code',
                ('school', 'room', 'room_name'),
                ('brand_category', 'brand'),
            )
        }),
        ('曜日・時間', {
            'fields': (
                ('day_of_week', 'period'),
                ('start_time', 'end_time', 'duration_minutes'),
                'break_time',
            )
        }),
        ('クラス情報', {
            'fields': (
                'class_name', 'class_type',
                'display_course_name', 'display_pair_name',
                'display_description',
            )
        }),
        ('チケット・振替', {
            'fields': (
                ('ticket_name', 'ticket_id'),
                ('transfer_group', 'schedule_group'),
                'calendar_pattern',
            )
        }),
        ('定員・承認', {
            'fields': (
                ('capacity', 'trial_capacity', 'reserved_seats'),
                ('pause_seat_fee', 'approval_type'),
            )
        }),
        ('期間', {
            'fields': (
                'display_start_date',
                ('class_start_date', 'class_end_date'),
            )
        }),
        ('ステータス', {
            'fields': ('is_active', 'tenant_id')
        }),
    )

    @admin.display(description='曜日')
    def get_day_of_week_display(self, obj):
        return obj.get_day_of_week_display()

    # CSV Import設定（Excel T14_開講時間割準拠）
    csv_import_fields = {
        '時間割コード': 'schedule_code',
        '校舎名': 'school__school_name',
        'ブランド名': 'brand__brand_name',
        '曜日': 'day_of_week',
        '時限': 'period',
        '開始時間': 'start_time',
        '授業時間': 'duration_minutes',
        '終了時間': 'end_time',
        'クラス名': 'class_name',
        'クラス種名': 'class_type',
        '保護者用コース名': 'display_course_name',
        '保護者用ペア名': 'display_pair_name',
        '保護者用説明': 'display_description',
        'チケット名': 'ticket_name',
        'チケットID': 'ticket_id',
        '振替グループ': 'transfer_group',
        '時間割グループ': 'schedule_group',
        '定員': 'capacity',
        '体験人数': 'trial_capacity',
        '休会時座席料金': 'pause_seat_fee',
        'カレンダーパターン': 'calendar_pattern',
        '承認種別': 'approval_type',
        '教室名': 'room_name',
        '保護者表示開始日': 'display_start_date',
        'クラス開始日': 'class_start_date',
        'クラス終了日': 'class_end_date',
        '有効': 'is_active',
    }
    csv_required_fields = ['時間割コード', 'クラス名']
    csv_unique_fields = ['schedule_code']
    csv_export_fields = [
        'schedule_code', 'school.school_name', 'brand.brand_name',
        'day_of_week', 'period', 'start_time', 'duration_minutes', 'end_time',
        'class_name', 'class_type', 'display_course_name', 'display_pair_name',
        'ticket_name', 'ticket_id', 'transfer_group', 'schedule_group',
        'capacity', 'trial_capacity', 'pause_seat_fee', 'calendar_pattern',
        'approval_type', 'room_name', 'display_start_date', 'class_start_date',
        'class_end_date', 'is_active'
    ]
    csv_export_headers = {
        'schedule_code': '時間割コード',
        'school.school_name': '校舎名',
        'brand.brand_name': 'ブランド名',
        'day_of_week': '曜日',
        'period': '時限',
        'start_time': '開始時間',
        'duration_minutes': '授業時間',
        'end_time': '終了時間',
        'class_name': 'クラス名',
        'class_type': 'クラス種名',
        'display_course_name': '保護者用コース名',
        'display_pair_name': '保護者用ペア名',
        'ticket_name': 'チケット名',
        'ticket_id': 'チケットID',
        'transfer_group': '振替グループ',
        'schedule_group': '時間割グループ',
        'capacity': '定員',
        'trial_capacity': '体験人数',
        'pause_seat_fee': '休会時座席料金',
        'calendar_pattern': 'カレンダーパターン',
        'approval_type': '承認種別',
        'room_name': '教室名',
        'display_start_date': '保護者表示開始日',
        'class_start_date': 'クラス開始日',
        'class_end_date': 'クラス終了日',
        'is_active': '有効',
    }
