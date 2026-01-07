"""
WebSocket Notification Service
REST APIからWebSocket通知を送信するサービス
"""
import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def notify_new_message(channel_id, message):
    """
    新着メッセージをWebSocketで通知

    Args:
        channel_id: チャンネルID
        message: Messageモデルインスタンス
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.warning("Channel layer is not configured")
        return

    room_group_name = f'chat_{channel_id}'

    # 送信者名を取得
    sender_name = 'Unknown'
    sender_type = 'staff'
    sender_id = None

    if message.is_bot_message:
        sender_name = 'アシスタント'
        sender_type = 'bot'
    elif message.sender:
        sender_name = message.sender.full_name or message.sender.email
        sender_type = 'staff'
        sender_id = str(message.sender.id)
    elif message.sender_guardian:
        sender_name = message.sender_guardian.full_name
        sender_type = 'guardian'
        sender_id = str(message.sender_guardian.id)

    message_data = {
        'id': str(message.id),
        'content': message.content,
        'sender_id': sender_id,
        'sender_name': sender_name,
        'sender_type': sender_type,
        'created_at': message.created_at.isoformat(),
        'reply_to': str(message.reply_to_id) if message.reply_to_id else None,
        'message_type': message.message_type,
        'attachment_url': message.attachment_url,
        'attachment_name': message.attachment_name,
    }

    try:
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'chat_message',
                'message': message_data,
            }
        )
        logger.debug(f"WebSocket notification sent to {room_group_name}")
    except Exception as e:
        logger.error(f"Failed to send WebSocket notification: {e}")


def notify_message_edited(channel_id, message):
    """
    メッセージ編集をWebSocketで通知
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    room_group_name = f'chat_{channel_id}'

    try:
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'message_edited',
                'message_id': str(message.id),
                'content': message.content,
                'edited_at': message.edited_at.isoformat() if message.edited_at else None,
            }
        )
    except Exception as e:
        logger.error(f"Failed to send message edit notification: {e}")


def notify_message_deleted(channel_id, message_id):
    """
    メッセージ削除をWebSocketで通知
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    room_group_name = f'chat_{channel_id}'

    try:
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'message_deleted',
                'message_id': str(message_id),
            }
        )
    except Exception as e:
        logger.error(f"Failed to send message delete notification: {e}")


def notify_channel_members_new_message(channel, message):
    """
    チャンネルメンバー全員に新着メッセージを個別通知（通知用WebSocket）
    サイドバーの未読バッジ更新等に使用
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    # チャンネルメンバーを取得
    members = channel.members.select_related('user').filter(user__isnull=False)

    sender_id = None
    if message.sender:
        sender_id = message.sender.id

    for member in members:
        # 送信者には通知しない
        if member.user_id == sender_id:
            continue

        user_group_name = f'notifications_{member.user_id}'

        try:
            async_to_sync(channel_layer.group_send)(
                user_group_name,
                {
                    'type': 'new_chat_message',
                    'channel_id': str(channel.id),
                    'channel_name': channel.name,
                    'message': {
                        'id': str(message.id),
                        'content': message.content[:100],  # プレビュー用に短縮
                        'sender_name': message.sender_name,
                        'created_at': message.created_at.isoformat(),
                    }
                }
            )
        except Exception as e:
            logger.error(f"Failed to notify user {member.user_id}: {e}")


def notify_user(user_id, notification_type, data):
    """
    特定ユーザーに通知を送信

    Args:
        user_id: ユーザーID
        notification_type: 通知タイプ（'system_notification' など）
        data: 通知データ
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    user_group_name = f'notifications_{user_id}'

    try:
        async_to_sync(channel_layer.group_send)(
            user_group_name,
            {
                'type': notification_type,
                **data
            }
        )
    except Exception as e:
        logger.error(f"Failed to notify user {user_id}: {e}")


def notify_thread_reply(channel_id, parent_message, reply_message):
    """
    スレッド返信をWebSocketで通知

    Args:
        channel_id: チャンネルID
        parent_message: 親メッセージ（返信先）
        reply_message: 返信メッセージ
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    room_group_name = f'chat_{channel_id}'

    # 送信者情報を取得
    sender_name = 'Unknown'
    sender_id = None

    if reply_message.is_bot_message:
        sender_name = 'アシスタント'
    elif reply_message.sender:
        sender_name = reply_message.sender.full_name or reply_message.sender.email
        sender_id = str(reply_message.sender.id)
    elif reply_message.sender_guardian:
        sender_name = reply_message.sender_guardian.full_name
        sender_id = str(reply_message.sender_guardian.id)

    try:
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'thread_reply',
                'parent_message_id': str(parent_message.id),
                'reply': {
                    'id': str(reply_message.id),
                    'content': reply_message.content,
                    'sender_id': sender_id,
                    'sender_name': sender_name,
                    'created_at': reply_message.created_at.isoformat(),
                },
                'reply_count': parent_message.replies.filter(is_deleted=False).count(),
            }
        )
    except Exception as e:
        logger.error(f"Failed to send thread reply notification: {e}")


def notify_reaction_added(channel_id, message_id, emoji, user_id, user_name):
    """
    リアクション追加をWebSocketで通知

    Args:
        channel_id: チャンネルID
        message_id: メッセージID
        emoji: 絵文字
        user_id: ユーザーID
        user_name: ユーザー名
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    room_group_name = f'chat_{channel_id}'

    try:
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'reaction_added',
                'message_id': message_id,
                'emoji': emoji,
                'user_id': user_id,
                'user_name': user_name,
            }
        )
    except Exception as e:
        logger.error(f"Failed to send reaction added notification: {e}")


def notify_reaction_removed(channel_id, message_id, emoji, user_id):
    """
    リアクション削除をWebSocketで通知

    Args:
        channel_id: チャンネルID
        message_id: メッセージID
        emoji: 絵文字
        user_id: ユーザーID
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    room_group_name = f'chat_{channel_id}'

    try:
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'reaction_removed',
                'message_id': message_id,
                'emoji': emoji,
                'user_id': user_id,
            }
        )
    except Exception as e:
        logger.error(f"Failed to send reaction removed notification: {e}")
