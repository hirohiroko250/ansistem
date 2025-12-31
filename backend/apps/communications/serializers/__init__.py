"""
Communications Serializers

モジュール構成:
- channel.py: Channel & Message serializers
- contact.py: ContactLog & Notification serializers
- bot.py: Bot serializers
- announcement.py: Announcement serializers
- feed.py: Feed serializers
- chatlog.py: ChatLog serializers
"""
# Channel & Message
from .channel import (
    ChannelMemberSerializer,
    ChannelListSerializer,
    ChannelDetailSerializer,
    ChannelCreateSerializer,
    MessageSerializer,
    MessageCreateSerializer,
)

# Contact Log & Notification
from .contact import (
    ContactLogCommentSerializer,
    ContactLogListSerializer,
    ContactLogDetailSerializer,
    ContactLogCreateSerializer,
    NotificationSerializer,
)

# Bot
from .bot import (
    BotFAQSerializer,
    BotConfigSerializer,
    BotConversationSerializer,
    BotChatSerializer,
)

# Announcement
from .announcement import (
    AnnouncementListSerializer,
    AnnouncementDetailSerializer,
    AnnouncementCreateSerializer,
)

# Feed
from .feed import (
    FeedMediaSerializer,
    FeedCommentSerializer,
    FeedCommentCreateSerializer,
    FeedPostListSerializer,
    FeedPostDetailSerializer,
    FeedPostCreateSerializer,
    FeedLikeSerializer,
    FeedBookmarkSerializer,
)

# ChatLog
from .chatlog import (
    ChatLogSerializer,
    ChatLogListSerializer,
)

__all__ = [
    # Channel & Message
    'ChannelMemberSerializer',
    'ChannelListSerializer',
    'ChannelDetailSerializer',
    'ChannelCreateSerializer',
    'MessageSerializer',
    'MessageCreateSerializer',
    # Contact Log & Notification
    'ContactLogCommentSerializer',
    'ContactLogListSerializer',
    'ContactLogDetailSerializer',
    'ContactLogCreateSerializer',
    'NotificationSerializer',
    # Bot
    'BotFAQSerializer',
    'BotConfigSerializer',
    'BotConversationSerializer',
    'BotChatSerializer',
    # Announcement
    'AnnouncementListSerializer',
    'AnnouncementDetailSerializer',
    'AnnouncementCreateSerializer',
    # Feed
    'FeedMediaSerializer',
    'FeedCommentSerializer',
    'FeedCommentCreateSerializer',
    'FeedPostListSerializer',
    'FeedPostDetailSerializer',
    'FeedPostCreateSerializer',
    'FeedLikeSerializer',
    'FeedBookmarkSerializer',
    # ChatLog
    'ChatLogSerializer',
    'ChatLogListSerializer',
]
