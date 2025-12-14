from django.contrib import admin
from django.db.models import Case, When
from django.utils.html import format_html
from apps.core.admin_csv import CSVImportExportMixin
from apps.core.csv_utils import CSVImporter
from .models import Student, Guardian, StudentSchool, StudentGuardian, AbsenceTicket, StudentEnrollment, SuspensionRequest, WithdrawalRequest, BankAccount, BankAccountChangeRequest, FriendshipRegistration, FSDiscount
from apps.lessons.models import Attendance


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
    csv_required_fields = ['姓', '名']  # 生徒番号は自動発番されるため必須ではない
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
        ('銀行口座情報', {
            'fields': (
                ('bank_name', 'bank_code'),
                ('branch_name', 'branch_code'),
                'account_type',
                'account_number',
                ('account_holder', 'account_holder_kana'),
            ),
            'description': '口座振替に使用する銀行口座情報'
        }),
        ('引き落とし設定', {
            'fields': ('withdrawal_day', 'payment_registered', 'payment_registered_at'),
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
class StudentSchoolAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['student', 'school', 'brand', 'get_day_of_week_display', 'start_time', 'enrollment_status', 'start_date', 'is_primary']
    list_filter = ['enrollment_status', 'school', 'brand', 'is_primary', 'day_of_week']
    raw_id_fields = ['student', 'school', 'brand', 'class_schedule']
    search_fields = ['student__student_no', 'student__last_name', 'student__first_name', 'school__school_name', 'brand__brand_name']
    ordering = ['student__student_no', 'brand', 'day_of_week', 'start_time']

    fieldsets = (
        ('基本情報', {
            'fields': ('student', 'school', 'brand', 'enrollment_status', 'is_primary')
        }),
        ('スケジュール', {
            'fields': ('class_schedule', 'day_of_week', 'start_time', 'end_time')
        }),
        ('期間', {
            'fields': ('start_date', 'end_date')
        }),
        ('その他', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='曜日')
    def get_day_of_week_display(self, obj):
        days = {1: '月', 2: '火', 3: '水', 4: '木', 5: '金', 6: '土', 7: '日'}
        return days.get(obj.day_of_week, '-')

    # CSV Import設定
    csv_import_fields = {
        '生徒番号': 'student__student_no',
        '校舎コード': 'school__school_code',
        'ブランドコード': 'brand__brand_code',
        '入塾ステータス': 'enrollment_status',
        '入塾日': 'start_date',
        '退塾日': 'end_date',
        '主所属': 'is_primary',
        '曜日': 'day_of_week',
        '開始時間': 'start_time',
        '終了時間': 'end_time',
    }
    csv_required_fields = ['生徒番号', '校舎コード']
    csv_unique_fields = []
    csv_export_fields = [
        'student.student_no', 'student.last_name', 'student.first_name',
        'school.school_code', 'school.school_name',
        'brand.brand_code', 'brand.brand_name',
        'enrollment_status', 'start_date', 'end_date', 'is_primary',
        'day_of_week', 'start_time', 'end_time'
    ]
    csv_export_headers = {
        'student.student_no': '生徒番号',
        'student.last_name': '生徒姓',
        'student.first_name': '生徒名',
        'school.school_code': '校舎コード',
        'school.school_name': '校舎名',
        'brand.brand_code': 'ブランドコード',
        'brand.brand_name': 'ブランド名',
        'enrollment_status': '入塾ステータス',
        'start_date': '入塾日',
        'end_date': '退塾日',
        'is_primary': '主所属',
        'day_of_week': '曜日',
        'start_time': '開始時間',
        'end_time': '終了時間',
    }


@admin.register(StudentGuardian)
class StudentGuardianAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['student', 'guardian', 'relationship', 'is_primary', 'is_emergency_contact']
    list_filter = ['relationship', 'is_primary', 'is_emergency_contact', 'is_billing_target']
    raw_id_fields = ['student', 'guardian']

    # CSV Import設定
    csv_import_fields = {
        '生徒番号': 'student__student_no',
        '保護者番号': 'guardian__guardian_no',
        '続柄': 'relationship',
        '主保護者': 'is_primary',
        '緊急連絡先': 'is_emergency_contact',
        '請求対象': 'is_billing_target',
    }
    csv_required_fields = ['生徒番号', '保護者番号']
    csv_unique_fields = []
    csv_export_fields = [
        'student.student_no', 'student.last_name', 'student.first_name',
        'guardian.guardian_no', 'guardian.last_name', 'guardian.first_name',
        'relationship', 'is_primary', 'is_emergency_contact', 'is_billing_target'
    ]
    csv_export_headers = {
        'student.student_no': '生徒番号',
        'student.last_name': '生徒姓',
        'student.first_name': '生徒名',
        'guardian.guardian_no': '保護者番号',
        'guardian.last_name': '保護者姓',
        'guardian.first_name': '保護者名',
        'relationship': '続柄',
        'is_primary': '主保護者',
        'is_emergency_contact': '緊急連絡先',
        'is_billing_target': '請求対象',
    }


@admin.register(Attendance)
class AttendanceAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """出席・欠席管理Admin"""
    list_display = ['get_student_name', 'get_student_no', 'schedule', 'status', 'check_in_time', 'check_out_time', 'absence_notified_at', 'tenant_ref']
    list_display_links = ['get_student_name']
    list_filter = ['tenant_ref', 'status', 'schedule__school', 'schedule__subject']
    search_fields = ['student__student_no', 'student__last_name', 'student__first_name', 'notes']
    ordering = ['-created_at']
    raw_id_fields = ['tenant_ref', 'schedule', 'student']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('基本情報', {
            'fields': ('tenant_ref', 'schedule', 'student')
        }),
        ('出席状況', {
            'fields': ('status', 'check_in_time', 'check_out_time')
        }),
        ('欠席情報', {
            'fields': ('absence_reason', 'absence_notified_at'),
            'classes': ('collapse',)
        }),
        ('備考', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def get_student_name(self, obj):
        if obj.student:
            return f"{obj.student.last_name} {obj.student.first_name}"
        return "-"
    get_student_name.short_description = '生徒名'
    get_student_name.admin_order_field = 'student__last_name'

    def get_student_no(self, obj):
        if obj.student:
            return obj.student.student_no
        return "-"
    get_student_no.short_description = '生徒番号'
    get_student_no.admin_order_field = 'student__student_no'

    # CSV Import設定
    csv_import_fields = {
        '生徒番号': 'student__student_no',
        '出席状況': 'status',
        '入室時間': 'check_in_time',
        '退室時間': 'check_out_time',
        '欠席理由': 'absence_reason',
        '欠席連絡日時': 'absence_notified_at',
        '備考': 'notes',
    }
    csv_required_fields = ['生徒番号', '出席状況']
    csv_unique_fields = []
    csv_export_fields = [
        'student.student_no', 'student.last_name', 'student.first_name',
        'schedule.id', 'status', 'check_in_time', 'check_out_time',
        'absence_reason', 'absence_notified_at', 'notes'
    ]
    csv_export_headers = {
        'student.student_no': '生徒番号',
        'student.last_name': '生徒姓',
        'student.first_name': '生徒名',
        'schedule.id': 'スケジュールID',
        'status': '出席状況',
        'check_in_time': '入室時間',
        'check_out_time': '退室時間',
        'absence_reason': '欠席理由',
        'absence_notified_at': '欠席連絡日時',
        'notes': '備考',
    }


@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    """生徒受講履歴Admin"""
    list_display = [
        'get_student_name',
        'get_student_no',
        'school',
        'brand',
        'get_day_of_week_display',
        'start_time',
        'status',
        'change_type',
        'effective_date',
        'end_date',
    ]
    list_display_links = ['get_student_name']
    list_filter = ['status', 'change_type', 'school', 'brand', 'day_of_week', 'effective_date']
    search_fields = [
        'student__student_no',
        'student__last_name',
        'student__first_name',
        'school__school_name',
        'brand__brand_name',
        'notes',
    ]
    ordering = ['-effective_date', '-created_at']
    raw_id_fields = ['student', 'school', 'brand', 'class_schedule', 'ticket', 'student_item', 'previous_enrollment']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'effective_date'

    fieldsets = (
        ('基本情報', {
            'fields': ('student', 'school', 'brand')
        }),
        ('スケジュール情報', {
            'fields': ('class_schedule', 'day_of_week', 'start_time', 'end_time')
        }),
        ('チケット・購入情報', {
            'fields': ('ticket', 'student_item'),
            'classes': ('collapse',)
        }),
        ('ステータス', {
            'fields': ('status', 'change_type', 'effective_date', 'end_date')
        }),
        ('変更履歴', {
            'fields': ('previous_enrollment',),
            'classes': ('collapse',)
        }),
        ('その他', {
            'fields': ('notes', 'metadata', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_student_name(self, obj):
        if obj.student:
            return f"{obj.student.last_name} {obj.student.first_name}"
        return "-"
    get_student_name.short_description = '生徒名'
    get_student_name.admin_order_field = 'student__last_name'

    def get_student_no(self, obj):
        if obj.student:
            return obj.student.student_no
        return "-"
    get_student_no.short_description = '生徒番号'
    get_student_no.admin_order_field = 'student__student_no'

    def get_day_of_week_display(self, obj):
        if obj.day_of_week is not None:
            days = ['月', '火', '水', '木', '金', '土', '日']
            if 0 <= obj.day_of_week < 7:
                return days[obj.day_of_week]
        return "-"
    get_day_of_week_display.short_description = '曜日'

    def get_queryset(self, request):
        """現在有効な記録を優先して表示"""
        qs = super().get_queryset(request).select_related(
            'student', 'school', 'brand', 'class_schedule'
        )
        return qs.order_by(
            Case(
                When(end_date__isnull=True, then=0),
                default=1,
            ),
            '-effective_date'
        )


@admin.register(AbsenceTicket)
class AbsenceTicketAdmin(admin.ModelAdmin):
    """欠席・振替チケット管理"""
    list_display = [
        'get_student_name',
        'get_student_no',
        'absence_date',
        'consumption_symbol',
        'status',
        'valid_until',
        'used_date',
    ]
    list_display_links = ['get_student_name']
    list_filter = ['status', 'consumption_symbol', 'absence_date']
    search_fields = [
        'student__student_no',
        'student__last_name',
        'student__first_name',
        'consumption_symbol',
        'notes',
    ]
    ordering = ['-absence_date']
    raw_id_fields = ['student', 'original_ticket', 'class_schedule', 'used_class_schedule']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'absence_date'

    fieldsets = (
        ('基本情報', {
            'fields': ('student', 'absence_date', 'class_schedule')
        }),
        ('チケット情報', {
            'fields': ('original_ticket', 'consumption_symbol', 'status', 'valid_until')
        }),
        ('振替使用', {
            'fields': ('used_date', 'used_class_schedule'),
            'description': '振替で使用した場合の情報'
        }),
        ('その他', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_student_name(self, obj):
        if obj.student:
            return f"{obj.student.last_name} {obj.student.first_name}"
        return "-"
    get_student_name.short_description = '生徒名'
    get_student_name.admin_order_field = 'student__last_name'

    def get_student_no(self, obj):
        if obj.student:
            return obj.student.student_no
        return "-"
    get_student_no.short_description = '生徒番号'
    get_student_no.admin_order_field = 'student__student_no'

    def get_queryset(self, request):
        """発行済を優先して表示"""
        qs = super().get_queryset(request).select_related('student', 'class_schedule', 'original_ticket')
        return qs.order_by(
            Case(
                When(status='issued', then=0),
                default=1,
            ),
            '-absence_date'
        )


@admin.register(SuspensionRequest)
class SuspensionRequestAdmin(admin.ModelAdmin):
    """休会申請Admin"""
    list_display = [
        'get_student_name',
        'get_student_no',
        'school',
        'brand',
        'suspend_from',
        'suspend_until',
        'status',
        'keep_seat',
        'requested_at',
    ]
    list_display_links = ['get_student_name']
    list_filter = ['status', 'reason', 'keep_seat', 'school', 'brand', 'suspend_from']
    search_fields = [
        'student__student_no',
        'student__last_name',
        'student__first_name',
        'reason_detail',
        'process_notes',
    ]
    ordering = ['-requested_at']
    raw_id_fields = ['student', 'school', 'brand', 'requested_by', 'processed_by', 'resumed_by']
    readonly_fields = ['requested_at', 'processed_at', 'created_at', 'updated_at']
    date_hierarchy = 'requested_at'

    fieldsets = (
        ('申請情報', {
            'fields': ('student', 'school', 'brand', 'status')
        }),
        ('休会期間', {
            'fields': ('suspend_from', 'suspend_until', 'keep_seat', 'monthly_fee_during_suspension')
        }),
        ('理由', {
            'fields': ('reason', 'reason_detail'),
        }),
        ('申請者', {
            'fields': ('requested_by', 'requested_at'),
            'classes': ('collapse',)
        }),
        ('処理情報', {
            'fields': ('processed_by', 'processed_at', 'process_notes'),
            'classes': ('collapse',)
        }),
        ('復会情報', {
            'fields': ('resumed_at', 'resumed_by'),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_requests', 'reject_requests']

    def get_student_name(self, obj):
        if obj.student:
            return f"{obj.student.last_name} {obj.student.first_name}"
        return "-"
    get_student_name.short_description = '生徒名'
    get_student_name.admin_order_field = 'student__last_name'

    def get_student_no(self, obj):
        if obj.student:
            return obj.student.student_no
        return "-"
    get_student_no.short_description = '生徒番号'
    get_student_no.admin_order_field = 'student__student_no'

    def get_queryset(self, request):
        """申請中を優先して表示"""
        qs = super().get_queryset(request).select_related('student', 'school', 'brand')
        return qs.order_by(
            Case(
                When(status='pending', then=0),
                default=1,
            ),
            '-requested_at'
        )

    def approve_requests(self, request, queryset):
        """選択した申請を承認"""
        count = 0
        for obj in queryset.filter(status='pending'):
            obj.approve(request.user)
            count += 1
        self.message_user(request, f'{count}件の休会申請を承認しました。')
    approve_requests.short_description = '選択した申請を承認'

    def reject_requests(self, request, queryset):
        """選択した申請を却下"""
        count = queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f'{count}件の休会申請を却下しました。')
    reject_requests.short_description = '選択した申請を却下'


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    """退会申請Admin"""
    list_display = [
        'get_student_name',
        'get_student_no',
        'school',
        'brand',
        'withdrawal_date',
        'status',
        'reason',
        'refund_amount',
        'requested_at',
    ]
    list_display_links = ['get_student_name']
    list_filter = ['status', 'reason', 'school', 'brand', 'withdrawal_date']
    search_fields = [
        'student__student_no',
        'student__last_name',
        'student__first_name',
        'reason_detail',
        'process_notes',
    ]
    ordering = ['-requested_at']
    raw_id_fields = ['student', 'school', 'brand', 'requested_by', 'processed_by']
    readonly_fields = ['requested_at', 'processed_at', 'created_at', 'updated_at']
    date_hierarchy = 'requested_at'

    fieldsets = (
        ('申請情報', {
            'fields': ('student', 'school', 'brand', 'status')
        }),
        ('退会日程', {
            'fields': ('withdrawal_date', 'last_lesson_date'),
        }),
        ('理由', {
            'fields': ('reason', 'reason_detail'),
        }),
        ('返金情報', {
            'fields': ('refund_amount', 'refund_calculated', 'remaining_tickets'),
            'description': '退会時の返金計算情報'
        }),
        ('申請者', {
            'fields': ('requested_by', 'requested_at'),
            'classes': ('collapse',)
        }),
        ('処理情報', {
            'fields': ('processed_by', 'processed_at', 'process_notes'),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_requests', 'reject_requests']

    def get_student_name(self, obj):
        if obj.student:
            return f"{obj.student.last_name} {obj.student.first_name}"
        return "-"
    get_student_name.short_description = '生徒名'
    get_student_name.admin_order_field = 'student__last_name'

    def get_student_no(self, obj):
        if obj.student:
            return obj.student.student_no
        return "-"
    get_student_no.short_description = '生徒番号'
    get_student_no.admin_order_field = 'student__student_no'

    def get_queryset(self, request):
        """申請中を優先して表示"""
        qs = super().get_queryset(request).select_related('student', 'school', 'brand')
        return qs.order_by(
            Case(
                When(status='pending', then=0),
                default=1,
            ),
            '-requested_at'
        )

    def approve_requests(self, request, queryset):
        """選択した申請を承認"""
        count = 0
        for obj in queryset.filter(status='pending'):
            obj.approve(request.user)
            count += 1
        self.message_user(request, f'{count}件の退会申請を承認しました。')
    approve_requests.short_description = '選択した申請を承認'

    def reject_requests(self, request, queryset):
        """選択した申請を却下"""
        count = queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f'{count}件の退会申請を却下しました。')
    reject_requests.short_description = '選択した申請を却下'


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    """銀行口座Admin"""
    list_display = [
        'get_guardian_name',
        'bank_name',
        'branch_name',
        'account_type',
        'account_number',
        'account_holder',
        'is_primary',
        'is_active',
    ]
    list_display_links = ['get_guardian_name', 'bank_name']
    list_filter = ['is_primary', 'is_active', 'account_type']
    search_fields = [
        'guardian__guardian_no',
        'guardian__last_name',
        'guardian__first_name',
        'bank_name',
        'branch_name',
        'account_holder',
        'account_holder_kana',
    ]
    ordering = ['-created_at']
    raw_id_fields = ['guardian']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('保護者情報', {
            'fields': ('guardian',)
        }),
        ('金融機関情報', {
            'fields': (
                ('bank_name', 'bank_code'),
                ('branch_name', 'branch_code'),
            )
        }),
        ('口座情報', {
            'fields': (
                'account_type',
                'account_number',
                ('account_holder', 'account_holder_kana'),
            )
        }),
        ('設定', {
            'fields': ('is_primary', 'is_active'),
        }),
        ('備考', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_guardian_name(self, obj):
        if obj.guardian:
            return f"{obj.guardian.last_name} {obj.guardian.first_name}"
        return "-"
    get_guardian_name.short_description = '保護者名'
    get_guardian_name.admin_order_field = 'guardian__last_name'


@admin.register(BankAccountChangeRequest)
class BankAccountChangeRequestAdmin(admin.ModelAdmin):
    """銀行口座変更申請Admin（作業一覧）"""
    list_display = [
        'get_guardian_name',
        'get_guardian_no',
        'request_type',
        'bank_name',
        'branch_name',
        'account_number',
        'is_primary',
        'status',
        'requested_at',
    ]
    list_display_links = ['get_guardian_name']
    list_filter = ['status', 'request_type', 'requested_at']
    search_fields = [
        'guardian__guardian_no',
        'guardian__last_name',
        'guardian__first_name',
        'bank_name',
        'branch_name',
        'account_holder',
        'request_notes',
    ]
    ordering = ['-requested_at']
    raw_id_fields = ['guardian', 'existing_account', 'requested_by', 'processed_by']
    readonly_fields = ['requested_at', 'processed_at', 'created_at', 'updated_at']
    date_hierarchy = 'requested_at'

    fieldsets = (
        ('申請情報', {
            'fields': ('guardian', 'request_type', 'existing_account', 'status')
        }),
        ('金融機関情報', {
            'fields': (
                ('bank_name', 'bank_code'),
                ('branch_name', 'branch_code'),
            )
        }),
        ('口座情報', {
            'fields': (
                'account_type',
                'account_number',
                ('account_holder', 'account_holder_kana'),
                'is_primary',
            )
        }),
        ('申請者', {
            'fields': ('requested_by', 'requested_at', 'request_notes'),
        }),
        ('処理情報', {
            'fields': ('processed_by', 'processed_at', 'process_notes'),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_requests', 'reject_requests']

    def get_guardian_name(self, obj):
        if obj.guardian:
            return f"{obj.guardian.last_name} {obj.guardian.first_name}"
        return "-"
    get_guardian_name.short_description = '保護者名'
    get_guardian_name.admin_order_field = 'guardian__last_name'

    def get_guardian_no(self, obj):
        if obj.guardian:
            return obj.guardian.guardian_no
        return "-"
    get_guardian_no.short_description = '保護者番号'
    get_guardian_no.admin_order_field = 'guardian__guardian_no'

    def get_queryset(self, request):
        """申請中を優先して表示（作業一覧として機能）"""
        qs = super().get_queryset(request).select_related('guardian', 'existing_account')
        return qs.order_by(
            Case(
                When(status='pending', then=0),
                default=1,
            ),
            '-requested_at'
        )

    def approve_requests(self, request, queryset):
        """選択した申請を承認"""
        count = 0
        for obj in queryset.filter(status='pending'):
            obj.approve(request.user)
            count += 1
        self.message_user(request, f'{count}件の銀行口座申請を承認しました。')
    approve_requests.short_description = '選択した申請を承認'

    def reject_requests(self, request, queryset):
        """選択した申請を却下"""
        count = 0
        for obj in queryset.filter(status='pending'):
            obj.reject(request.user, notes='管理者により却下')
            count += 1
        self.message_user(request, f'{count}件の銀行口座申請を却下しました。')
    reject_requests.short_description = '選択した申請を却下'


@admin.register(FriendshipRegistration)
class FriendshipRegistrationAdmin(admin.ModelAdmin):
    """友達登録Admin（FS登録）"""
    list_display = [
        'get_requester_name',
        'get_requester_no',
        'get_target_name',
        'get_target_no',
        'status_badge',
        'friend_code',
        'requested_at',
        'accepted_at',
    ]
    list_display_links = ['get_requester_name']
    list_filter = ['status', 'requested_at', 'accepted_at']
    search_fields = [
        'requester__guardian_no',
        'requester__last_name',
        'requester__first_name',
        'target__guardian_no',
        'target__last_name',
        'target__first_name',
        'friend_code',
        'notes',
    ]
    ordering = ['-requested_at']
    raw_id_fields = ['requester', 'target']
    readonly_fields = ['requested_at', 'accepted_at', 'created_at', 'updated_at']
    date_hierarchy = 'requested_at'

    fieldsets = (
        ('友達登録情報', {
            'fields': ('requester', 'target', 'status', 'friend_code')
        }),
        ('日時', {
            'fields': ('requested_at', 'accepted_at'),
        }),
        ('備考', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['accept_registrations', 'reject_registrations']

    def get_requester_name(self, obj):
        if obj.requester:
            return f"{obj.requester.last_name} {obj.requester.first_name}"
        return "-"
    get_requester_name.short_description = '申請者'
    get_requester_name.admin_order_field = 'requester__last_name'

    def get_requester_no(self, obj):
        if obj.requester:
            return obj.requester.guardian_no
        return "-"
    get_requester_no.short_description = '申請者番号'

    def get_target_name(self, obj):
        if obj.target:
            return f"{obj.target.last_name} {obj.target.first_name}"
        return "-"
    get_target_name.short_description = '対象者'
    get_target_name.admin_order_field = 'target__last_name'

    def get_target_no(self, obj):
        if obj.target:
            return obj.target.guardian_no
        return "-"
    get_target_no.short_description = '対象者番号'

    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'accepted': 'green',
            'rejected': 'red',
            'cancelled': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'ステータス'

    def get_queryset(self, request):
        """申請中を優先して表示"""
        qs = super().get_queryset(request).select_related('requester', 'target')
        return qs.order_by(
            Case(
                When(status='pending', then=0),
                default=1,
            ),
            '-requested_at'
        )

    def accept_registrations(self, request, queryset):
        """選択した友達登録を承認"""
        count = 0
        for obj in queryset.filter(status='pending'):
            obj.accept()
            count += 1
        self.message_user(request, f'{count}件の友達登録を承認しました。両者にFS割引が適用されます。')
    accept_registrations.short_description = '選択した友達登録を承認'

    def reject_registrations(self, request, queryset):
        """選択した友達登録を拒否"""
        count = 0
        for obj in queryset.filter(status='pending'):
            obj.reject()
            count += 1
        self.message_user(request, f'{count}件の友達登録を拒否しました。')
    reject_registrations.short_description = '選択した友達登録を拒否'


@admin.register(FSDiscount)
class FSDiscountAdmin(admin.ModelAdmin):
    """FS割引Admin（友達紹介割引）"""
    list_display = [
        'get_guardian_name',
        'get_guardian_no',
        'discount_type_display',
        'discount_value_display',
        'status_badge',
        'valid_from',
        'valid_until',
        'applied_amount_display',
        'used_at',
    ]
    list_display_links = ['get_guardian_name']
    list_filter = ['status', 'discount_type', 'valid_from', 'valid_until']
    search_fields = [
        'guardian__guardian_no',
        'guardian__last_name',
        'guardian__first_name',
        'notes',
    ]
    ordering = ['-created_at']
    raw_id_fields = ['guardian', 'friendship', 'used_invoice']
    readonly_fields = ['used_at', 'created_at', 'updated_at']
    date_hierarchy = 'valid_from'

    fieldsets = (
        ('基本情報', {
            'fields': ('guardian', 'friendship', 'status')
        }),
        ('割引内容', {
            'fields': ('discount_type', 'discount_value', 'valid_from', 'valid_until')
        }),
        ('使用情報', {
            'fields': ('used_at', 'used_invoice', 'applied_amount'),
            'classes': ('collapse',)
        }),
        ('備考', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_guardian_name(self, obj):
        if obj.guardian:
            return f"{obj.guardian.last_name} {obj.guardian.first_name}"
        return "-"
    get_guardian_name.short_description = '保護者名'
    get_guardian_name.admin_order_field = 'guardian__last_name'

    def get_guardian_no(self, obj):
        if obj.guardian:
            return obj.guardian.guardian_no
        return "-"
    get_guardian_no.short_description = '保護者番号'
    get_guardian_no.admin_order_field = 'guardian__guardian_no'

    def discount_type_display(self, obj):
        return obj.get_discount_type_display()
    discount_type_display.short_description = '割引タイプ'

    def discount_value_display(self, obj):
        if obj.discount_type == 'percentage':
            return f"{obj.discount_value}%"
        elif obj.discount_type == 'fixed':
            return f"¥{obj.discount_value:,.0f}"
        elif obj.discount_type == 'months_free':
            return f"{int(obj.discount_value)}ヶ月"
        return str(obj.discount_value)
    discount_value_display.short_description = '割引値'

    def applied_amount_display(self, obj):
        if obj.applied_amount:
            return f"¥{obj.applied_amount:,.0f}"
        return "-"
    applied_amount_display.short_description = '適用額'

    def status_badge(self, obj):
        colors = {
            'active': 'green',
            'used': 'blue',
            'expired': 'gray',
            'cancelled': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'ステータス'

    def get_queryset(self, request):
        """有効な割引を優先して表示"""
        qs = super().get_queryset(request).select_related('guardian', 'friendship')
        return qs.order_by(
            Case(
                When(status='active', then=0),
                default=1,
            ),
            '-created_at'
        )
