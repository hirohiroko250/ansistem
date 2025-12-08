from django.contrib import admin
from django.utils.html import format_html
from apps.core.admin_csv import CSVImportExportMixin
from .models import Tenant


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
