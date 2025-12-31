"""
Friendship Admin - 友達登録・FS割引管理Admin
"""
from django.contrib import admin
from django.db.models import Case, When
from django.utils.html import format_html
from ..models import FriendshipRegistration, FSDiscount


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
