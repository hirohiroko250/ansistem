"""
Knowledge Management Models
社内マニュアル・返信テンプレート管理
"""
import uuid
from django.db import models
from apps.core.models import TenantModel


class ManualCategory(TenantModel):
    """マニュアルカテゴリ"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('カテゴリ名', max_length=100)
    slug = models.CharField('スラッグ', max_length=100, blank=True)
    description = models.TextField('説明', blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='親カテゴリ'
    )
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't30_manual_categories'
        verbose_name = 'マニュアルカテゴリ'
        verbose_name_plural = 'マニュアルカテゴリ'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Manual(TenantModel):
    """社内マニュアル"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField('タイトル', max_length=200)
    slug = models.CharField('スラッグ', max_length=200, blank=True)
    category = models.ForeignKey(
        ManualCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manuals',
        verbose_name='カテゴリ'
    )
    content = models.TextField('内容', help_text='Markdown形式で記述可能')
    summary = models.TextField('概要', blank=True, help_text='検索用の概要')
    tags = models.JSONField('タグ', default=list, blank=True)

    # 画像
    images = models.JSONField(
        '画像',
        default=list,
        blank=True,
        help_text='添付画像のURL一覧 [{"url": "...", "alt": "..."}]'
    )
    cover_image = models.URLField('カバー画像', blank=True, help_text='サムネイル用の画像URL')

    # メタデータ
    author = models.ForeignKey(
        'tenants.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='authored_manuals',
        verbose_name='作成者'
    )
    external_url = models.URLField('外部リンク', blank=True, help_text='Google Docsなどの外部リンク')

    # 閲覧情報
    view_count = models.IntegerField('閲覧数', default=0)

    # ステータス
    is_published = models.BooleanField('公開', default=True)
    is_pinned = models.BooleanField('ピン留め', default=False)

    # 日時
    published_at = models.DateTimeField('公開日時', null=True, blank=True)

    class Meta:
        db_table = 't31_manuals'
        verbose_name = 'マニュアル'
        verbose_name_plural = 'マニュアル'
        ordering = ['-is_pinned', '-updated_at']

    def __str__(self):
        return self.title

    def increment_view_count(self):
        self.view_count += 1
        self.save(update_fields=['view_count'])


class TemplateCategory(TenantModel):
    """テンプレートカテゴリ"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('カテゴリ名', max_length=100)
    slug = models.CharField('スラッグ', max_length=100, blank=True)
    description = models.TextField('説明', blank=True)
    sort_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 't32_template_categories'
        verbose_name = 'テンプレートカテゴリ'
        verbose_name_plural = 'テンプレートカテゴリ'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class ChatTemplate(TenantModel):
    """チャット返信テンプレート"""

    class TemplateType(models.TextChoices):
        CHAT = 'chat', 'チャット返信'
        EMAIL = 'email', 'メール'
        SMS = 'sms', 'SMS'
        NOTIFICATION = 'notification', '通知'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField('タイトル', max_length=200)
    template_type = models.CharField(
        'テンプレート種別',
        max_length=20,
        choices=TemplateType.choices,
        default=TemplateType.CHAT
    )
    category = models.ForeignKey(
        TemplateCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='templates',
        verbose_name='カテゴリ'
    )

    # 使用場面
    scene = models.CharField('使用場面', max_length=200, blank=True, help_text='例: 入会申請後の返信')

    # テンプレート内容
    subject = models.CharField('件名', max_length=200, blank=True, help_text='メール用')
    content = models.TextField('本文')

    # 変数定義
    variables = models.JSONField(
        '変数',
        default=list,
        blank=True,
        help_text='使用可能な変数 例: ["保護者名", "生徒名", "校舎名"]'
    )

    # タグ
    tags = models.JSONField('タグ', default=list, blank=True)

    # 使用統計
    use_count = models.IntegerField('使用回数', default=0)

    # ステータス
    is_active = models.BooleanField('有効', default=True)
    is_default = models.BooleanField('デフォルト', default=False, help_text='同じ場面でのデフォルトテンプレート')

    class Meta:
        db_table = 't33_chat_templates'
        verbose_name = 'チャットテンプレート'
        verbose_name_plural = 'チャットテンプレート'
        ordering = ['-is_default', '-use_count', 'title']

    def __str__(self):
        return f"{self.title} ({self.get_template_type_display()})"

    def increment_use_count(self):
        self.use_count += 1
        self.save(update_fields=['use_count'])

    def render(self, context: dict) -> str:
        """変数を置換してテンプレートをレンダリング"""
        content = self.content
        for key, value in context.items():
            content = content.replace(f'{{{key}}}', str(value))
        return content
