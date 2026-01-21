"""
Communications URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ChannelViewSet, MessageViewSet, ContactLogViewSet,
    NotificationViewSet, BotConfigViewSet, BotFAQViewSet,
    BotChatViewSet, AnnouncementViewSet,
    FeedPostViewSet, FeedCommentViewSet, FeedBookmarkViewSet,
    ChatLogViewSet,
    MessageMemoViewSet, TelMemoViewSet,
)

app_name = 'communications'

router = DefaultRouter()
router.register(r'channels', ChannelViewSet, basename='channel')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'contact-logs', ContactLogViewSet, basename='contact-log')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'bot/configs', BotConfigViewSet, basename='bot-config')
router.register(r'bot/faqs', BotFAQViewSet, basename='bot-faq')
router.register(r'bot/chat', BotChatViewSet, basename='bot-chat')
router.register(r'announcements', AnnouncementViewSet, basename='announcement')
router.register(r'feed/posts', FeedPostViewSet, basename='feed-post')
router.register(r'feed/comments', FeedCommentViewSet, basename='feed-comment')
router.register(r'feed/bookmarks', FeedBookmarkViewSet, basename='feed-bookmark')
router.register(r'chat-logs', ChatLogViewSet, basename='chat-log')
router.register(r'message-memos', MessageMemoViewSet, basename='message-memo')
router.register(r'tel-memos', TelMemoViewSet, basename='tel-memo')

urlpatterns = [
    path('', include(router.urls)),
]
