"""
Staff Profile Models - 講師プロフィール詳細
"""
import uuid
from django.db import models
from apps.core.models import TenantModel


class StaffProfile(TenantModel):
    """講師・社員の詳細プロフィール"""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    employee = models.OneToOneField(
        'tenants.Employee',
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='社員'
    )
    # 表示名（ニックネーム）
    display_name = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='表示名',
        help_text='「○○先生」など'
    )
    # 自己紹介
    greeting = models.TextField(
        blank=True,
        verbose_name='ごあいさつ'
    )
    bio = models.TextField(
        blank=True,
        verbose_name='自己紹介'
    )
    lesson_style = models.TextField(
        blank=True,
        verbose_name='レッスン内容・スタイル'
    )
    career = models.TextField(
        blank=True,
        verbose_name='経歴・趣味'
    )
    # 出身・居住情報
    origin_country = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='出身国'
    )
    residence_country = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='居住国'
    )
    # コミュニケーションツール
    communication_tool = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='通話ツール',
        help_text='Google Meet, Zoom, Skype等'
    )
    communication_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='通話URL'
    )
    # SNS・連絡先
    line_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='LINE ID'
    )
    twitter_url = models.URLField(
        max_length=200,
        blank=True,
        verbose_name='Twitter URL'
    )
    instagram_url = models.URLField(
        max_length=200,
        blank=True,
        verbose_name='Instagram URL'
    )
    youtube_url = models.URLField(
        max_length=200,
        blank=True,
        verbose_name='YouTube URL'
    )
    # 評価
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        verbose_name='評価'
    )
    review_count = models.PositiveIntegerField(
        default=0,
        verbose_name='レビュー数'
    )
    lesson_count = models.PositiveIntegerField(
        default=0,
        verbose_name='レッスン回数'
    )
    # ポイント・ランキング
    points = models.PositiveIntegerField(
        default=0,
        verbose_name='ポイント'
    )
    # 公開設定
    is_public = models.BooleanField(
        default=False,
        verbose_name='プロフィール公開'
    )
    is_bookable = models.BooleanField(
        default=False,
        verbose_name='予約受付可'
    )
    # 事務局コメント
    admin_comment = models.TextField(
        blank=True,
        verbose_name='事務局より'
    )
    # 作成日時
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='作成日時'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新日時'
    )

    class Meta:
        db_table = 't_staff_profile'
        verbose_name = '講師プロフィール'
        verbose_name_plural = '講師プロフィール'

    def __str__(self):
        return self.display_name or self.employee.full_name


class StaffSkill(TenantModel):
    """講師のスキル・得意分野"""

    class SkillCategory(models.TextChoices):
        SUBJECT = 'subject', '教科'
        LANGUAGE = 'language', '言語'
        CERTIFICATION = 'certification', '資格'
        SPECIALTY = 'specialty', '得意分野'
        OTHER = 'other', 'その他'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    profile = models.ForeignKey(
        StaffProfile,
        on_delete=models.CASCADE,
        related_name='skills',
        verbose_name='プロフィール'
    )
    category = models.CharField(
        max_length=20,
        choices=SkillCategory.choices,
        default=SkillCategory.SPECIALTY,
        verbose_name='カテゴリ'
    )
    name = models.CharField(
        max_length=50,
        verbose_name='スキル名'
    )
    level = models.PositiveSmallIntegerField(
        default=3,
        verbose_name='レベル',
        help_text='1-5'
    )
    display_order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='表示順'
    )
    # タグ表示用の色
    color = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='表示色',
        help_text='blue, green, red, purple等'
    )

    class Meta:
        db_table = 't_staff_skill'
        verbose_name = '講師スキル'
        verbose_name_plural = '講師スキル'
        ordering = ['category', 'display_order', 'name']

    def __str__(self):
        return f"{self.profile.employee.full_name} - {self.name}"


class StaffReview(TenantModel):
    """講師へのレビュー・生徒の声"""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    profile = models.ForeignKey(
        StaffProfile,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='プロフィール'
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_reviews',
        verbose_name='生徒'
    )
    rating = models.PositiveSmallIntegerField(
        verbose_name='評価',
        help_text='1-5'
    )
    comment = models.TextField(
        blank=True,
        verbose_name='コメント'
    )
    # 公開設定
    is_public = models.BooleanField(
        default=False,
        verbose_name='公開'
    )
    is_approved = models.BooleanField(
        default=False,
        verbose_name='承認済み'
    )
    # 匿名表示
    is_anonymous = models.BooleanField(
        default=False,
        verbose_name='匿名'
    )
    # 作成日時
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='作成日時'
    )

    class Meta:
        db_table = 't_staff_review'
        verbose_name = '講師レビュー'
        verbose_name_plural = '講師レビュー'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.profile.employee.full_name} - {self.rating}点"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # プロフィールの評価を更新
        self.profile.update_rating()


class StaffProfilePhoto(TenantModel):
    """講師のプロフィール写真（複数枚対応）"""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    profile = models.ForeignKey(
        StaffProfile,
        on_delete=models.CASCADE,
        related_name='photos',
        verbose_name='プロフィール'
    )
    image_url = models.URLField(
        max_length=500,
        verbose_name='画像URL'
    )
    caption = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='キャプション'
    )
    is_main = models.BooleanField(
        default=False,
        verbose_name='メイン画像'
    )
    display_order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='表示順'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='作成日時'
    )

    class Meta:
        db_table = 't_staff_profile_photo'
        verbose_name = '講師写真'
        verbose_name_plural = '講師写真'
        ordering = ['-is_main', 'display_order']

    def __str__(self):
        return f"{self.profile.employee.full_name} - 写真{self.display_order}"
