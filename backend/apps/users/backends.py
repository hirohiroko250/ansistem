"""
カスタム認証バックエンド
電話番号またはメールアドレスでログイン可能
"""
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .models import User


class PhoneOrEmailBackend(ModelBackend):
    """電話番号またはメールアドレスで認証するバックエンド"""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        # 電話番号の正規化（ハイフンや空白を除去）
        normalized_phone = ''.join(c for c in username if c.isdigit())

        try:
            # メールアドレスまたは電話番号でユーザーを検索
            user = User.objects.get(
                Q(email__iexact=username) |
                Q(phone=username) |
                Q(phone=normalized_phone),
                is_active=True,
                deleted_at__isnull=True
            )
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            # 複数ユーザーが見つかった場合は最初のものを使用
            user = User.objects.filter(
                Q(email__iexact=username) |
                Q(phone=username) |
                Q(phone=normalized_phone),
                is_active=True,
                deleted_at__isnull=True
            ).first()
            if user is None:
                return None

        if user.check_password(password):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id, is_active=True, deleted_at__isnull=True)
        except User.DoesNotExist:
            return None
