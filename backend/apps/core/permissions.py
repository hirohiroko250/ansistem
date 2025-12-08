"""
Custom Permissions
"""
from rest_framework import permissions


class IsTenantUser(permissions.BasePermission):
    """テナントユーザーであることを確認"""
    message = 'テナントへのアクセス権限がありません'

    def has_permission(self, request, view):
        # tenant_idはrequest.tenant_idまたはrequest.user.tenant_idから取得
        tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)
        return (
            request.user and
            request.user.is_authenticated and
            tenant_id is not None
        )


class IsTenantAdmin(permissions.BasePermission):
    """テナント管理者であることを確認"""
    message = 'テナント管理者権限が必要です'

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request, 'tenant') and
            request.tenant is not None and
            request.user.role in ['ADMIN', 'SUPER_ADMIN']
        )


class IsSchoolManager(permissions.BasePermission):
    """校舎管理者であることを確認"""
    message = '校舎管理者権限が必要です'

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ['ADMIN', 'SUPER_ADMIN', 'SCHOOL_MANAGER']
        )


class IsTeacher(permissions.BasePermission):
    """講師であることを確認"""
    message = '講師権限が必要です'

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.user_type in ['TEACHER', 'STAFF'] or
            request.user.role in ['ADMIN', 'SUPER_ADMIN', 'SCHOOL_MANAGER']
        )


class IsStaffOrAdmin(permissions.BasePermission):
    """スタッフまたは管理者であることを確認"""
    message = 'スタッフ権限が必要です'

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.user_type in ['TEACHER', 'STAFF', 'ADMIN'] or
            request.user.role in ['ADMIN', 'SUPER_ADMIN', 'SCHOOL_MANAGER']
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """オブジェクトの所有者または管理者であることを確認"""
    message = 'このリソースへのアクセス権限がありません'

    def has_object_permission(self, request, view, obj):
        # 管理者は全てアクセス可能
        if request.user.role in ['ADMIN', 'SUPER_ADMIN']:
            return True

        # オブジェクトの所有者チェック
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        if hasattr(obj, 'student') and hasattr(request.user, 'student_id'):
            return obj.student_id == request.user.student_id

        return False


class ReadOnlyOrAdmin(permissions.BasePermission):
    """読み取り専用または管理者"""
    message = '読み取り専用アクセスのみ許可されています'

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ['ADMIN', 'SUPER_ADMIN']
        )
