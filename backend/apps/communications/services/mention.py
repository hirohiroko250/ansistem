"""
Mention Service
メンション機能のパースと通知処理
"""
import re
import logging
from typing import List, Tuple
from django.db import transaction

from apps.communications.models import MessageMention, Notification
from apps.users.models import User

logger = logging.getLogger(__name__)

# メンションパターン: @[user_id] 形式
# フロントエンドから送られてくる形式: @[uuid]
MENTION_PATTERN = re.compile(r'@\[([0-9a-f-]{36})\]')

# 表示用: @名前 形式も検出（フォールバック）
MENTION_DISPLAY_PATTERN = re.compile(r'@(\S+)')


def parse_mentions(content: str) -> List[Tuple[str, int, int]]:
    """
    メッセージ内容からメンションを解析

    Args:
        content: メッセージ内容

    Returns:
        List of (user_id, start_index, end_index)
    """
    mentions = []

    for match in MENTION_PATTERN.finditer(content):
        user_id = match.group(1)
        start = match.start()
        end = match.end()
        mentions.append((user_id, start, end))

    return mentions


def create_mentions_for_message(message, content: str = None) -> List[MessageMention]:
    """
    メッセージに対するメンションレコードを作成

    Args:
        message: Messageモデルインスタンス
        content: メッセージ内容（省略時はmessage.contentを使用）

    Returns:
        作成されたMessageMentionのリスト
    """
    if content is None:
        content = message.content

    parsed_mentions = parse_mentions(content)

    if not parsed_mentions:
        return []

    # ユーザーIDを収集
    user_ids = [m[0] for m in parsed_mentions]

    # 存在するユーザーを取得
    existing_users = {
        str(u.id): u
        for u in User.objects.filter(id__in=user_ids, is_active=True)
    }

    created_mentions = []

    with transaction.atomic():
        for user_id, start, end in parsed_mentions:
            if user_id not in existing_users:
                logger.warning(f"Mention target user not found: {user_id}")
                continue

            mentioned_user = existing_users[user_id]

            # 自分自身へのメンションはスキップ
            if message.sender and message.sender.id == mentioned_user.id:
                continue

            # メンションレコード作成（重複は無視）
            mention, created = MessageMention.objects.get_or_create(
                message=message,
                mentioned_user=mentioned_user,
                defaults={
                    'start_index': start,
                    'end_index': end,
                }
            )

            if created:
                created_mentions.append(mention)
                logger.debug(f"Created mention: {mention}")

    return created_mentions


def create_mention_notifications(message, mentions: List[MessageMention]) -> List[Notification]:
    """
    メンション通知を作成

    Args:
        message: Messageモデルインスタンス
        mentions: MessageMentionのリスト

    Returns:
        作成されたNotificationのリスト
    """
    if not mentions:
        return []

    notifications = []
    sender_name = message.sender_name
    channel = message.channel

    # 通知内容を作成
    content_preview = message.content[:50] + ('...' if len(message.content) > 50 else '')

    for mention in mentions:
        # 通知を作成
        notification = Notification.objects.create(
            tenant_id=message.tenant_id,
            user=mention.mentioned_user,
            notification_type='MENTION',
            title=f'{sender_name}さんがあなたをメンションしました',
            content=content_preview,
            action_url=f'/chat?channel={channel.id}&message={message.id}',
        )
        notifications.append(notification)
        logger.debug(f"Created mention notification for user {mention.mentioned_user.id}")

    return notifications


def send_mention_websocket_notifications(message, mentions: List[MessageMention]):
    """
    メンションのWebSocket通知を送信

    Args:
        message: Messageモデルインスタンス
        mentions: MessageMentionのリスト
    """
    from apps.communications.services.websocket import notify_user

    sender_name = message.sender_name
    channel = message.channel

    for mention in mentions:
        notify_user(
            user_id=str(mention.mentioned_user.id),
            notification_type='mention_notification',
            data={
                'channel_id': str(channel.id),
                'channel_name': channel.name,
                'message_id': str(message.id),
                'sender_name': sender_name,
                'content': message.content[:100],
            }
        )


def process_message_mentions(message) -> List[MessageMention]:
    """
    メッセージのメンションを処理（メイン関数）

    1. メンションをパース
    2. MessageMentionレコード作成
    3. Notification作成
    4. WebSocket通知送信

    Args:
        message: Messageモデルインスタンス

    Returns:
        作成されたMessageMentionのリスト
    """
    # メンションレコード作成
    mentions = create_mentions_for_message(message)

    if not mentions:
        return []

    # 通知作成
    create_mention_notifications(message, mentions)

    # WebSocket通知
    send_mention_websocket_notifications(message, mentions)

    return mentions


def format_content_with_mentions(content: str, mentions: List[dict] = None) -> str:
    """
    メンションを含むコンテンツを表示用にフォーマット
    @[user_id] → @ユーザー名 に変換

    Args:
        content: 元のメッセージ内容
        mentions: メンション情報のリスト [{'user_id': str, 'user_name': str}]

    Returns:
        フォーマットされたメッセージ内容
    """
    if not mentions:
        return content

    # user_idからuser_nameへのマッピングを作成
    user_map = {m['user_id']: m['user_name'] for m in mentions if 'user_id' in m and 'user_name' in m}

    def replace_mention(match):
        user_id = match.group(1)
        if user_id in user_map:
            return f"@{user_map[user_id]}"
        return match.group(0)

    return MENTION_PATTERN.sub(replace_mention, content)


def get_mentionable_users(channel) -> List[dict]:
    """
    チャンネル内でメンション可能なユーザー一覧を取得

    Args:
        channel: Channelモデルインスタンス

    Returns:
        ユーザー情報のリスト
    """
    members = channel.members.select_related('user').filter(
        user__isnull=False,
        user__is_active=True
    )

    return [
        {
            'id': str(member.user.id),
            'name': member.user.full_name or member.user.email,
            'email': member.user.email,
        }
        for member in members
    ]
