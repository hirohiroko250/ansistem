"""
Custom Exception Handlers and Exceptions
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from django.core.exceptions import PermissionDenied, ValidationError


def custom_exception_handler(exc, context):
    """カスタム例外ハンドラー"""
    # DRF標準の例外処理を実行
    response = exception_handler(exc, context)

    if response is not None:
        # レスポンスをカスタマイズ
        custom_response_data = {
            'success': False,
            'error': {
                'code': response.status_code,
                'message': get_error_message(exc),
                'details': response.data if hasattr(response, 'data') else None,
            }
        }
        response.data = custom_response_data
    else:
        # DRFが処理しなかった例外
        if isinstance(exc, Http404):
            data = {
                'success': False,
                'error': {
                    'code': 404,
                    'message': 'リソースが見つかりません',
                    'details': str(exc),
                }
            }
            return Response(data, status=status.HTTP_404_NOT_FOUND)
        elif isinstance(exc, PermissionDenied):
            data = {
                'success': False,
                'error': {
                    'code': 403,
                    'message': 'アクセス権限がありません',
                    'details': str(exc),
                }
            }
            return Response(data, status=status.HTTP_403_FORBIDDEN)
        elif isinstance(exc, ValidationError):
            data = {
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'バリデーションエラー',
                    'details': exc.messages if hasattr(exc, 'messages') else str(exc),
                }
            }
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

    return response


def get_error_message(exc):
    """例外からエラーメッセージを取得"""
    if hasattr(exc, 'detail'):
        if isinstance(exc.detail, str):
            return exc.detail
        elif isinstance(exc.detail, dict):
            return '入力内容に問題があります'
        elif isinstance(exc.detail, list):
            return exc.detail[0] if exc.detail else 'エラーが発生しました'
    return str(exc) if str(exc) else 'エラーが発生しました'


# Custom Exceptions
class OZAException(Exception):
    """OZAシステム基底例外"""
    default_message = 'エラーが発生しました'
    default_code = 'error'

    def __init__(self, message=None, code=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        super().__init__(self.message)


class TenantNotFoundError(OZAException):
    """テナントが見つからない"""
    default_message = 'テナントが見つかりません'
    default_code = 'tenant_not_found'


class TenantAccessDeniedError(OZAException):
    """テナントへのアクセス権限がない"""
    default_message = 'このテナントへのアクセス権限がありません'
    default_code = 'tenant_access_denied'


class ResourceNotFoundError(OZAException):
    """リソースが見つからない"""
    default_message = '指定されたリソースが見つかりません'
    default_code = 'resource_not_found'


class DuplicateResourceError(OZAException):
    """リソースが重複"""
    default_message = '既に存在するリソースです'
    default_code = 'duplicate_resource'


class InvalidOperationError(OZAException):
    """無効な操作"""
    default_message = 'この操作は許可されていません'
    default_code = 'invalid_operation'


class BusinessRuleViolationError(OZAException):
    """ビジネスルール違反"""
    default_message = 'ビジネスルールに違反しています'
    default_code = 'business_rule_violation'
