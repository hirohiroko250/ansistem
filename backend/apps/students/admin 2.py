from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from apps.core.csv_utils import CSVImporter
from .models import Student, Guardian, StudentSchool, StudentGuardian


class StudentCSVImporter(CSVImporter):
    """生徒用カスタムCSVインポーター（FK名前解決付き）"""

    def resolve_foreign_keys(self, data: dict) -> dict:
        """名前からForeignKeyを解決"""
        from apps.schools.models import School, Brand, Grade

        # 主所属校舎
        school_name = data.pop('primary_school_name', None)
        if school_name:
            try:
                school = School.objects.filter(school_name=school_name).first()
                if school:
                    data['primary_school'] = school
            except Exception:
                pass

        # 主所属ブランド
        brand_name = data.pop('primary_brand_name', None)
        if brand_name:
            try:
                brand = Brand.objects.filter(brand_name=brand_name).first()
                if brand:
                    data['primary_brand'] = brand
            except Exception:
                pass

        # 学年
        grade_name = data.pop('grade_name', None)
        if grade_name:
            try:
                grade = Grade.objects.filter(grade_name=grade_name).first()
                if grade:
                    data['grade'] = grade
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

                # データ変換
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


@admin.register(Student)
class StudentAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """生徒管理Admin"""

    # カスタムインポーター使用
    csv_importer_class = StudentCSVImporter
    list_display = ['student_no', 'last_name', 'first_name', 'grade', 'primary_school', 'status', 'enrollment_date', 'tenant_ref']
    list_filter = ['tenant_ref', 'status', 'grade', 'primary_school', 'primary_brand']
    search_fields = ['student_no', 'last_name', 'first_name', 'email']
    ordering = ['-created_at']
    raw_id_fields = ['grade', 'primary_school', 'primary_brand', 'user', 'tenant_ref']

    # CSV Import設定
    csv_import_fields = {
        '生徒番号': 'student_no',
        '姓': 'last_name',
        '名': 'first_name',
        '姓（カナ）': 'last_name_kana',
        '名（カナ）': 'first_name_kana',
        '表示名': 'display_name',
        'メールアドレス': 'email',
        '電話番号': 'phone',
        'LINE ID': 'line_id',
        '生年月日': 'birth_date',
        '性別': 'gender',
        '在籍学校名': 'school_name',
        '学校種別': 'school_type',
        '主所属校舎': 'primary_school_name',  # 名前で検索してFKにマッピング
        '主所属ブランド': 'primary_brand_name',  # 名前で検索してFKにマッピング
        '学年': 'grade_name',  # 名前で検索してFKにマッピング
        '入塾日': 'enrollment_date',
        '退塾日': 'withdrawal_date',
        '退塾理由': 'withdrawal_reason',
        'ステータス': 'status',
        '備考': 'notes',
    }
    csv_required_fields = ['生徒番号', '姓', '名']
    csv_unique_fields = ['student_no']
    csv_export_fields = [
        'student_no', 'last_name', 'first_name', 'last_name_kana', 'first_name_kana',
        'display_name', 'email', 'phone', 'line_id', 'birth_date', 'gender',
        'school_name', 'school_type', 'primary_school.school_name', 'primary_brand.brand_name',
        'grade.grade_name', 'enrollment_date', 'withdrawal_date', 'withdrawal_reason',
        'status', 'notes'
    ]
    csv_export_headers = {
        'student_no': '生徒番号',
        'last_name': '姓',
        'first_name': '名',
        'last_name_kana': '姓（カナ）',
        'first_name_kana': '名（カナ）',
        'display_name': '表示名',
        'email': 'メールアドレス',
        'phone': '電話番号',
        'line_id': 'LINE ID',
        'birth_date': '生年月日',
        'gender': '性別',
        'school_name': '在籍学校名',
        'school_type': '学校種別',
        'primary_school.school_name': '主所属校舎',
        'primary_brand.brand_name': '主所属ブランド',
        'grade.grade_name': '学年',
        'enrollment_date': '入塾日',
        'withdrawal_date': '退塾日',
        'withdrawal_reason': '退塾理由',
        'status': 'ステータス',
        'notes': '備考',
    }


