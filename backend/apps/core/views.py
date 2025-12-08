"""
Core Views
"""
from django.http import JsonResponse
from django.db import connection


def health_check(request):
    """ヘルスチェックエンドポイント"""
    health_status = {
        'status': 'healthy',
        'database': 'unknown',
    }

    # データベース接続チェック
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health_status['database'] = 'connected'
    except Exception as e:
        health_status['database'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'

    status_code = 200 if health_status['status'] == 'healthy' else 503
    return JsonResponse(health_status, status=status_code)
