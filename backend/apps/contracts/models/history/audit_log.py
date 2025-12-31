"""
SystemAuditLog Model - システム監査ログ
"""
import uuid
from django.db import models
from apps.core.models import TenantModel


class SystemAuditLog(TenantModel):
    """システム監査ログ

    システム全体の操作履歴を記録する。
    契約だけでなく、生徒、保護者、請求など全てのエンティティの変更を追跡。
    """

    class EntityType(models.TextChoices):
        STUDENT = 'student', '生徒'
        GUARDIAN = 'guardian', '保護者'
        CONTRACT = 'contract', '契約'
        STUDENT_ITEM = 'student_item', '生徒商品'
        INVOICE = 'invoice', '請求書'
        PAYMENT = 'payment', '入金'
        MILE = 'mile', 'マイル'
        DISCOUNT = 'discount', '割引'
        SCHOOL = 'school', '校舎'
        COURSE = 'course', 'コース'
        CLASS_SCHEDULE = 'class_schedule', 'クラススケジュール'
        ENROLLMENT = 'enrollment', '受講登録'
        USER = 'user', 'ユーザー'
        OTHER = 'other', 'その他'

    class ActionType(models.TextChoices):
        CREATE = 'create', '作成'
        UPDATE = 'update', '更新'
        DELETE = 'delete', '削除'
        SOFT_DELETE = 'soft_delete', '論理削除'
        RESTORE = 'restore', '復元'
        LOGIN = 'login', 'ログイン'
        LOGOUT = 'logout', 'ログアウト'
        EXPORT = 'export', 'エクスポート'
        IMPORT = 'import', 'インポート'
        APPROVE = 'approve', '承認'
        REJECT = 'reject', '却下'
        CANCEL = 'cancel', 'キャンセル'
        OTHER = 'other', 'その他'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 対象エンティティ
    entity_type = models.CharField(
        'エンティティ種別',
        max_length=30,
        choices=EntityType.choices
    )
    entity_id = models.CharField('エンティティID', max_length=100)
    entity_name = models.CharField('エンティティ名', max_length=200, blank=True)

    # 操作種別
    action_type = models.CharField(
        '操作種別',
        max_length=30,
        choices=ActionType.choices
    )
    action_detail = models.CharField('操作詳細', max_length=500)

    # 変更データ
    before_data = models.JSONField('変更前データ', null=True, blank=True)
    after_data = models.JSONField('変更後データ', null=True, blank=True)
    changed_fields = models.JSONField(
        '変更フィールド',
        null=True,
        blank=True,
        help_text='変更されたフィールド名のリスト'
    )

    # 関連エンティティ（検索用）
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs',
        verbose_name='関連生徒'
    )
    guardian = models.ForeignKey(
        'students.Guardian',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs',
        verbose_name='関連保護者'
    )
    contract = models.ForeignKey(
        'contracts.Contract',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs',
        verbose_name='関連契約'
    )

    # 操作者
    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs',
        verbose_name='操作者'
    )
    user_name = models.CharField('操作者名', max_length=100, blank=True)
    user_email = models.CharField('操作者メール', max_length=200, blank=True)

    # システム情報
    is_system_action = models.BooleanField('システム操作', default=False)
    ip_address = models.GenericIPAddressField('IPアドレス', null=True, blank=True)
    user_agent = models.TextField('ユーザーエージェント', blank=True)
    request_path = models.CharField('リクエストパス', max_length=500, blank=True)
    request_method = models.CharField('リクエストメソッド', max_length=10, blank=True)

    # 結果
    is_success = models.BooleanField('成功', default=True)
    error_message = models.TextField('エラーメッセージ', blank=True)

    notes = models.TextField('備考', blank=True)

    class Meta:
        db_table = 'system_audit_logs'
        verbose_name = 'システム監査ログ'
        verbose_name_plural = 'システム監査ログ'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['action_type']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['student']),
            models.Index(fields=['guardian']),
            models.Index(fields=['contract']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"[{self.entity_type}] {self.action_detail} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    @classmethod
    def log(cls, tenant_id, entity_type, entity_id, action_type, action_detail,
            user=None, before_data=None, after_data=None, request=None, **kwargs):
        """監査ログを記録するヘルパーメソッド"""
        log_data = {
            'tenant_id': tenant_id,
            'entity_type': entity_type,
            'entity_id': str(entity_id),
            'action_type': action_type,
            'action_detail': action_detail,
            'before_data': before_data,
            'after_data': after_data,
        }

        if user:
            log_data['user'] = user
            log_data['user_name'] = user.get_full_name() if hasattr(user, 'get_full_name') else str(user)
            log_data['user_email'] = getattr(user, 'email', '')

        if request:
            log_data['ip_address'] = cls._get_client_ip(request)
            log_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')[:500]
            log_data['request_path'] = request.path[:500]
            log_data['request_method'] = request.method

        log_data.update(kwargs)
        return cls.objects.create(**log_data)

    @staticmethod
    def _get_client_ip(request):
        """クライアントIPアドレスを取得"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
