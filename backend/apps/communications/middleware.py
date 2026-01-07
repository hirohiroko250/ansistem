"""
WebSocket Authentication Middleware
JWT認証ミドルウェア（WebSocket用）
"""
import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user_from_token(token_string):
    """
    JWTトークンからユーザーを取得
    """
    from apps.users.models import User

    try:
        # トークンを検証
        access_token = AccessToken(token_string)
        user_id = access_token.get('user_id')

        if user_id:
            user = User.objects.get(id=user_id)
            return user
    except TokenError as e:
        logger.warning(f"Token error: {e}")
    except InvalidToken as e:
        logger.warning(f"Invalid token: {e}")
    except User.DoesNotExist:
        logger.warning(f"User not found for token")
    except Exception as e:
        logger.error(f"Error getting user from token: {e}")

    return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    WebSocket接続用JWT認証ミドルウェア

    トークンの取得方法:
    1. クエリパラメータ: ws://host/ws/chat/xxx/?token=xxx
    2. サブプロトコル: Sec-WebSocket-Protocol ヘッダー
    """

    async def __call__(self, scope, receive, send):
        # クエリパラメータからトークンを取得
        query_string = scope.get('query_string', b'').decode('utf-8')
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]

        # サブプロトコルからもトークンを試行
        if not token:
            subprotocols = scope.get('subprotocols', [])
            for protocol in subprotocols:
                if protocol.startswith('bearer.'):
                    token = protocol[7:]  # 'bearer.'を除去
                    break

        if token:
            scope['user'] = await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)


class GuardianJWTAuthMiddleware(BaseMiddleware):
    """
    保護者用WebSocket認証ミドルウェア

    保護者は User モデルではなく Guardian モデルで管理されている場合のミドルウェア
    """

    async def __call__(self, scope, receive, send):
        from apps.students.models import Guardian

        query_string = scope.get('query_string', b'').decode('utf-8')
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]

        if token:
            user = await get_user_from_token(token)
            scope['user'] = user

            # 保護者プロファイルも取得
            if user.is_authenticated:
                guardian = await self.get_guardian_profile(user)
                scope['guardian'] = guardian
        else:
            scope['user'] = AnonymousUser()
            scope['guardian'] = None

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_guardian_profile(self, user):
        """ユーザーの保護者プロファイルを取得"""
        try:
            return user.guardian_profile
        except Exception:
            return None
