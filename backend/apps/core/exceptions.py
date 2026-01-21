"""
Custom Exception Handlers and Exceptions

統一エラーレスポンス形式:
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "ユーザー向けメッセージ",
        "details": { "field": ["エラー詳細"] }  // オプション
    }
}
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework import status
from django.http import Http404
from django.core.exceptions import PermissionDenied, ValidationError


# =============================================================================
# エラーコード定義
# =============================================================================
class ErrorCode:
    """統一エラーコード"""
    # 認証・認可
    UNAUTHORIZED = 'UNAUTHORIZED'
    FORBIDDEN = 'FORBIDDEN'
    TOKEN_EXPIRED = 'TOKEN_EXPIRED'
    INVALID_CREDENTIALS = 'INVALID_CREDENTIALS'
    ACCOUNT_LOCKED = 'ACCOUNT_LOCKED'

    # バリデーション
    VALIDATION_ERROR = 'VALIDATION_ERROR'
    INVALID_FORMAT = 'INVALID_FORMAT'
    REQUIRED_FIELD = 'REQUIRED_FIELD'
    DUPLICATE_VALUE = 'DUPLICATE_VALUE'

    # リソース
    NOT_FOUND = 'NOT_FOUND'
    RESOURCE_NOT_FOUND = 'RESOURCE_NOT_FOUND'
    TENANT_NOT_FOUND = 'TENANT_NOT_FOUND'
    STUDENT_NOT_FOUND = 'STUDENT_NOT_FOUND'
    GUARDIAN_NOT_FOUND = 'GUARDIAN_NOT_FOUND'
    SCHOOL_NOT_FOUND = 'SCHOOL_NOT_FOUND'

    # ビジネスロジック
    BUSINESS_RULE_VIOLATION = 'BUSINESS_RULE_VIOLATION'
    INVALID_OPERATION = 'INVALID_OPERATION'
    INSUFFICIENT_BALANCE = 'INSUFFICIENT_BALANCE'
    CAPACITY_EXCEEDED = 'CAPACITY_EXCEEDED'
    ALREADY_EXISTS = 'ALREADY_EXISTS'
    ALREADY_BOOKED = 'ALREADY_BOOKED'
    BOOKING_FULL = 'BOOKING_FULL'
    CLOSED_DAY = 'CLOSED_DAY'

    # サーバーエラー
    INTERNAL_ERROR = 'INTERNAL_ERROR'
    SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE'


# =============================================================================
# カスタム例外クラス（DRF APIException ベース）
# =============================================================================
class OZAException(APIException):
    """OZAシステム基底例外（DRF APIExceptionを継承）"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'エラーが発生しました'
    default_code = 'error'

    def __init__(self, detail=None, code=None, status_code=None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code
        if status_code is not None:
            self.status_code = status_code

        # DRF APIExceptionの形式に合わせる
        super().__init__(detail=detail, code=code)
        self.error_code = code  # 独自のエラーコードを保持


class ValidationException(OZAException):
    """バリデーションエラー"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = '入力内容に問題があります'
    default_code = ErrorCode.VALIDATION_ERROR

    def __init__(self, detail=None, field_errors=None, code=None):
        super().__init__(detail=detail, code=code)
        self.field_errors = field_errors or {}


class NotFoundError(OZAException):
    """リソースが見つからない"""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = '指定されたリソースが見つかりません'
    default_code = ErrorCode.RESOURCE_NOT_FOUND


class TenantNotFoundError(NotFoundError):
    """テナントが見つからない"""
    default_detail = 'テナントが見つかりません'
    default_code = ErrorCode.TENANT_NOT_FOUND


class StudentNotFoundError(NotFoundError):
    """生徒が見つからない"""
    default_detail = '生徒が見つかりません'
    default_code = ErrorCode.STUDENT_NOT_FOUND


class GuardianNotFoundError(NotFoundError):
    """保護者が見つからない"""
    default_detail = '保護者が見つかりません'
    default_code = ErrorCode.GUARDIAN_NOT_FOUND


class SchoolNotFoundError(NotFoundError):
    """校舎が見つからない"""
    default_detail = '校舎が見つかりません'
    default_code = ErrorCode.SCHOOL_NOT_FOUND


class UnauthorizedError(OZAException):
    """認証エラー"""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = '認証が必要です'
    default_code = ErrorCode.UNAUTHORIZED


class ForbiddenError(OZAException):
    """アクセス権限エラー"""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'アクセス権限がありません'
    default_code = ErrorCode.FORBIDDEN


class TenantAccessDeniedError(ForbiddenError):
    """テナントへのアクセス権限がない"""
    default_detail = 'このテナントへのアクセス権限がありません'
    default_code = 'TENANT_ACCESS_DENIED'


class DuplicateResourceError(OZAException):
    """リソースが重複"""
    status_code = status.HTTP_409_CONFLICT
    default_detail = '既に存在するリソースです'
    default_code = ErrorCode.ALREADY_EXISTS


class InvalidOperationError(OZAException):
    """無効な操作"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'この操作は許可されていません'
    default_code = ErrorCode.INVALID_OPERATION


class BusinessRuleViolationError(OZAException):
    """ビジネスルール違反"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'ビジネスルールに違反しています'
    default_code = ErrorCode.BUSINESS_RULE_VIOLATION


class BookingFullError(BusinessRuleViolationError):
    """予約が満席"""
    default_detail = 'この日時は満席です'
    default_code = ErrorCode.BOOKING_FULL


class AlreadyBookedError(BusinessRuleViolationError):
    """既に予約済み"""
    default_detail = 'この日時は既に予約済みです'
    default_code = ErrorCode.ALREADY_BOOKED


class ClosedDayError(BusinessRuleViolationError):
    """休講日"""
    default_detail = '休講日のため予約できません'
    default_code = ErrorCode.CLOSED_DAY


# 後方互換性のためのエイリアス
ResourceNotFoundError = NotFoundError


# =============================================================================
# カスタム例外ハンドラー
# =============================================================================
def custom_exception_handler(exc, context):
    """
    カスタム例外ハンドラー

    すべての例外を統一フォーマットに変換:
    {
        "success": false,
        "error": {
            "code": "ERROR_CODE",
            "message": "メッセージ",
            "details": {...}
        }
    }
    """
    # DRF標準の例外処理を実行
    response = exception_handler(exc, context)

    if response is not None:
        # OZAExceptionの場合はerror_codeを使用
        if isinstance(exc, OZAException):
            error_code = exc.error_code
            message = str(exc.detail) if exc.detail else exc.default_detail
            details = getattr(exc, 'field_errors', None)
        else:
            error_code = _get_error_code_from_status(response.status_code)
            message = _get_error_message(exc)
            details = response.data if hasattr(response, 'data') else None

        custom_response_data = {
            'success': False,
            'error': {
                'code': error_code,
                'message': message,
                'details': details,
            }
        }
        response.data = custom_response_data
        return response

    # DRFが処理しなかった例外
    if isinstance(exc, Http404):
        data = {
            'success': False,
            'error': {
                'code': ErrorCode.NOT_FOUND,
                'message': 'リソースが見つかりません',
                'details': None,
            }
        }
        return Response(data, status=status.HTTP_404_NOT_FOUND)

    elif isinstance(exc, PermissionDenied):
        data = {
            'success': False,
            'error': {
                'code': ErrorCode.FORBIDDEN,
                'message': 'アクセス権限がありません',
                'details': None,
            }
        }
        return Response(data, status=status.HTTP_403_FORBIDDEN)

    elif isinstance(exc, ValidationError):
        data = {
            'success': False,
            'error': {
                'code': ErrorCode.VALIDATION_ERROR,
                'message': 'バリデーションエラー',
                'details': exc.messages if hasattr(exc, 'messages') else str(exc),
            }
        }
        return Response(data, status=status.HTTP_400_BAD_REQUEST)

    return response


def _get_error_code_from_status(status_code):
    """HTTPステータスコードからエラーコードを取得"""
    status_to_code = {
        400: ErrorCode.VALIDATION_ERROR,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        409: ErrorCode.ALREADY_EXISTS,
        500: ErrorCode.INTERNAL_ERROR,
    }
    return status_to_code.get(status_code, ErrorCode.INTERNAL_ERROR)


def _get_error_message(exc):
    """例外からエラーメッセージを取得"""
    if hasattr(exc, 'detail'):
        if isinstance(exc.detail, str):
            return exc.detail
        elif isinstance(exc.detail, dict):
            return '入力内容に問題があります'
        elif isinstance(exc.detail, list):
            return exc.detail[0] if exc.detail else 'エラーが発生しました'
    return str(exc) if str(exc) else 'エラーが発生しました'


# 後方互換性のため旧関数名も残す
get_error_message = _get_error_message
