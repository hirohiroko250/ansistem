"""
Logging Configuration - 構造化ログとリクエストID追跡
"""
import json
import logging
import threading
import time
import uuid
from datetime import datetime


# スレッドローカルストレージでリクエストIDを管理
_request_local = threading.local()


def get_request_id():
    """現在のリクエストIDを取得"""
    return getattr(_request_local, 'request_id', None)


def set_request_id(request_id=None):
    """リクエストIDを設定（Noneの場合は自動生成）"""
    _request_local.request_id = request_id or str(uuid.uuid4())[:8]
    return _request_local.request_id


def clear_request_id():
    """リクエストIDをクリア"""
    _request_local.request_id = None


class RequestIDMiddleware:
    """
    リクエストIDミドルウェア

    各リクエストにユニークなIDを付与し、ログ追跡を容易にする
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # リクエストヘッダーからIDを取得、なければ生成
        request_id = request.headers.get('X-Request-ID')
        set_request_id(request_id)

        # リクエストにIDを付与
        request.request_id = get_request_id()

        # レスポンスを取得
        response = self.get_response(request)

        # レスポンスヘッダーにIDを付与
        response['X-Request-ID'] = request.request_id

        # クリーンアップ
        clear_request_id()

        return response


class JSONFormatter(logging.Formatter):
    """
    JSON形式のログフォーマッター

    ログ集約システム（ELK, CloudWatch等）での解析を容易にする
    """

    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # リクエストIDがあれば追加
        request_id = get_request_id()
        if request_id:
            log_data['request_id'] = request_id

        # 例外情報があれば追加
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # 追加の属性があれば追加
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data

        return json.dumps(log_data, ensure_ascii=False)


class RequestLoggingMiddleware:
    """
    リクエスト/レスポンスログミドルウェア

    APIリクエストの開始・終了をログ出力する
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('apps.api')

    def __call__(self, request):
        # 開始時刻を記録
        start_time = time.time()

        # ログ対象外のパスをスキップ
        skip_paths = ['/health/', '/static/', '/media/', '/favicon.ico']
        should_log = not any(request.path.startswith(p) for p in skip_paths)

        if should_log:
            self.logger.info(
                f"Request: {request.method} {request.path}",
                extra={'extra_data': {
                    'method': request.method,
                    'path': request.path,
                    'user_id': str(request.user.id) if request.user.is_authenticated else None,
                    'tenant_id': getattr(request, 'tenant_id', None),
                }}
            )

        # レスポンスを取得
        response = self.get_response(request)

        # 処理時間を計算
        duration_ms = (time.time() - start_time) * 1000

        if should_log:
            log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
            self.logger.log(
                log_level,
                f"Response: {response.status_code} ({duration_ms:.0f}ms)",
                extra={'extra_data': {
                    'status_code': response.status_code,
                    'duration_ms': round(duration_ms, 2),
                    'method': request.method,
                    'path': request.path,
                }}
            )

        return response


def get_logger(name):
    """
    アプリケーション用ロガーを取得

    Usage:
        from apps.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info('Something happened', extra={'extra_data': {'key': 'value'}})
    """
    return logging.getLogger(name)
