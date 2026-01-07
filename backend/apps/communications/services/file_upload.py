"""
File Upload Service - ファイルアップロード処理
チャットメッセージへのファイル添付機能を提供
"""
import os
import uuid
import logging
from typing import Tuple, Optional
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)

# 許可するファイル拡張子
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS

# ファイルサイズ制限（10MB）
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

# MIMEタイプマッピング
MIME_TYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.ppt': 'application/vnd.ms-powerpoint',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.txt': 'text/plain',
    '.csv': 'text/csv',
}


class FileUploadError(Exception):
    """ファイルアップロードエラー"""
    pass


def validate_file(file: UploadedFile) -> Tuple[bool, Optional[str]]:
    """
    ファイルのバリデーション

    Args:
        file: アップロードされたファイル

    Returns:
        Tuple[bool, Optional[str]]: (有効かどうか, エラーメッセージ)
    """
    if not file:
        return False, 'ファイルが選択されていません'

    # ファイル名チェック
    if not file.name:
        return False, 'ファイル名が不正です'

    # 拡張子チェック
    _, ext = os.path.splitext(file.name.lower())
    if ext not in ALLOWED_EXTENSIONS:
        allowed_list = ', '.join(sorted(ALLOWED_EXTENSIONS))
        return False, f'許可されていないファイル形式です。対応形式: {allowed_list}'

    # ファイルサイズチェック
    if file.size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        return False, f'ファイルサイズが大きすぎます。最大{max_mb:.0f}MBまでです'

    # MIMEタイプチェック（簡易）
    content_type = file.content_type or ''
    expected_mime = MIME_TYPES.get(ext, '')

    # 一部のブラウザは正しいMIMEタイプを送らないことがあるので、
    # 画像の場合のみ厳密にチェック
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        if not content_type.startswith('image/'):
            return False, f'ファイルの内容が拡張子と一致しません'

    return True, None


def get_file_type(filename: str) -> str:
    """
    ファイル名からメッセージタイプを判定

    Args:
        filename: ファイル名

    Returns:
        str: 'IMAGE' または 'FILE'
    """
    _, ext = os.path.splitext(filename.lower())
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        return 'IMAGE'
    return 'FILE'


def generate_unique_filename(original_filename: str, channel_id: str) -> str:
    """
    ユニークなファイル名を生成

    Args:
        original_filename: 元のファイル名
        channel_id: チャンネルID

    Returns:
        str: ユニークなファイルパス
    """
    _, ext = os.path.splitext(original_filename)
    unique_id = uuid.uuid4().hex[:12]
    safe_channel_id = str(channel_id)[:8]  # チャンネルIDの一部を使用
    new_filename = f"{unique_id}{ext}"

    # パス: chat_attachments/{channel_id_prefix}/{filename}
    return f"chat_attachments/{safe_channel_id}/{new_filename}"


def save_uploaded_file(file: UploadedFile, channel_id: str) -> Tuple[str, str]:
    """
    ファイルをストレージに保存

    Args:
        file: アップロードされたファイル
        channel_id: チャンネルID

    Returns:
        Tuple[str, str]: (ファイルURL, 元のファイル名)

    Raises:
        FileUploadError: アップロードに失敗した場合
    """
    # バリデーション
    is_valid, error_message = validate_file(file)
    if not is_valid:
        raise FileUploadError(error_message)

    try:
        # ユニークなファイル名を生成
        file_path = generate_unique_filename(file.name, channel_id)

        # ファイルを保存
        saved_path = default_storage.save(file_path, file)

        # URLを生成
        file_url = default_storage.url(saved_path)

        # 相対パスの場合は絶対パスに変換
        if not file_url.startswith('http'):
            # MEDIA_URLを使用してフルURLを構築
            file_url = f"{settings.MEDIA_URL}{saved_path}"

        logger.info(f"File uploaded successfully: {saved_path}")

        return file_url, file.name

    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise FileUploadError(f'ファイルの保存に失敗しました: {str(e)}')


def delete_file(file_url: str) -> bool:
    """
    ファイルを削除

    Args:
        file_url: ファイルURL

    Returns:
        bool: 削除成功かどうか
    """
    try:
        # URLからパスを抽出
        if file_url.startswith(settings.MEDIA_URL):
            file_path = file_url[len(settings.MEDIA_URL):]
        else:
            # フルURLの場合
            from urllib.parse import urlparse
            parsed = urlparse(file_url)
            file_path = parsed.path.lstrip('/')
            if file_path.startswith('media/'):
                file_path = file_path[6:]  # 'media/' を除去

        if default_storage.exists(file_path):
            default_storage.delete(file_path)
            logger.info(f"File deleted: {file_path}")
            return True
        else:
            logger.warning(f"File not found for deletion: {file_path}")
            return False

    except Exception as e:
        logger.error(f"Failed to delete file: {e}")
        return False


def get_file_info(file: UploadedFile) -> dict:
    """
    ファイル情報を取得

    Args:
        file: アップロードされたファイル

    Returns:
        dict: ファイル情報
    """
    _, ext = os.path.splitext(file.name.lower())

    return {
        'name': file.name,
        'size': file.size,
        'size_formatted': format_file_size(file.size),
        'extension': ext,
        'content_type': file.content_type,
        'is_image': ext in ALLOWED_IMAGE_EXTENSIONS,
        'message_type': get_file_type(file.name),
    }


def format_file_size(size_bytes: int) -> str:
    """
    ファイルサイズを人間が読みやすい形式にフォーマット

    Args:
        size_bytes: バイト単位のサイズ

    Returns:
        str: フォーマットされたサイズ文字列
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