@admin.register(Guardian)
class GuardianAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['guardian_no', 'last_name', 'first_name', 'email', 'phone_mobile', 'prefecture', 'city', 'nearest_school', 'tenant_ref']
    list_display_links = ['guardian_no', 'last_name', 'first_name']
    list_filter = ['tenant_ref', 'prefecture', 'nearest_school']
    search_fields = ['guardian_no', 'last_name', 'first_name', 'email', 'phone', 'phone_mobile', 'postal_code', 'city']
    ordering = ['-created_at']
    raw_id_fields = ['tenant_ref', 'user', 'nearest_school']

    fieldsets = (
        ('基本情報', {
            'fields': ('guardian_no', 'user', 'tenant_ref')
        }),
        ('氏名', {
            'fields': (('last_name', 'first_name'), ('last_name_kana', 'first_name_kana'))
        }),
        ('連絡先', {
            'fields': ('email', 'phone', 'phone_mobile', 'line_id')
        }),
        ('住所', {
            'fields': ('postal_code', ('prefecture', 'city'), 'address1', 'address2')
        }),
        ('勤務先', {
            'fields': ('workplace', 'workplace_phone'),
            'classes': ('collapse',)
        }),
        ('登録時情報', {
            'fields': ('nearest_school', 'interested_brands', 'referral_source', 'expectations'),
            'description': '新規登録時に入力された情報'
        }),
        ('備考', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    # CSV Import設定
    csv_import_fields = {
        '保護者番号': 'guardian_no',
        '姓': 'last_name',
        '名': 'first_name',
        '姓（カナ）': 'last_name_kana',
        '名（カナ）': 'first_name_kana',
        'メールアドレス': 'email',
        '電話番号': 'phone',
        '携帯電話': 'phone_mobile',
        '勤務先': 'workplace',
        '勤務先電話番号': 'workplace_phone',
        '郵便番号': 'postal_code',
        '都道府県': 'prefecture',
        '市区町村': 'city',
        '住所1': 'address1',
        '住所2': 'address2',
        '紹介元': 'referral_source',
        '期待・要望': 'expectations',
        '備考': 'notes',
    }
    csv_required_fields = ['姓', '名']
    csv_unique_fields = ['guardian_no']
    csv_export_fields = [
        'guardian_no', 'last_name', 'first_name', 'last_name_kana', 'first_name_kana',
        'email', 'phone', 'phone_mobile', 'workplace', 'workplace_phone',
        'postal_code', 'prefecture', 'city', 'address1', 'address2',
        'nearest_school.school_name', 'referral_source', 'expectations', 'notes'
    ]
    csv_export_headers = {
        'guardian_no': '保護者番号',
        'last_name': '姓',
        'first_name': '名',
        'last_name_kana': '姓（カナ）',
        'first_name_kana': '名（カナ）',
        'email': 'メールアドレス',
        'phone': '電話番号',
        'phone_mobile': '携帯電話',
        'workplace': '勤務先',
        'workplace_phone': '勤務先電話番号',
        'postal_code': '郵便番号',
        'prefecture': '都道府県',
        'city': '市区町村',
        'address1': '住所1',
        'address2': '住所2',
        'nearest_school.school_name': '最寄り校舎',
        'referral_source': '紹介元',
        'expectations': '期待・要望',
        'notes': '備考',
    }


@admin.register(StudentSchool)
class StudentSchoolAdmin(admin.ModelAdmin):
    list_display = ['student', 'school', 'brand', 'enrollment_status', 'start_date', 'is_primary']
    list_filter = ['enrollment_status', 'school', 'brand', 'is_primary']
    raw_id_fields = ['student', 'school', 'brand']


@admin.register(StudentGuardian)
class StudentGuardianAdmin(admin.ModelAdmin):
    list_display = ['student', 'guardian', 'relationship', 'is_primary', 'is_emergency_contact']
    list_filter = ['relationship', 'is_primary', 'is_emergency_contact', 'is_billing_target']
    raw_id_fields = ['student', 'guardian']
