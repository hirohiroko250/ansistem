"""
Task auto-creation signals
各イベント発生時にタスクを自動作成する
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Task


def create_task_for_event(
    tenant_id,
    task_type,
    title,
    description='',
    priority='normal',
    school=None,
    student=None,
    guardian=None,
    source_type='',
    source_id=None,
    metadata=None
):
    """汎用タスク作成ヘルパー"""
    return Task.objects.create(
        tenant_id=tenant_id,
        task_type=task_type,
        title=title,
        description=description,
        status='new',
        priority=priority,
        school=school,
        student=student,
        guardian=guardian,
        source_type=source_type,
        source_id=source_id,
        metadata=metadata or {}
    )


# =============================================================================
# 生徒登録時のタスク作成
# =============================================================================
@receiver(post_save, sender='students.Student')
def create_task_on_student_registration(sender, instance, created, **kwargs):
    """生徒が新規登録されたらタスクを作成"""
    if created:
        create_task_for_event(
            tenant_id=instance.tenant_id,
            task_type='student_registration',
            title=f'生徒登録: {instance.last_name}{instance.first_name}',
            description=f'新しい生徒が登録されました',
            student=instance,
            guardian=instance.guardian if hasattr(instance, 'guardian') else None,
            source_type='student',
            source_id=instance.id,
        )


# =============================================================================
# 保護者登録時のタスク作成
# =============================================================================
@receiver(post_save, sender='students.Guardian')
def create_task_on_guardian_registration(sender, instance, created, **kwargs):
    """保護者が新規登録されたらタスクを作成"""
    if created:
        create_task_for_event(
            tenant_id=instance.tenant_id,
            task_type='guardian_registration',
            title=f'保護者登録: {instance.last_name}{instance.first_name}',
            description=f'新しい保護者が登録されました',
            guardian=instance,
            source_type='guardian',
            source_id=instance.id,
        )


# =============================================================================
# チャットメッセージ受信時のタスク作成
# =============================================================================
@receiver(post_save, sender='communications.Message')
def create_task_on_chat_message(sender, instance, created, **kwargs):
    """保護者からのチャットメッセージでタスクを作成"""
    if not created:
        return

    # 保護者からのメッセージのみ対象（sender_typeで判定）
    if getattr(instance, 'sender_type', '') != 'guardian':
        return

    # 同じチャンネルで未完了のチャットタスクがあれば作成しない
    channel = getattr(instance, 'channel', None)
    if channel:
        existing = Task.objects.filter(
            source_type='channel',
            source_id=channel.id,
            task_type='chat',
            status__in=['new', 'in_progress', 'waiting']
        ).exists()
        if existing:
            return

    # チャンネルから保護者情報を取得
    guardian = None
    tenant_id = getattr(instance, 'tenant_id', None)
    if not tenant_id and channel:
        tenant_id = getattr(channel, 'tenant_id', None)

    create_task_for_event(
        tenant_id=tenant_id,
        task_type='chat',
        title=f'チャット対応',
        description=f'新しいチャットメッセージが届きました',
        guardian=guardian,
        source_type='channel',
        source_id=channel.id if channel else None,
    )


# =============================================================================
# 休会申請時のタスク作成
# =============================================================================
@receiver(post_save, sender='students.SuspensionRequest')
def create_task_on_suspension_request(sender, instance, created, **kwargs):
    """休会申請が作成されたらタスクを作成"""
    if not created:
        return

    student = getattr(instance, 'student', None)
    student_name = f'{student.last_name}{student.first_name}' if student else '不明'

    # 休会期間の説明を作成
    suspend_from = instance.suspend_from.strftime('%Y/%m/%d') if instance.suspend_from else '未定'
    suspend_until = instance.suspend_until.strftime('%Y/%m/%d') if instance.suspend_until else '未定'
    return_day = instance.return_day.strftime('%Y/%m/%d') if getattr(instance, 'return_day', None) else None

    description = f'休会期間: {suspend_from} 〜 {suspend_until}'
    if return_day:
        description += f'（復会予定日: {return_day}）'

    create_task_for_event(
        tenant_id=instance.tenant_id,
        task_type='suspension',
        title=f'休会申請: {student_name}',
        description=description,
        priority='high',
        student=student,
        guardian=getattr(instance, 'guardian', None),
        school=getattr(student, 'school', None) if student else None,
        source_type='suspension_request',
        source_id=instance.id,
        metadata={
            'suspend_from': str(instance.suspend_from) if instance.suspend_from else None,
            'suspend_until': str(instance.suspend_until) if instance.suspend_until else None,
            'return_day': str(instance.return_day) if getattr(instance, 'return_day', None) else None,
            'keep_seat': instance.keep_seat,
        }
    )


# =============================================================================
# 退会申請時のタスク作成
# =============================================================================
@receiver(post_save, sender='students.WithdrawalRequest')
def create_task_on_withdrawal_request(sender, instance, created, **kwargs):
    """退会申請が作成されたらタスクを作成"""
    if not created:
        return

    student = getattr(instance, 'student', None)
    student_name = f'{student.last_name}{student.first_name}' if student else '不明'

    create_task_for_event(
        tenant_id=instance.tenant_id,
        task_type='withdrawal',
        title=f'退会申請: {student_name}',
        description=f'退会申請が提出されました',
        priority='high',
        student=student,
        guardian=getattr(instance, 'guardian', None),
        school=getattr(student, 'school', None) if student else None,
        source_type='withdrawal_request',
        source_id=instance.id,
    )


# =============================================================================
# 体験登録時のタスク作成
# =============================================================================
@receiver(post_save, sender='students.TrialBooking')
def create_task_on_trial_registration(sender, instance, created, **kwargs):
    """体験授業が登録されたらタスクを作成"""
    if not created:
        return

    student = getattr(instance, 'student', None)
    student_name = f'{student.last_name}{student.first_name}' if student else '不明'

    create_task_for_event(
        tenant_id=instance.tenant_id,
        task_type='trial_registration',
        title=f'体験登録: {student_name}',
        description=f'体験授業が登録されました',
        student=student,
        guardian=getattr(student, 'guardian', None) if student else None,
        school=getattr(instance, 'school', None),
        source_type='trial_booking',
        source_id=instance.id,
    )


# =============================================================================
# 入会申請時のタスク作成
# =============================================================================
@receiver(post_save, sender='contracts.StudentItem')
def create_task_on_enrollment(sender, instance, created, **kwargs):
    """契約（StudentItem）が作成されたらタスク作成"""
    if not created:
        return

    # 新規入会の場合のみ（status=active で is_trial=False）
    if getattr(instance, 'is_trial', False):
        return

    student = getattr(instance, 'student', None)
    if not student:
        return

    student_name = f'{student.last_name}{student.first_name}'

    # 同じ生徒の入会タスクが既にあれば作成しない（複数商品契約の場合）
    existing = Task.objects.filter(
        student=student,
        task_type='enrollment',
        status__in=['new', 'in_progress', 'waiting'],
        created_at__date=instance.created_at.date() if instance.created_at else None
    ).exists()
    if existing:
        return

    create_task_for_event(
        tenant_id=instance.tenant_id,
        task_type='enrollment',
        title=f'入会申請: {student_name}',
        description=f'新規入会申請が届きました',
        priority='high',
        student=student,
        guardian=getattr(student, 'guardian', None),
        school=getattr(instance, 'school', None),
        source_type='student_item',
        source_id=instance.id,
    )


# =============================================================================
# 引落失敗時のタスク作成
# =============================================================================
def create_debit_failure_task(invoice):
    """引落失敗タスクを作成（billing views.pyから呼び出し）"""
    guardian = getattr(invoice, 'guardian', None)
    guardian_name = f'{guardian.last_name}{guardian.first_name}' if guardian else '不明'

    return create_task_for_event(
        tenant_id=invoice.tenant_id,
        task_type='debit_failure',
        title=f'引落失敗: {guardian_name}様 {invoice.billing_month}',
        description=f'引落金額: ¥{invoice.balance_due:,.0f}',
        priority='urgent',
        guardian=guardian,
        source_type='invoice',
        source_id=invoice.id,
        metadata={
            'invoice_no': invoice.invoice_no,
            'billing_month': invoice.billing_month,
            'amount': float(invoice.balance_due),
        }
    )


# =============================================================================
# 返金申請時のタスク作成
# =============================================================================
@receiver(post_save, sender='billing.RefundRequest')
def create_task_on_refund_request(sender, instance, created, **kwargs):
    """返金申請が作成されたらタスクを作成"""
    if not created:
        return

    guardian = getattr(instance, 'guardian', None)
    guardian_name = f'{guardian.last_name}{guardian.first_name}' if guardian else '不明'
    amount = getattr(instance, 'amount', 0)

    create_task_for_event(
        tenant_id=instance.tenant_id,
        task_type='refund_request',
        title=f'返金申請: {guardian_name}様',
        description=f'返金金額: ¥{amount:,.0f}',
        priority='high',
        guardian=guardian,
        source_type='refund_request',
        source_id=instance.id,
        metadata={
            'amount': float(amount),
            'reason': getattr(instance, 'reason', ''),
        }
    )
