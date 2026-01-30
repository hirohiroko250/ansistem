from django import forms
from django.contrib import admin
from apps.core.admin_csv import CSVImportExportMixin
from apps.tenants.models import Tenant
from .models import (
    Channel, ChannelMember, Message, MessageRead,
    ContactLog, ContactLogComment, Notification,
    BotConfig, BotFAQ, BotConversation,
    Announcement, AnnouncementRead,
    FeedPost, FeedMedia, FeedLike, FeedComment, FeedCommentLike, FeedBookmark,
    ChatLog
)


@admin.register(Channel)
class ChannelAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['name', 'channel_type', 'student', 'guardian', 'school', 'is_archived', 'created_at']
    list_filter = ['channel_type', 'is_archived']
    search_fields = ['name']

    csv_import_fields = {
        'チャンネル名': 'name',
        'チャンネル種別': 'channel_type',
        'アーカイブ': 'is_archived',
    }
    csv_required_fields = ['チャンネル名']
    csv_unique_fields = []
    csv_export_fields = ['name', 'channel_type', 'student.student_no', 'guardian.guardian_no', 'school.school_name', 'is_archived', 'created_at']
    csv_export_headers = {
        'name': 'チャンネル名',
        'channel_type': 'チャンネル種別',
        'student.student_no': '生徒番号',
        'guardian.guardian_no': '保護者番号',
        'school.school_name': '校舎名',
        'is_archived': 'アーカイブ',
        'created_at': '作成日時',
    }


@admin.register(Message)
class MessageAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['channel', 'message_type', 'sender', 'is_bot_message', 'created_at']
    list_filter = ['message_type', 'is_bot_message']
    search_fields = ['content']

    csv_import_fields = {
        'メッセージ種別': 'message_type',
        '内容': 'content',
        'ボットメッセージ': 'is_bot_message',
    }
    csv_required_fields = ['内容']
    csv_unique_fields = []
    csv_export_fields = ['channel.name', 'message_type', 'content', 'sender.email', 'is_bot_message', 'created_at']
    csv_export_headers = {
        'channel.name': 'チャンネル名',
        'message_type': 'メッセージ種別',
        'content': '内容',
        'sender.email': '送信者',
        'is_bot_message': 'ボットメッセージ',
        'created_at': '作成日時',
    }


@admin.register(ContactLog)
class ContactLogAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['subject', 'contact_type', 'student', 'guardian', 'handled_by', 'status', 'priority', 'created_at']
    list_filter = ['contact_type', 'status', 'priority']
    search_fields = ['subject', 'content']

    csv_import_fields = {
        '件名': 'subject',
        '連絡種別': 'contact_type',
        '内容': 'content',
        'ステータス': 'status',
        '優先度': 'priority',
    }
    csv_required_fields = ['件名']
    csv_unique_fields = []
    csv_export_fields = ['subject', 'contact_type', 'content', 'student.student_no', 'guardian.guardian_no', 'handled_by.email', 'status', 'priority', 'created_at']
    csv_export_headers = {
        'subject': '件名',
        'contact_type': '連絡種別',
        'content': '内容',
        'student.student_no': '生徒番号',
        'guardian.guardian_no': '保護者番号',
        'handled_by.email': '担当者',
        'status': 'ステータス',
        'priority': '優先度',
        'created_at': '作成日時',
    }


