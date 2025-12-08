"""
Communications Services
ボットサービス、通知サービス等
"""
from django.utils import timezone
from .models import (
    Channel, ChannelMember, Message, BotConfig, BotFAQ, BotConversation, Notification
)


class BotService:
    """チャットボットサービス"""

    def __init__(self, tenant_id):
        self.tenant_id = tenant_id
        self.bot_config = self._get_bot_config()

    def _get_bot_config(self):
        """有効なボット設定を取得"""
        return BotConfig.objects.filter(
            tenant_id=self.tenant_id,
            is_active=True
        ).first()

    def get_response(self, message: str, channel_id=None, user=None):
        """メッセージに対する応答を生成"""
        if not self.bot_config:
            return {
                'response': 'ボットが設定されていません。',
                'matched_faq': None,
                'conversation_id': None
            }

        # チャンネル取得または作成
        channel = self._get_or_create_channel(channel_id, user)

        # FAQマッチング
        matched_faq = self._match_faq(message)

        if matched_faq:
            response_text = matched_faq.answer
            is_ai_response = False
        elif self.bot_config.ai_enabled:
            # AI応答（将来的にOpenAI等と連携）
            response_text = self._get_ai_response(message)
            is_ai_response = True
        else:
            response_text = self.bot_config.fallback_message
            is_ai_response = False

        # 会話ログ保存
        conversation = BotConversation.objects.create(
            tenant_id=self.tenant_id,
            channel=channel,
            bot_config=self.bot_config,
            user_input=message,
            bot_response=response_text,
            matched_faq=matched_faq,
            is_ai_response=is_ai_response
        )

        # メッセージとして保存
        if channel:
            # ユーザーメッセージ
            Message.objects.create(
                tenant_id=self.tenant_id,
                channel=channel,
                message_type=Message.MessageType.TEXT,
                sender=user,
                content=message
            )
            # ボット応答
            Message.objects.create(
                tenant_id=self.tenant_id,
                channel=channel,
                message_type=Message.MessageType.BOT,
                is_bot_message=True,
                content=response_text
            )

        return {
            'response': response_text,
            'matched_faq': {
                'id': str(matched_faq.id),
                'question': matched_faq.question,
                'category': matched_faq.category
            } if matched_faq else None,
            'conversation_id': str(conversation.id),
            'channel_id': str(channel.id) if channel else None,
            'next_action': matched_faq.next_action if matched_faq else None
        }

    def _get_or_create_channel(self, channel_id, user):
        """チャンネル取得または作成"""
        if channel_id:
            try:
                return Channel.objects.get(
                    id=channel_id,
                    tenant_id=self.tenant_id
                )
            except Channel.DoesNotExist:
                pass

        # 新規チャンネル作成
        channel = Channel.objects.create(
            tenant_id=self.tenant_id,
            channel_type=Channel.ChannelType.BOT,
            name=f"ボットチャット - {user.email if user else 'Guest'}"
        )

        if user:
            ChannelMember.objects.create(
                channel=channel,
                user=user,
                role=ChannelMember.Role.MEMBER
            )

        return channel

    def _match_faq(self, message: str):
        """FAQマッチング"""
        message_lower = message.lower()

        faqs = BotFAQ.objects.filter(
            tenant_id=self.tenant_id,
            bot_config=self.bot_config,
            is_active=True
        ).order_by('sort_order')

        best_match = None
        best_score = 0

        for faq in faqs:
            score = 0

            # キーワードマッチング
            for keyword in faq.keywords:
                if keyword.lower() in message_lower:
                    score += 10

            # 質問文との類似度（簡易版）
            question_words = faq.question.lower().split()
            for word in question_words:
                if len(word) > 2 and word in message_lower:
                    score += 5

            if score > best_score:
                best_score = score
                best_match = faq

        # 閾値以上のスコアがあればマッチ
        if best_score >= 10:
            return best_match

        return None

    def _get_ai_response(self, message: str):
        """AI応答を生成（将来的にOpenAI等と連携）"""
        # TODO: OpenAI API連携
        # import openai
        # response = openai.ChatCompletion.create(
        #     model=self.bot_config.ai_model,
        #     messages=[
        #         {"role": "system", "content": self.bot_config.ai_system_prompt},
        #         {"role": "user", "content": message}
        #     ]
        # )
        # return response.choices[0].message.content

        return self.bot_config.fallback_message

    def get_welcome_message(self):
        """ウェルカムメッセージを取得"""
        if self.bot_config:
            return self.bot_config.welcome_message
        return 'こんにちは！何かお手伝いできることはありますか？'

    def get_suggested_questions(self, category=None):
        """よくある質問を取得"""
        faqs = BotFAQ.objects.filter(
            tenant_id=self.tenant_id,
            bot_config=self.bot_config,
            is_active=True
        ).order_by('sort_order')

        if category:
            faqs = faqs.filter(category=category)

        return [
            {
                'id': str(faq.id),
                'question': faq.question,
                'category': faq.category
            }
            for faq in faqs[:10]
        ]


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
