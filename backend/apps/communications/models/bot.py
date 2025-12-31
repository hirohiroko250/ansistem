"""
Bot Models - チャットボット関連
BotConfig, BotFAQ, BotConversation
"""
import uuid
from django.db import models

from .chat import Channel


class BotConfig(models.Model):
    """チャットボット設定"""

    class BotType(models.TextChoices):
        FAQ = 'FAQ', 'FAQ応答'
        SCHEDULE = 'SCHEDULE', 'スケジュール確認'
        GENERAL = 'GENERAL', '一般応答'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    tenant_id = models.UUIDField(verbose_name='会社ID')
    name = models.CharField(
        max_length=50,
        verbose_name='ボット名'
    )
    bot_type = models.CharField(
        max_length=20,
        choices=BotType.choices,
        default=BotType.GENERAL,
        verbose_name='ボット種別'
    )
    welcome_message = models.TextField(
        default='こんにちは！何かお手伝いできることはありますか？',
        verbose_name='ウェルカムメッセージ'
    )
    fallback_message = models.TextField(
        default='申し訳ございません。ご質問の内容を理解できませんでした。スタッフにお繋ぎしますか？',
        verbose_name='フォールバックメッセージ'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='有効'
    )
    # AI設定（OpenAI等）
    ai_enabled = models.BooleanField(
        default=False,
        verbose_name='AI応答有効'
    )
    ai_model = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='AIモデル'
    )
    ai_system_prompt = models.TextField(
        null=True,
        blank=True,
        verbose_name='AIシステムプロンプト'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'communication_bot_configs'
        verbose_name = 'ボット設定'
        verbose_name_plural = 'ボット設定'

    def __str__(self):
        return f"{self.name} ({self.get_bot_type_display()})"


class BotFAQ(models.Model):
    """ボットFAQ"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    tenant_id = models.UUIDField(verbose_name='会社ID')
    bot_config = models.ForeignKey(
        BotConfig,
        on_delete=models.CASCADE,
        related_name='faqs',
        verbose_name='ボット設定'
    )
    category = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='カテゴリ'
    )
    question = models.TextField(
        verbose_name='質問'
    )
    # キーワード（マッチング用）
    keywords = models.JSONField(
        default=list,
        verbose_name='キーワード'
    )
    answer = models.TextField(
        verbose_name='回答'
    )
    # 次のアクション
    next_action = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='次のアクション'
    )
    sort_order = models.IntegerField(
        default=0,
        verbose_name='表示順'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='有効'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'communication_bot_faqs'
        verbose_name = 'ボットFAQ'
        verbose_name_plural = 'ボットFAQ'
        ordering = ['category', 'sort_order']

    def __str__(self):
        return f"{self.question[:50]}..."


class BotConversation(models.Model):
    """ボット会話ログ"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    tenant_id = models.UUIDField(verbose_name='会社ID')
    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        related_name='bot_conversations',
        verbose_name='チャンネル'
    )
    bot_config = models.ForeignKey(
        BotConfig,
        on_delete=models.SET_NULL,
        null=True,
        related_name='conversations',
        verbose_name='ボット設定'
    )
    # ユーザー入力
    user_input = models.TextField(
        verbose_name='ユーザー入力'
    )
    # ボット応答
    bot_response = models.TextField(
        verbose_name='ボット応答'
    )
    # マッチしたFAQ
    matched_faq = models.ForeignKey(
        BotFAQ,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='マッチFAQ'
    )
    # AI応答の場合
    is_ai_response = models.BooleanField(
        default=False,
        verbose_name='AI応答'
    )
    # スタッフに転送されたか
    escalated_to_staff = models.BooleanField(
        default=False,
        verbose_name='スタッフ転送'
    )
    escalated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='転送日時'
    )
    # フィードバック
    was_helpful = models.BooleanField(
        null=True,
        blank=True,
        verbose_name='役に立った'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')

    class Meta:
        db_table = 'communication_bot_conversations'
        verbose_name = 'ボット会話'
        verbose_name_plural = 'ボット会話'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user_input[:30]}... -> {self.bot_response[:30]}..."