@admin.register(Notification)
class NotificationAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['title', 'notification_type', 'user', 'guardian', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read']
    search_fields = ['title', 'content']

    csv_import_fields = {
        'タイトル': 'title',
        '通知種別': 'notification_type',
        '内容': 'content',
    }
    csv_required_fields = ['タイトル']
    csv_unique_fields = []
    csv_export_fields = ['title', 'notification_type', 'content', 'user.email', 'guardian.guardian_no', 'is_read', 'created_at']
    csv_export_headers = {
        'title': 'タイトル',
        'notification_type': '通知種別',
        'content': '内容',
        'user.email': 'ユーザー',
        'guardian.guardian_no': '保護者番号',
        'is_read': '既読',
        'created_at': '作成日時',
    }


@admin.register(BotConfig)
class BotConfigAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['name', 'bot_type', 'ai_enabled', 'is_active']
    list_filter = ['bot_type', 'ai_enabled', 'is_active']

    csv_import_fields = {
        '名前': 'name',
        'ボット種別': 'bot_type',
        'AI有効': 'ai_enabled',
        '有効': 'is_active',
    }
    csv_required_fields = ['名前']
    csv_unique_fields = []
    csv_export_fields = ['name', 'bot_type', 'ai_enabled', 'is_active']
    csv_export_headers = {
        'name': '名前',
        'bot_type': 'ボット種別',
        'ai_enabled': 'AI有効',
        'is_active': '有効',
    }


@admin.register(BotFAQ)
class BotFAQAdmin(CSVImportExportMixin, admin.ModelAdmin):
    list_display = ['question', 'category', 'bot_config', 'sort_order', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['question', 'answer']

    csv_import_fields = {
        '質問': 'question',
        '回答': 'answer',
        'カテゴリ': 'category',
        '並び順': 'sort_order',
        '有効': 'is_active',
    }
    csv_required_fields = ['質問', '回答']
    csv_unique_fields = []
    csv_export_fields = ['question', 'answer', 'category', 'bot_config.name', 'sort_order', 'is_active']
    csv_export_headers = {
        'question': '質問',
        'answer': '回答',
        'category': 'カテゴリ',
        'bot_config.name': 'ボット設定',
        'sort_order': '並び順',
        'is_active': '有効',
    }


class AnnouncementAdminForm(forms.ModelForm):
    """お知らせ管理フォーム（テナント選択対応）"""
    tenant = forms.ModelChoiceField(
        queryset=Tenant.objects.filter(is_active=True).order_by('tenant_code'),
        label='テナント',
        required=True,
        help_text='お知らせを配信するテナントを選択してください'
    )

    class Meta:
        model = Announcement
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 既存データの場合、tenant_idからテナントを設定
        if self.instance and self.instance.pk and self.instance.tenant_id:
            try:
                self.fields['tenant'].initial = Tenant.objects.get(id=self.instance.tenant_id)
            except Tenant.DoesNotExist:
                pass

    def save(self, commit=True):
        instance = super().save(commit=False)
        # 選択されたテナントのIDを設定
        if self.cleaned_data.get('tenant'):
            instance.tenant_id = self.cleaned_data['tenant'].id
        if commit:
            instance.save()
            self.save_m2m()
        return instance


@admin.register(Announcement)
class AnnouncementAdmin(CSVImportExportMixin, admin.ModelAdmin):
    form = AnnouncementAdminForm
    list_display = ['title', 'get_tenant_name', 'target_type', 'status', 'sent_count', 'read_count', 'created_at']
    list_filter = ['target_type', 'status']
    search_fields = ['title', 'content']
    exclude = ['tenant_id']

    def get_tenant_name(self, obj):
        """テナント名を取得"""
        if obj.tenant_id:
            try:
                tenant = Tenant.objects.get(id=obj.tenant_id)
                return tenant.tenant_name
            except Tenant.DoesNotExist:
                return str(obj.tenant_id)
        return '-'
    get_tenant_name.short_description = 'テナント'

    csv_import_fields = {
        'タイトル': 'title',
        '内容': 'content',
        '対象種別': 'target_type',
        'ステータス': 'status',
    }
    csv_required_fields = ['タイトル', '内容']
    csv_unique_fields = []
    csv_export_fields = ['title', 'content', 'target_type', 'status', 'sent_count', 'read_count', 'created_at']
    csv_export_headers = {
        'title': 'タイトル',
        'content': '内容',
        'target_type': '対象種別',
        'status': 'ステータス',
        'sent_count': '送信数',
        'read_count': '既読数',
        'created_at': '作成日時',
    }


class FeedMediaInline(admin.TabularInline):
    """フィードメディアインライン"""
    model = FeedMedia
    extra = 1
    fields = ['media_type', 'file_url', 'thumbnail_url', 'file_name', 'sort_order']


@admin.register(FeedPost)
class FeedPostAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """フィード投稿Admin"""
    list_display = [
        'get_content_preview', 'post_type', 'author', 'school',
        'visibility', 'is_pinned', 'like_count', 'comment_count',
        'is_published', 'approval_status', 'created_at'
    ]
    list_filter = ['post_type', 'visibility', 'is_pinned', 'is_published', 'approval_status', 'is_deleted']
    search_fields = ['content', 'hashtags']
    filter_horizontal = ['target_schools', 'target_grades']
    inlines = [FeedMediaInline]
    ordering = ['-created_at']
    readonly_fields = ['like_count', 'comment_count', 'view_count', 'approved_by', 'approved_at', 'created_at', 'updated_at']

    fieldsets = (
        ('基本情報', {
            'fields': ('author', 'school', 'post_type', 'content', 'hashtags')
        }),
        ('公開設定', {
            'fields': ('visibility', 'target_schools', 'target_grades', 'is_published', 'published_at',
                       'approval_status', 'approved_by', 'approved_at')
        }),
        ('表示設定', {
            'fields': ('is_pinned', 'pinned_at', 'allow_comments', 'allow_likes')
        }),
        ('統計', {
            'fields': ('like_count', 'comment_count', 'view_count'),
            'classes': ('collapse',)
        }),
        ('システム情報', {
            'fields': ('tenant_id', 'is_deleted', 'deleted_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    get_content_preview.short_description = '内容'

    csv_import_fields = {
        '内容': 'content',
        '投稿種別': 'post_type',
        '公開範囲': 'visibility',
        '固定表示': 'is_pinned',
        'コメント許可': 'allow_comments',
        'いいね許可': 'allow_likes',
        '公開済み': 'is_published',
    }
    csv_required_fields = ['内容']
    csv_unique_fields = []
    csv_export_fields = [
        'content', 'post_type', 'author.email', 'school.school_name',
        'visibility', 'is_pinned', 'like_count', 'comment_count',
        'is_published', 'created_at'
    ]
    csv_export_headers = {
        'content': '内容',
        'post_type': '投稿種別',
        'author.email': '投稿者',
        'school.school_name': '校舎',
        'visibility': '公開範囲',
        'is_pinned': '固定表示',
        'like_count': 'いいね数',
        'comment_count': 'コメント数',
        'is_published': '公開済み',
        'created_at': '作成日時',
    }


@admin.register(FeedMedia)
class FeedMediaAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """フィードメディアAdmin"""
    list_display = ['post', 'media_type', 'file_name', 'sort_order', 'created_at']
    list_filter = ['media_type']
    search_fields = ['file_name', 'file_url']

    csv_import_fields = {}
    csv_required_fields = []
    csv_unique_fields = []
    csv_export_fields = [
        'post.id', 'media_type', 'file_url', 'file_name',
        'file_size', 'sort_order', 'created_at',
    ]
    csv_export_headers = {
        'post.id': '投稿ID',
        'media_type': 'メディア種別',
        'file_url': 'ファイルURL',
        'file_name': 'ファイル名',
        'file_size': 'ファイルサイズ',
        'sort_order': '並び順',
        'created_at': '作成日時',
    }


@admin.register(FeedComment)
class FeedCommentAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """フィードコメントAdmin"""
    list_display = ['get_content_preview', 'post', 'user', 'guardian', 'like_count', 'is_deleted', 'created_at']
    list_filter = ['is_deleted']
    search_fields = ['content']

    def get_content_preview(self, obj):
        return obj.content[:30] + '...' if len(obj.content) > 30 else obj.content
    get_content_preview.short_description = 'コメント'

    csv_import_fields = {}
    csv_required_fields = []
    csv_unique_fields = []
    csv_export_fields = [
        'post.id', 'user.email', 'guardian.guardian_no',
        'content', 'like_count', 'is_deleted', 'created_at',
    ]
    csv_export_headers = {
        'post.id': '投稿ID',
        'user.email': 'ユーザー',
        'guardian.guardian_no': '保護者番号',
        'content': 'コメント内容',
        'like_count': 'いいね数',
        'is_deleted': '削除済',
        'created_at': '作成日時',
    }


@admin.register(FeedLike)
class FeedLikeAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """フィードいいねAdmin"""
    list_display = ['post', 'user', 'guardian', 'created_at']

    csv_import_fields = {}
    csv_required_fields = []
    csv_unique_fields = []
    csv_export_fields = ['post.id', 'user.email', 'guardian.guardian_no', 'created_at']
    csv_export_headers = {
        'post.id': '投稿ID',
        'user.email': 'ユーザー',
        'guardian.guardian_no': '保護者番号',
        'created_at': '作成日時',
    }


@admin.register(FeedBookmark)
class FeedBookmarkAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """フィードブックマークAdmin"""
    list_display = ['post', 'user', 'guardian', 'created_at']

    csv_import_fields = {}
    csv_required_fields = []
    csv_unique_fields = []
    csv_export_fields = ['post.id', 'user.email', 'guardian.guardian_no', 'created_at']
    csv_export_headers = {
        'post.id': '投稿ID',
        'user.email': 'ユーザー',
        'guardian.guardian_no': '保護者番号',
        'created_at': '作成日時',
    }


@admin.register(ChatLog)
class ChatLogAdmin(CSVImportExportMixin, admin.ModelAdmin):
    """チャットログAdmin"""
    list_display = [
        'timestamp', 'brand_name', 'school_name', 'guardian_name',
        'sender_type', 'get_content_preview'
    ]
    list_filter = ['sender_type', 'brand_name', 'school_name']
    search_fields = ['content', 'guardian_name', 'school_name', 'brand_name']
    ordering = ['-timestamp']
    readonly_fields = ['id', 'timestamp', 'message']
    date_hierarchy = 'timestamp'

    fieldsets = (
        ('基本情報', {
            'fields': ('timestamp', 'sender_type', 'content')
        }),
        ('送信者情報', {
            'fields': ('guardian', 'guardian_name')
        }),
        ('所属情報', {
            'fields': ('brand', 'brand_name', 'school', 'school_name')
        }),
        ('システム情報', {
            'fields': ('id', 'tenant_id', 'message'),
            'classes': ('collapse',)
        }),
    )

    def get_content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    get_content_preview.short_description = 'メッセージ内容'

    csv_import_fields = {}
    csv_required_fields = []
    csv_unique_fields = []
    csv_export_fields = [
        'timestamp', 'brand_name', 'school_name', 'guardian_name',
        'sender_type', 'content'
    ]
    csv_export_headers = {
        'timestamp': 'タイムスタンプ',
        'brand_name': 'ブランド',
        'school_name': '校舎',
        'guardian_name': '保護者名',
        'sender_type': '送信者タイプ',
        'content': 'メッセージ内容',
    }
