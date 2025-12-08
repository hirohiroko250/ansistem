"""
Utility Functions
"""
import uuid
from datetime import datetime, date
from typing import Optional


def generate_code(prefix: str, sequence: int, width: int = 3) -> str:
    """
    コード生成（例: STU2024001）

    Args:
        prefix: プレフィックス文字列
        sequence: 連番
        width: 連番の桁数

    Returns:
        生成されたコード
    """
    year = datetime.now().year
    return f"{prefix}{year}{str(sequence).zfill(width)}"


def parse_uuid(value: str) -> Optional[uuid.UUID]:
    """
    文字列をUUIDに変換（失敗時はNone）

    Args:
        value: UUID文字列

    Returns:
        UUID or None
    """
    try:
        return uuid.UUID(value)
    except (ValueError, TypeError):
        return None


def get_year_month(dt: Optional[date] = None) -> str:
    """
    日付からYYYY-MM形式の文字列を取得

    Args:
        dt: 日付（デフォルトは今日）

    Returns:
        YYYY-MM形式の文字列
    """
    if dt is None:
        dt = date.today()
    return dt.strftime('%Y-%m')


def calculate_age(birth_date: date) -> int:
    """
    生年月日から年齢を計算

    Args:
        birth_date: 生年月日

    Returns:
        年齢
    """
    today = date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def format_phone_number(phone: str) -> str:
    """
    電話番号をフォーマット（ハイフン除去）

    Args:
        phone: 電話番号

    Returns:
        フォーマット済み電話番号
    """
    if not phone:
        return phone
    return phone.replace('-', '').replace('−', '').replace(' ', '')


def mask_email(email: str) -> str:
    """
    メールアドレスをマスク

    Args:
        email: メールアドレス

    Returns:
        マスク済みメールアドレス
    """
    if not email or '@' not in email:
        return email

    local, domain = email.split('@')
    if len(local) <= 2:
        masked_local = '*' * len(local)
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]

    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    """
    電話番号をマスク

    Args:
        phone: 電話番号

    Returns:
        マスク済み電話番号
    """
    if not phone:
        return phone

    clean_phone = format_phone_number(phone)
    if len(clean_phone) <= 4:
        return '*' * len(clean_phone)

    return clean_phone[:3] + '*' * (len(clean_phone) - 7) + clean_phone[-4:]
