from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.core.admin_csv import CSVImportExportMixin
from .models import User


@admin.register(User)
class UserAdmin(CSVImportExportMixin, BaseUserAdmin):
    list_display = ['email', 'full_name', 'user_type', 'role', 'is_active', 'created_at']
    list_filter = ['user_type', 'role', 'is_active', 'is_staff']
    search_fields = ['email', 'last_name', 'first_name', 'user_no']
    ordering = ['-created_at']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('基本情報', {'fields': ('last_name', 'first_name', 'last_name_kana', 'first_name_kana', 'display_name')}),
        ('連絡先', {'fields': ('phone', 'line_id')}),
        ('プロフィール', {'fields': ('profile_image_url', 'birth_date', 'gender')}),
        ('テナント・所属', {'fields': ('tenant_id', 'primary_school_id', 'primary_brand_id')}),
        ('権限', {'fields': ('user_type', 'role', 'is_active', 'is_staff', 'is_superuser', 'permissions')}),
        ('関連', {'fields': ('student_id', 'staff_id')}),
        ('セキュリティ', {'fields': ('failed_login_count', 'locked_until', 'password_changed_at')}),
        ('日時', {'fields': ('last_login_at', 'created_at', 'updated_at', 'deleted_at')}),
    )

    readonly_fields = ['created_at', 'updated_at', 'last_login_at']

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'last_name', 'first_name', 'user_type', 'role'),
        }),
    )

    # CSV Import設定
    csv_import_fields = {
        'メールアドレス': 'email',
        '姓': 'last_name',
        '名': 'first_name',
        '姓（カナ）': 'last_name_kana',
        '名（カナ）': 'first_name_kana',
        '表示名': 'display_name',
        '電話番号': 'phone',
        'ユーザー種別': 'user_type',
        '役割': 'role',
        '有効': 'is_active',
    }
    csv_required_fields = ['メールアドレス', '姓', '名']
    csv_unique_fields = ['email']
    csv_export_fields = [
        'email', 'last_name', 'first_name', 'last_name_kana', 'first_name_kana',
        'display_name', 'phone', 'user_type', 'role', 'is_active', 'is_staff', 'created_at'
    ]
    csv_export_headers = {
        'email': 'メールアドレス',
        'last_name': '姓',
        'first_name': '名',
        'last_name_kana': '姓（カナ）',
        'first_name_kana': '名（カナ）',
        'display_name': '表示名',
        'phone': '電話番号',
        'user_type': 'ユーザー種別',
        'role': '役割',
        'is_active': '有効',
        'is_staff': 'スタッフ権限',
        'created_at': '作成日時',
    }
