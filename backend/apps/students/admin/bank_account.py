"""
Bank Account Admin - 銀行口座管理Admin
"""
from django.contrib import admin
from django.db.models import Case, When
from ..models import BankAccount, BankAccountChangeRequest


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    """銀行口座履歴Admin

    口座変更時に旧口座を履歴として保存するテーブル。
    現在有効な口座はGuardianモデルに直接保存されています。
    """
    list_display = [
        'get_guardian_name',
        'bank_name',
        'branch_name',
        'account_type',
        'account_number',
        'account_holder',
        'is_active',
        'created_at',
    ]
    list_display_links = ['get_guardian_name', 'bank_name']
    list_filter = ['is_active', 'account_type', 'created_at']
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

    def save_model(self, request, obj, form, change):
        """ステータスが承認済に変更されたらapproveメソッドを呼ぶ"""
        if change and 'status' in form.changed_data:
            old_status = BankAccountChangeRequest.objects.filter(pk=obj.pk).values_list('status', flat=True).first()
            if old_status == 'pending' and obj.status == 'approved':
                # save()は呼ばずにapprove()を呼ぶ（approve内でsaveされる）
                obj.approve(request.user, notes=obj.process_notes or '')
                return
        super().save_model(request, obj, form, change)
