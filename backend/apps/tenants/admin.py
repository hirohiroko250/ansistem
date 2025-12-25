from django.contrib import admin
from django.utils.html import format_html
from apps.core.admin_csv import CSVImportExportMixin
from .models import Tenant, Employee, Position, FeatureMaster, PositionPermission


class ChildTenantInline(admin.TabularInline):
    """子テナントインライン表示"""
    model = Tenant
    fk_name = 'parent'
    extra = 0
    fields = ['tenant_code', 'tenant_name', 'tenant_type', 'plan_type', 'is_active']
    readonly_fields = ['tenant_code', 'tenant_name']
    show_change_link = True
    verbose_name = '子会社'
    verbose_name_plural = '子会社一覧'

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Tenant)
class TenantAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['tenant_code', 'tenant_name', 'tenant_type', 'parent_link', 'children_count', 'plan_type', 'is_active', 'created_at']

    # CSV Import設定
    csv_import_fields = {
        'テナントコード': 'tenant_code',
        'テナント名': 'tenant_name',
        'テナント種別': 'tenant_type',
        'プラン': 'plan_type',
        '最大校舎数': 'max_schools',
        '最大ユーザー数': 'max_users',
        '連絡先メール': 'contact_email',
        '連絡先電話': 'contact_phone',
        '有効': 'is_active',
    }
    csv_required_fields = ['テナントコード', 'テナント名']
    csv_unique_fields = ['tenant_code']
    csv_export_fields = [
        'tenant_code', 'tenant_name', 'tenant_type', 'parent.tenant_name',
        'plan_type', 'max_schools', 'max_users', 'contact_email', 'contact_phone', 'is_active'
    ]
    csv_export_headers = {
        'tenant_code': 'テナントコード',
        'tenant_name': 'テナント名',
        'tenant_type': 'テナント種別',
        'parent.tenant_name': '親会社',
        'plan_type': 'プラン',
        'max_schools': '最大校舎数',
        'max_users': '最大ユーザー数',
        'contact_email': '連絡先メール',
        'contact_phone': '連絡先電話',
        'is_active': '有効',
    }
    list_filter = ['tenant_type', 'plan_type', 'is_active', 'parent']
    search_fields = ['tenant_code', 'tenant_name', 'contact_email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'children_list']
    ordering = ['parent', 'tenant_code']
    raw_id_fields = ['parent']
    inlines = [ChildTenantInline]

    fieldsets = (
        ('基本情報', {
            'fields': ('tenant_code', 'tenant_name', 'tenant_type', 'parent')
        }),
        ('グループ情報', {
            'fields': ('children_list',),
            'classes': ('collapse',),
        }),
        ('契約情報', {
            'fields': ('plan_type', 'max_schools', 'max_users')
        }),
        ('連絡先', {
            'fields': ('contact_email', 'contact_phone')
        }),
        ('設定', {
            'fields': ('settings', 'features', 'is_active'),
            'classes': ('collapse',),
        }),
        ('システム情報', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def parent_link(self, obj):
        if obj.parent:
            return format_html(
                '<a href="/admin/tenants/tenant/{}/change/">{}</a>',
                obj.parent.id,
                obj.parent.tenant_name
            )
        return '-'
    parent_link.short_description = '親会社'

    def children_count(self, obj):
        count = obj.children.count()
        if count > 0:
            return format_html(
                '<a href="/admin/tenants/tenant/?parent__id__exact={}">{} 社</a>',
                obj.id,
                count
            )
        return '-'
    children_count.short_description = '子会社数'

    def children_list(self, obj):
        children = obj.children.all()
        if children:
            links = []
            for child in children:
                links.append(format_html(
                    '<a href="/admin/tenants/tenant/{}/change/">{} ({})</a>',
                    child.id,
                    child.tenant_name,
                    child.tenant_code
                ))
            return format_html('<br>'.join(links))
        return '子会社なし'
    children_list.short_description = '子会社一覧'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent').prefetch_related('children')


class PositionPermissionInline(admin.TabularInline):
    """役職権限インライン"""
    model = PositionPermission
    extra = 0
    fields = ['feature', 'has_permission']
    autocomplete_fields = ['feature']


@admin.register(Position)
class PositionAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'position_name', 'position_code', 'rank',
        'school_restriction', 'brand_restriction', 'is_accounting', 'is_active'
    ]
    list_filter = ['is_active', 'school_restriction', 'brand_restriction', 'is_accounting']
    search_fields = ['position_name', 'position_code']
    ordering = ['-rank', 'position_name']
    inlines = [PositionPermissionInline]

    fieldsets = (
        ('基本情報', {
            'fields': ('position_code', 'position_name', 'rank', 'is_active')
        }),
        ('グローバル権限設定', {
            'fields': (
                'school_restriction',
                'brand_restriction',
                'bulk_email_restriction',
                'email_approval_required',
                'is_accounting',
            ),
            'description': 'チェックONの場合、制限が適用されます'
        }),
    )

    csv_import_fields = {
        '役職コード': 'position_code',
        '役職名': 'position_name',
        'ランク': 'rank',
        '校舎制限': 'school_restriction',
        'ブランド制限': 'brand_restriction',
        'メール一括送信制限': 'bulk_email_restriction',
        'メール上長承認必要': 'email_approval_required',
        '経理権限': 'is_accounting',
        '有効': 'is_active',
    }
    csv_required_fields = ['役職名']
    csv_export_fields = [
        'position_code', 'position_name', 'rank',
        'school_restriction', 'brand_restriction', 'bulk_email_restriction',
        'email_approval_required', 'is_accounting', 'is_active'
    ]
    csv_export_headers = {
        'position_code': '役職コード',
        'position_name': '役職名',
        'rank': 'ランク',
        'school_restriction': '校舎制限',
        'brand_restriction': 'ブランド制限',
        'bulk_email_restriction': 'メール一括送信制限',
        'email_approval_required': 'メール上長承認必要',
        'is_accounting': '経理権限',
        'is_active': '有効',
    }


@admin.register(FeatureMaster)
class FeatureMasterAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """機能マスタ管理"""
    list_display = ['feature_code', 'feature_name', 'parent_code', 'category', 'display_order', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['feature_code', 'feature_name', 'category']
    ordering = ['display_order', 'feature_code']

    csv_import_fields = {
        '機能コード': 'feature_code',
        '機能名': 'feature_name',
        '親機能コード': 'parent_code',
        'カテゴリ': 'category',
        '説明': 'description',
        '表示順': 'display_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['機能コード', '機能名']
    csv_unique_fields = ['feature_code']
    csv_export_fields = ['feature_code', 'feature_name', 'parent_code', 'category', 'description', 'display_order', 'is_active']
    csv_export_headers = {
        'feature_code': '機能コード',
        'feature_name': '機能名',
        'parent_code': '親機能コード',
        'category': 'カテゴリ',
        'description': '説明',
        'display_order': '表示順',
        'is_active': '有効',
    }


@admin.register(PositionPermission)
class PositionPermissionAdmin(admin.ModelAdmin):
    """役職権限管理"""
    list_display = ['position', 'feature', 'has_permission_display']
    list_filter = ['position', 'has_permission', 'feature__category']
    search_fields = ['position__position_name', 'feature__feature_name', 'feature__feature_code']
    autocomplete_fields = ['position', 'feature']
    list_editable = []

    def has_permission_display(self, obj):
        if obj.has_permission:
            return format_html('<span style="color: green; font-weight: bold;">○</span>')
        return format_html('<span style="color: red;">×</span>')
    has_permission_display.short_description = '権限'


@admin.register(Employee)
class EmployeeAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = [
        'full_name', 'department', 'position', 'email', 'phone',
        'discount_flag', 'discount_amount', 'discount_unit', 'is_active'
    ]
    list_filter = ['department', 'position', 'is_active', 'discount_flag', 'prefecture']
    search_fields = ['last_name', 'first_name', 'email', 'phone', 'department']
    ordering = ['department', 'last_name', 'first_name']
    autocomplete_fields = ['position']

    # CSV Import設定
    csv_import_fields = {
        '社員番号': 'employee_no',
        '部署': 'department',
        '姓': 'last_name',
        '名': 'first_name',
        'メールアドレス': 'email',
        '電話番号': 'phone',
        '役職': 'position_text',
        '郵便番号': 'postal_code',
        '都道府県': 'prefecture',
        '市区町村': 'city',
        '住所': 'address',
        '国籍': 'nationality',
        '社員割引フラッグ': 'discount_flag',
        '社員割引額': 'discount_amount',
        '社員割引額単位': 'discount_unit',
        '社員割引請求カテゴリー名': 'discount_category_name',
        '社員割引請求カテゴリー区分': 'discount_category_code',
    }
    csv_required_fields = ['姓', '名']
    csv_export_fields = [
        'employee_no', 'department', 'last_name', 'first_name',
        'email', 'phone', 'position.position_name', 'position_text', 'postal_code', 'prefecture',
        'city', 'address', 'discount_flag', 'discount_amount',
        'discount_unit', 'is_active'
    ]
    csv_export_headers = {
        'employee_no': '社員番号',
        'department': '部署',
        'last_name': '姓',
        'first_name': '名',
        'email': 'メールアドレス',
        'phone': '電話番号',
        'position.position_name': '役職',
        'position_text': '役職（テキスト）',
        'postal_code': '郵便番号',
        'prefecture': '都道府県',
        'city': '市区町村',
        'address': '住所',
        'discount_flag': '社員割引フラグ',
        'discount_amount': '社員割引額',
        'discount_unit': '社員割引額単位',
        'is_active': '有効',
    }

    filter_horizontal = ['schools', 'brands']

    fieldsets = (
        ('基本情報', {
            'fields': (
                ('last_name', 'first_name'),
                'employee_no',
                'department',
                ('position', 'position_text'),
                ('email', 'phone'),
                'guardian',
            )
        }),
        ('所属', {
            'fields': (
                'tenant_ref',
                'schools',
                'brands',
            )
        }),
        ('雇用情報', {
            'fields': (
                ('hire_date', 'termination_date'),
                'is_active',
            )
        }),
        ('住所', {
            'fields': (
                'postal_code',
                ('prefecture', 'city'),
                'address',
                'nationality',
            ),
            'classes': ('collapse',),
        }),
        ('社員割引', {
            'fields': (
                'discount_flag',
                ('discount_amount', 'discount_unit'),
                ('discount_category_name', 'discount_category_code'),
            ),
            'classes': ('collapse',),
        }),
        ('システム情報', {
            'fields': (
                'ozaworks_registered',
            ),
            'classes': ('collapse',),
        }),
    )

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = '氏名'
