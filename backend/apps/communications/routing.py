"""
WebSocket routing for communications app
チャット用WebSocketルーティング
"""
from django.urls import path, re_path
from . import consumers

websocket_urlpatterns = [
    # チャンネル別WebSocket
    re_path(r'ws/chat/(?P<channel_id>[0-9a-f-]+)/$', consumers.ChatConsumer.as_asgi()),
    # 全体通知用WebSocket（ユーザー単位）
    path('ws/notifications/', consumers.NotificationConsumer.as_asgi()),
]
