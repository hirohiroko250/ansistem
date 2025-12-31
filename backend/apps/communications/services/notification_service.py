"""
Notification Service - 通知サービス
"""
from django.utils import timezone
from ..models import Message, Notification


class NotificationService:
    """通知サービス"""

    def __init__(self, tenant_id):
        self.tenant_id = tenant_id

    def create_notification(
        self,
        notification_type: str,
        title: str,
        content: str,
        user=None,
        guardian=None,
        link_type=None,
        link_id=None
    ):
        """通知を作成"""
        notification = Notification.objects.create(
            tenant_id=self.tenant_id,
            notification_type=notification_type,
            title=title,
            content=content,
            user=user,
            guardian=guardian,
            link_type=link_type,
            link_id=link_id
        )

        # TODO: プッシュ通知送信
        # self._send_push_notification(notification)

        return notification

    def create_bulk_notifications(
        self,
        notification_type: str,
        title: str,
        content: str,
        users=None,
        guardians=None,
        link_type=None,
        link_id=None
    ):
        """一括通知を作成"""
        notifications = []

        if users:
            for user in users:
                notification = Notification(
                    tenant_id=self.tenant_id,
                    notification_type=notification_type,
                    title=title,
                    content=content,
                    user=user,
                    link_type=link_type,
                    link_id=link_id
                )
                notifications.append(notification)

        if guardians:
            for guardian in guardians:
                notification = Notification(
                    tenant_id=self.tenant_id,
                    notification_type=notification_type,
                    title=title,
                    content=content,
                    guardian=guardian,
                    link_type=link_type,
                    link_id=link_id
                )
                notifications.append(notification)

        Notification.objects.bulk_create(notifications)
        return len(notifications)

    def notify_new_message(self, message: Message):
        """新着メッセージ通知"""
        channel = message.channel
        members = channel.members.exclude(user=message.sender).select_related('user', 'guardian')

        for member in members:
            if member.is_muted:
                continue

            self.create_notification(
                notification_type=Notification.NotificationType.MESSAGE,
                title=f"新着メッセージ: {channel.name}",
                content=f"{message.sender_name}: {message.content[:100]}...",
                user=member.user,
                guardian=member.guardian,
                link_type='channel',
                link_id=channel.id
            )

    def notify_lesson_reminder(self, schedule, hours_before=24):
        """授業リマインダー通知"""
        if schedule.student:
            self.create_notification(
                notification_type=Notification.NotificationType.LESSON_REMINDER,
                title="授業リマインダー",
                content=f"明日 {schedule.start_time.strftime('%H:%M')} から {schedule.subject.subject_name if schedule.subject else ''} の授業があります。",
                user=None,
                guardian=None,  # TODO: 生徒に紐づく保護者を取得
                link_type='schedule',
                link_id=schedule.id
            )

    def notify_makeup_request(self, makeup_lesson):
        """振替リクエスト通知"""
        # 管理者に通知
        # TODO: 適切な管理者を取得
        pass

    def notify_makeup_approved(self, makeup_lesson):
        """振替承認通知"""
        if makeup_lesson.student:
            # 保護者に通知
            guardians = makeup_lesson.student.guardian_relations.filter(
                is_active=True
            ).values_list('guardian', flat=True)

            from apps.students.models import Guardian
            for guardian in Guardian.objects.filter(id__in=guardians):
                self.create_notification(
                    notification_type=Notification.NotificationType.MAKEUP_APPROVED,
                    title="振替が承認されました",
                    content=f"{makeup_lesson.student.full_name}さんの振替が承認されました。",
                    guardian=guardian,
                    link_type='makeup',
                    link_id=makeup_lesson.id
                )
