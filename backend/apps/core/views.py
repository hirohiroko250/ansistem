"""
Core Views
"""
import os
import uuid
from django.http import JsonResponse
from django.db import connection
from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser


ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.webm', '.mov', '.avi']
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_file(request):
    """
    ファイルアップロードエンドポイント

    POST /api/core/upload/
    - file: アップロードするファイル
    - type: 'image' or 'video' (optional, default: auto-detect)

    Returns:
    {
        "url": "/media/uploads/2024/01/uuid-filename.jpg",
        "filename": "original-filename.jpg",
        "size": 12345,
        "type": "image"
    }
    """
    if 'file' not in request.FILES:
        return Response(
            {'error': 'ファイルが選択されていません'},
            status=status.HTTP_400_BAD_REQUEST
        )

    uploaded_file = request.FILES['file']
    file_type = request.data.get('type', 'auto')

    # ファイルサイズチェック
    if uploaded_file.size > MAX_FILE_SIZE:
        return Response(
            {'error': f'ファイルサイズは{MAX_FILE_SIZE // (1024*1024)}MB以下にしてください'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 拡張子チェック
    _, ext = os.path.splitext(uploaded_file.name)
    ext = ext.lower()

    if file_type == 'image' or (file_type == 'auto' and ext in ALLOWED_IMAGE_EXTENSIONS):
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            return Response(
                {'error': f'画像は {", ".join(ALLOWED_IMAGE_EXTENSIONS)} 形式のみ対応しています'},
                status=status.HTTP_400_BAD_REQUEST
            )
        detected_type = 'image'
    elif file_type == 'video' or (file_type == 'auto' and ext in ALLOWED_VIDEO_EXTENSIONS):
        if ext not in ALLOWED_VIDEO_EXTENSIONS:
            return Response(
                {'error': f'動画は {", ".join(ALLOWED_VIDEO_EXTENSIONS)} 形式のみ対応しています'},
                status=status.HTTP_400_BAD_REQUEST
            )
        detected_type = 'video'
    else:
        return Response(
            {'error': '対応していないファイル形式です'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ユニークなファイル名を生成
    from datetime import datetime
    date_path = datetime.now().strftime('%Y/%m')
    unique_id = uuid.uuid4().hex[:8]
    safe_filename = f"{unique_id}-{uploaded_file.name}"
    file_path = f"uploads/{date_path}/{safe_filename}"

    # ファイルを保存
    try:
        saved_path = default_storage.save(file_path, uploaded_file)
        file_url = f"{settings.MEDIA_URL}{saved_path}"

        return Response({
            'url': file_url,
            'filename': uploaded_file.name,
            'size': uploaded_file.size,
            'type': detected_type,
        })
    except Exception as e:
        return Response(
            {'error': f'ファイルの保存に失敗しました: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_multiple_files(request):
    """
    複数ファイルアップロードエンドポイント

    POST /api/core/upload/multiple/
    - files: アップロードするファイル（複数可）

    Returns:
    {
        "files": [
            {"url": "...", "filename": "...", "size": 123, "type": "image"},
            ...
        ]
    }
    """
    files = request.FILES.getlist('files')

    if not files:
        return Response(
            {'error': 'ファイルが選択されていません'},
            status=status.HTTP_400_BAD_REQUEST
        )

    results = []
    errors = []

    for uploaded_file in files:
        # ファイルサイズチェック
        if uploaded_file.size > MAX_FILE_SIZE:
            errors.append(f'{uploaded_file.name}: ファイルサイズが大きすぎます')
            continue

        # 拡張子チェック
        _, ext = os.path.splitext(uploaded_file.name)
        ext = ext.lower()

        if ext in ALLOWED_IMAGE_EXTENSIONS:
            detected_type = 'image'
        elif ext in ALLOWED_VIDEO_EXTENSIONS:
            detected_type = 'video'
        else:
            errors.append(f'{uploaded_file.name}: 対応していないファイル形式です')
            continue

        # ファイル保存
        from datetime import datetime
        date_path = datetime.now().strftime('%Y/%m')
        unique_id = uuid.uuid4().hex[:8]
        safe_filename = f"{unique_id}-{uploaded_file.name}"
        file_path = f"uploads/{date_path}/{safe_filename}"

        try:
            saved_path = default_storage.save(file_path, uploaded_file)
            file_url = f"{settings.MEDIA_URL}{saved_path}"

            results.append({
                'url': file_url,
                'filename': uploaded_file.name,
                'size': uploaded_file.size,
                'type': detected_type,
            })
        except Exception as e:
            errors.append(f'{uploaded_file.name}: 保存に失敗しました')

    return Response({
        'files': results,
        'errors': errors if errors else None,
    })


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
