"""
Chat Log Model - チャットログ
"""
import uuid
from django.db import models

from .chat import Message


class ChatLog(models.Model):
    """チャットログ（メッセージ送信時に自動記録）"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    tenant_id = models.UUIDField(verbose_name='会社ID')
    # 関連メッセージ
    message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_logs',
        verbose_name='メッセージ'
    )
    # 校舎情報
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_logs',
        verbose_name='校舎'
    )
    school_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='校舎名（スナップショット）'
    )
    # 保護者情報
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_logs',
        verbose_name='保護者'
    )
    guardian_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='保護者名（スナップショット）'
    )
    # ブランド情報
    brand = models.ForeignKey(
        'schools.Brand',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_logs',
        verbose_name='ブランド'
    )
    brand_name = models.CharField(
        max_length=100,
        default='その他',
        verbose_name='ブランド名（スナップショット）'
    )
    # メッセージ内容
    content = models.TextField(verbose_name='メッセージ内容')
    # 送信者タイプ
    sender_type = models.CharField(
        max_length=20,
        choices=[
            ('GUARDIAN', '保護者'),
            ('STAFF', 'スタッフ'),
            ('BOT', 'ボット'),
        ],
        verbose_name='送信者タイプ'
    )
    # タイムスタンプ
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='タイムスタンプ')

    class Meta:
        db_table = 'communication_chat_logs'
        verbose_name = 'チャットログ'
        verbose_name_plural = 'チャットログ'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tenant_id', '-timestamp']),
            models.Index(fields=['school', '-timestamp']),
            models.Index(fields=['guardian', '-timestamp']),
            models.Index(fields=['brand', '-timestamp']),
        ]

    def __str__(self):
        return f"[{self.timestamp}] {self.brand_name} - {self.school_name} - {self.guardian_name}: {self.content[:30]}..."

    @classmethod
    def create_from_message(cls, message, tenant_id):
        """メッセージからチャットログを作成"""
        guardian = message.sender_guardian
        school = None
        brand = None
        brand_name = 'その他'
        school_name = None
        guardian_name = None
        sender_type = 'STAFF'

        # 送信者タイプを判定
        if message.is_bot_message:
            sender_type = 'BOT'
        elif guardian:
            sender_type = 'GUARDIAN'
            guardian_name = guardian.full_name

            # 保護者から校舎・ブランド情報を取得
            # 保護者の生徒から校舎を取得
            students = guardian.students.all()
            if students.exists():
                student = students.first()
                # 生徒のコースから校舎を取得
                contracts = student.contracts.filter(is_active=True).select_related('school', 'brand')
                if contracts.exists():
                    contract = contracts.first()
                    school = contract.school
                    brand = contract.brand
                    if school:
                        school_name = school.school_name
                    if brand:
                        brand_name = brand.brand_name

        # チャンネルから校舎情報を取得（保護者から取得できなかった場合）
        if not school and message.channel and message.channel.school:
            school = message.channel.school
            school_name = school.school_name

        return cls.objects.create(
            tenant_id=tenant_id,
            message=message,
            school=school,
            school_name=school_name,
            guardian=guardian,
            guardian_name=guardian_name,
            brand=brand,
            brand_name=brand_name,
            content=message.content,
            sender_type=sender_type,
        )
