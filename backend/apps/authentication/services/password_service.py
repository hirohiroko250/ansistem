"""
Password Service - パスワード関連サービス
"""
import secrets
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class PasswordResetService:
    """パスワードリセットサービス"""

    TOKEN_TIMEOUT = 3600  # 1時間
    CACHE_PREFIX = 'password_reset:'

    def __init__(self, user=None):
        self.user = user

    def generate_reset_token(self) -> str:
        """リセットトークンを生成してキャッシュに保存

        Returns:
            生成されたトークン
        """
        if not self.user:
            raise ValueError('ユーザーが設定されていません')

        token = secrets.token_urlsafe(32)
        cache_key = f'{self.CACHE_PREFIX}{token}'
        cache.set(cache_key, str(self.user.id), timeout=self.TOKEN_TIMEOUT)

        logger.info(f"Password reset token generated for user {self.user.id}")

        return token

    @classmethod
    def validate_token(cls, token: str):
        """トークンを検証してユーザーを返す

        Args:
            token: リセットトークン

        Returns:
            User オブジェクト、無効な場合は None
        """
        cache_key = f'{cls.CACHE_PREFIX}{token}'
        user_id = cache.get(cache_key)

        if not user_id:
            return None

        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @classmethod
    def invalidate_token(cls, token: str):
        """トークンを無効化"""
        cache_key = f'{cls.CACHE_PREFIX}{token}'
        cache.delete(cache_key)

    def reset_password(self, token: str, new_password: str) -> bool:
        """パスワードをリセット

        Args:
            token: リセットトークン
            new_password: 新しいパスワード

        Returns:
            成功した場合 True

        Raises:
            ValueError: トークンが無効または期限切れの場合
        """
        user = self.validate_token(token)

        if not user:
            raise ValueError('リセットトークンが無効または期限切れです')

        user.set_password(new_password)
        user.password_changed_at = timezone.now()
        user.save(update_fields=['password', 'password_changed_at'])

        # トークン無効化
        self.invalidate_token(token)

        logger.info(f"Password reset completed for user {user.id}")

        return True

    @staticmethod
    def change_password(user, current_password: str, new_password: str) -> bool:
        """パスワードを変更（現在のパスワード確認付き）

        Args:
            user: ユーザーオブジェクト
            current_password: 現在のパスワード
            new_password: 新しいパスワード

        Returns:
            成功した場合 True

        Raises:
            ValueError: 現在のパスワードが不正な場合
        """
        if not user.check_password(current_password):
            raise ValueError('現在のパスワードが正しくありません')

        user.set_password(new_password)
        user.password_changed_at = timezone.now()
        user.must_change_password = False
        user.save(update_fields=['password', 'password_changed_at', 'must_change_password'])

        logger.info(f"Password changed for user {user.id}")

        return True
