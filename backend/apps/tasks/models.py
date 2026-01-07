"""Task management models."""
from django.db import models
from apps.core.models import TenantModel


class TaskCategory(TenantModel):
    """作業カテゴリ"""
    category_code = models.CharField('カテゴリコード', max_length=20)
    category_name = models.CharField('カテゴリ名', max_length=50)
    icon = models.CharField('アイコン', max_length=50, blank=True)
    color = models.CharField('カラー', max_length=20, blank=True)
    sort_order = models.IntegerField('並び順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'task_categories'
        verbose_name = '作業カテゴリ'
        verbose_name_plural = '作業カテゴリ'
        ordering = ['sort_order', 'category_code']
        unique_together = [['tenant_id', 'category_code']]

    def __str__(self):
        return self.category_name


class Task(TenantModel):
    """作業（タスク）"""
    TASK_TYPE_CHOICES = [
        # 問い合わせ系
        ('customer_inquiry', '客問い合わせ'),
        ('inquiry', '問い合わせ'),
        ('chat', 'チャット対応'),

        # 入会・退会・休会
        ('trial_registration', '体験登録'),
        ('enrollment', '入会申請'),
        ('withdrawal', '退会'),
        ('suspension', '休会'),

        # 契約・料金系
        ('contract_change', '契約変更'),
        ('tuition_operation', '授業料操作'),
        ('debit_failure', '引落失敗'),
        ('refund_request', '返金申請'),
        ('bank_account_request', '口座申請'),

        # イベント・紹介
        ('event_registration', 'イベント申し込み'),
        ('referral', '友人紹介'),

        # 登録系
        ('guardian_registration', '保護者登録'),
        ('student_registration', '生徒登録'),
        ('staff_registration', '社員登録'),

        # その他
        ('request', '依頼'),
        ('trouble', 'トラブル'),
        ('follow_up', 'フォローアップ'),
        ('other', 'その他'),
    ]

    STATUS_CHOICES = [
        ('new', '新規'),
        ('in_progress', '対応中'),
        ('waiting', '保留'),
        ('completed', '完了'),
        ('cancelled', 'キャンセル'),
    ]

    PRIORITY_CHOICES = [
        ('low', '低'),
        ('normal', '通常'),
        ('high', '高'),
        ('urgent', '緊急'),
    ]

    # 基本情報
    task_type = models.CharField('種別', max_length=50, choices=TASK_TYPE_CHOICES, default='inquiry')
    category = models.ForeignKey(
        TaskCategory, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='カテゴリ', related_name='tasks', db_column='category_id'
    )
    title = models.CharField('タイトル', max_length=200)
    description = models.TextField('説明', blank=True)
    status = models.CharField('ステータス', max_length=20, choices=STATUS_CHOICES, default='new')
    priority = models.CharField('優先度', max_length=10, choices=PRIORITY_CHOICES, default='normal')

    # 関連情報
    school = models.ForeignKey(
        'schools.School', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='校舎', related_name='tasks', db_column='school_id'
    )
    brand = models.ForeignKey(
        'schools.Brand', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='ブランド', related_name='tasks', db_column='brand_id'
    )
    student = models.ForeignKey(
        'students.Student', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='生徒', related_name='tasks', db_column='student_id'
    )
    guardian = models.ForeignKey(
        'students.Guardian', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='保護者', related_name='tasks', db_column='guardian_id'
    )

    # 担当・期限（UUIDフィールドとして扱う - t28_staffテーブルとの整合性のため）
    assigned_to_id = models.UUIDField('担当者ID', null=True, blank=True, db_column='assigned_to_id')
    created_by_id = models.UUIDField('作成者ID', null=True, blank=True, db_column='created_by_id')
    due_date = models.DateField('期限日', null=True, blank=True)
    completed_at = models.DateTimeField('完了日時', null=True, blank=True)

    # 参照元
    source_type = models.CharField('参照元種別', max_length=50, blank=True)
    source_id = models.UUIDField('参照元ID', null=True, blank=True)
    source_url = models.CharField('参照元URL', max_length=200, blank=True)

    # 追加情報
    metadata = models.JSONField('メタデータ', default=dict, blank=True)

    class Meta:
        db_table = 'tasks'
        verbose_name = '作業'
        verbose_name_plural = '作業一覧'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class TaskComment(TenantModel):
    """作業コメント（対応履歴）"""
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, verbose_name='作業', related_name='comments', db_column='task_id'
    )
    comment = models.TextField('コメント')
    commented_by_id = models.UUIDField('コメント者ID', null=True, blank=True, db_column='commented_by_id')
    is_internal = models.BooleanField('内部メモ', default=False, help_text='内部メモは顧客に表示されません')

    class Meta:
        db_table = 'task_comments'
        verbose_name = '作業コメント'
        verbose_name_plural = '作業コメント'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.task.title} - {self.created_at}'
