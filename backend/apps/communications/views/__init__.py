"""
Communications Views Package
コミュニケーション関連Views
"""

# Channel
from .channel import ChannelViewSet

# Message
from .message import MessageViewSet

# Contact
from .contact import ContactLogViewSet

# Notification
from .notification import NotificationViewSet

# Bot
from .bot import (
    BotConfigViewSet,
    BotFAQViewSet,
    BotChatViewSet,
)

# Announcement
from .announcement import AnnouncementViewSet

# Feed
from .feed import (
    FeedPostViewSet,
    FeedCommentViewSet,
    FeedBookmarkViewSet,
)

# ChatLog
from .chat_log import ChatLogViewSet

# Memo
from .memo import (
    MessageMemoViewSet,
    TelMemoViewSet,
)


__all__ = [
    # Channel & Message
    'ChannelViewSet',
    'MessageViewSet',
    # Contact
    'ContactLogViewSet',
    # Notification
    'NotificationViewSet',
    # Bot
    'BotConfigViewSet',
    'BotFAQViewSet',
    'BotChatViewSet',
    # Announcement
    'AnnouncementViewSet',
    # Feed
    'FeedPostViewSet',
    'FeedCommentViewSet',
    'FeedBookmarkViewSet',
    # ChatLog
    'ChatLogViewSet',
    # Memo
    'MessageMemoViewSet',
    'TelMemoViewSet',
]
