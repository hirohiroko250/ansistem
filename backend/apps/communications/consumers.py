"""
WebSocket Consumers for real-time chat
リアルタイムチャット用Consumer
"""
import json
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from asgiref.sync import sync_to_async

from .models import Channel, ChannelMember, Message, MessageRead

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    チャットチャンネル用WebSocket Consumer
    - チャンネルへの接続・切断
    - メッセージの送受信
    - 既読処理
    - タイピング通知
    """

    async def connect(self):
        """WebSocket接続時の処理"""
        self.channel_id = self.scope['url_route']['kwargs']['channel_id']
        self.room_group_name = f'chat_{self.channel_id}'
        self.user = self.scope.get('user')

        # 認証チェック
        if not self.user or not self.user.is_authenticated:
            logger.warning(f"Unauthorized WebSocket connection attempt to channel {self.channel_id}")
            await self.close(code=4001)
            return

        # チャンネルメンバーシップ確認
        is_member = await self.check_channel_membership()
        if not is_member:
            logger.warning(f"User {self.user.id} is not a member of channel {self.channel_id}")
            await self.close(code=4003)
            return

        # グループに参加
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # 接続通知
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_join',
                'user_id': str(self.user.id),
                'user_name': self.user.full_name or self.user.email,
            }
        )

        logger.info(f"User {self.user.id} connected to channel {self.channel_id}")

    async def disconnect(self, close_code):
        """WebSocket切断時の処理"""
        if hasattr(self, 'room_group_name'):
            # 離脱通知（認証済みユーザーのみ）
            if hasattr(self, 'user') and self.user and self.user.is_authenticated:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'user_leave',
                        'user_id': str(self.user.id),
                        'user_name': getattr(self.user, 'full_name', None) or self.user.email,
                    }
                )

            # グループから離脱
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

        logger.info(f"User disconnected from channel {getattr(self, 'channel_id', 'unknown')}")

    async def receive_json(self, content):
        """クライアントからのメッセージ受信"""
        message_type = content.get('type', 'chat_message')

        if message_type == 'chat_message':
            await self.handle_chat_message(content)
        elif message_type == 'typing':
            await self.handle_typing(content)
        elif message_type == 'mark_read':
            await self.handle_mark_read(content)
        elif message_type == 'ping':
            await self.send_json({'type': 'pong'})
        else:
            logger.warning(f"Unknown message type: {message_type}")

    async def handle_chat_message(self, content):
        """チャットメッセージの処理"""
        message_content = content.get('content', '').strip()
        reply_to_id = content.get('reply_to')

        if not message_content:
            return

        # メッセージをDBに保存
        message = await self.save_message(message_content, reply_to_id)

        if message:
            # グループ全体にブロードキャスト
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'id': str(message.id),
                        'content': message.content,
                        'sender_id': str(self.user.id),
                        'sender_name': self.user.full_name or self.user.email,
                        'sender_type': 'staff',
                        'created_at': message.created_at.isoformat(),
                        'reply_to': str(message.reply_to_id) if message.reply_to_id else None,
                    }
                }
            )

    async def handle_typing(self, content):
        """タイピング通知の処理"""
        is_typing = content.get('is_typing', False)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_notification',
                'user_id': str(self.user.id),
                'user_name': self.user.full_name or self.user.email,
                'is_typing': is_typing,
            }
        )

    async def handle_mark_read(self, content):
        """既読処理"""
        message_id = content.get('message_id')
        if message_id:
            await self.mark_message_as_read(message_id)

    # ========================================
    # Group message handlers
    # ========================================

    async def chat_message(self, event):
        """チャットメッセージをクライアントに送信"""
        await self.send_json({
            'type': 'chat_message',
            'message': event['message'],
        })

    async def typing_notification(self, event):
        """タイピング通知をクライアントに送信"""
        # 自分自身には送らない
        if event['user_id'] != str(self.user.id):
            await self.send_json({
                'type': 'typing',
                'user_id': event['user_id'],
                'user_name': event['user_name'],
                'is_typing': event['is_typing'],
            })

    async def user_join(self, event):
        """ユーザー参加通知をクライアントに送信"""
        await self.send_json({
            'type': 'user_join',
            'user_id': event['user_id'],
            'user_name': event['user_name'],
        })

    async def user_leave(self, event):
        """ユーザー離脱通知をクライアントに送信"""
        await self.send_json({
            'type': 'user_leave',
            'user_id': event['user_id'],
            'user_name': event['user_name'],
        })

    async def new_message_notification(self, event):
        """新着メッセージ通知（外部から呼び出し用）"""
        await self.send_json({
            'type': 'new_message',
            'message': event['message'],
        })

    async def message_edited(self, event):
        """メッセージ編集通知をクライアントに送信"""
        await self.send_json({
            'type': 'message_edited',
            'message_id': event['message_id'],
            'content': event['content'],
            'edited_at': event.get('edited_at'),
        })

    async def message_deleted(self, event):
        """メッセージ削除通知をクライアントに送信"""
        await self.send_json({
            'type': 'message_deleted',
            'message_id': event['message_id'],
        })

    async def thread_reply(self, event):
        """スレッド返信通知をクライアントに送信"""
        await self.send_json({
            'type': 'thread_reply',
            'parent_message_id': event['parent_message_id'],
            'reply': event['reply'],
            'reply_count': event['reply_count'],
        })

    async def reaction_added(self, event):
        """リアクション追加通知をクライアントに送信"""
        await self.send_json({
            'type': 'reaction_added',
            'message_id': event['message_id'],
            'emoji': event['emoji'],
            'user_id': event['user_id'],
            'user_name': event['user_name'],
        })

    async def reaction_removed(self, event):
        """リアクション削除通知をクライアントに送信"""
        await self.send_json({
            'type': 'reaction_removed',
            'message_id': event['message_id'],
            'emoji': event['emoji'],
            'user_id': event['user_id'],
        })

    async def mention_notification(self, event):
        """メンション通知をクライアントに送信"""
        await self.send_json({
            'type': 'mention',
            'channel_id': event['channel_id'],
            'channel_name': event['channel_name'],
            'message_id': event['message_id'],
            'sender_name': event['sender_name'],
            'content': event['content'],
        })

    # ========================================
    # Database operations
    # ========================================

    @database_sync_to_async
    def check_channel_membership(self):
        """チャンネルメンバーシップを確認"""
        try:
            return ChannelMember.objects.filter(
                channel_id=self.channel_id,
                user=self.user
            ).exists()
        except Exception as e:
            logger.error(f"Error checking channel membership: {e}")
            return False

    @database_sync_to_async
    def save_message(self, content, reply_to_id=None):
        """メッセージをDBに保存"""
        try:
            channel = Channel.objects.get(id=self.channel_id)
            message = Message.objects.create(
                tenant_id=channel.tenant_id,
                channel=channel,
                sender=self.user,
                content=content,
                reply_to_id=reply_to_id,
                message_type=Message.MessageType.TEXT,
            )
            # チャンネルの更新日時を更新
            channel.updated_at = timezone.now()
            channel.save(update_fields=['updated_at'])
            return message
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return None

    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        """メッセージを既読にする"""
        try:
            MessageRead.objects.get_or_create(
                message_id=message_id,
                user=self.user
            )
            # ChannelMemberの最終既読日時も更新
            ChannelMember.objects.filter(
                channel_id=self.channel_id,
                user=self.user
            ).update(last_read_at=timezone.now())
        except Exception as e:
            logger.error(f"Error marking message as read: {e}")


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    通知用WebSocket Consumer
    - ユーザー単位での通知受信
    - 未読メッセージ通知
    - システム通知
    """

    async def connect(self):
        """WebSocket接続時の処理"""
        self.user = self.scope.get('user')

        # 認証チェック
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.user_group_name = f'notifications_{self.user.id}'

        # ユーザー固有のグループに参加
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"User {self.user.id} connected to notifications")

    async def disconnect(self, close_code):
        """WebSocket切断時の処理"""
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )

    async def receive_json(self, content):
        """クライアントからのメッセージ受信"""
        message_type = content.get('type', '')

        if message_type == 'ping':
            await self.send_json({'type': 'pong'})

    # ========================================
    # Notification handlers
    # ========================================

    async def new_chat_message(self, event):
        """新着チャットメッセージ通知"""
        await self.send_json({
            'type': 'new_chat_message',
            'channel_id': event['channel_id'],
            'channel_name': event['channel_name'],
            'message': event['message'],
        })

    async def channel_update(self, event):
        """チャンネル更新通知"""
        await self.send_json({
            'type': 'channel_update',
            'channel_id': event['channel_id'],
            'action': event['action'],
        })

    async def system_notification(self, event):
        """システム通知"""
        await self.send_json({
            'type': 'system_notification',
            'title': event.get('title', ''),
            'message': event.get('message', ''),
            'level': event.get('level', 'info'),
        })


# ========================================
# Helper functions for sending notifications
# ========================================

async def notify_channel_members(channel_id, message_data, exclude_user_id=None):
    """
    チャンネルメンバー全員に通知を送信
    REST APIから呼び出し可能なヘルパー関数
    """
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    room_group_name = f'chat_{channel_id}'

    await channel_layer.group_send(
        room_group_name,
        {
            'type': 'chat_message',
            'message': message_data,
        }
    )


async def notify_user(user_id, notification_data):
    """
    特定ユーザーに通知を送信
    """
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    user_group_name = f'notifications_{user_id}'

    await channel_layer.group_send(
        user_group_name,
        notification_data
    )
