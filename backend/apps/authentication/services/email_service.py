"""
Email Service - メール送信サービス
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """メール送信サービス

    認証関連のメール送信を一元管理
    """

    DEFAULT_FROM_EMAIL = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@example.com'

    def __init__(self, tenant_id=None):
        self.tenant_id = tenant_id

    def send_password_reset_email(self, email: str, token: str, reset_url: str = None) -> bool:
        """パスワードリセットメールを送信

        Args:
            email: 送信先メールアドレス
            token: リセットトークン
            reset_url: リセットURL（オプション）

        Returns:
            成功した場合 True
        """
        if not reset_url:
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            reset_url = f"{frontend_url}/reset-password?token={token}"

        subject = 'パスワードリセットのご案内'
        message = f"""
パスワードリセットのリクエストを受け付けました。

以下のリンクからパスワードを再設定してください：
{reset_url}

このリンクは1時間有効です。

心当たりがない場合は、このメールを無視してください。
"""

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=self.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            logger.info(f"Password reset email sent to {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {e}")
            return False

    def send_welcome_email(self, email: str, full_name: str, temporary_password: str = None) -> bool:
        """ウェルカムメールを送信

        Args:
            email: 送信先メールアドレス
            full_name: ユーザー名
            temporary_password: 仮パスワード（オプション）

        Returns:
            成功した場合 True
        """
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        login_url = f"{frontend_url}/login"

        subject = 'アカウント登録完了のお知らせ'
        message = f"""
{full_name} 様

アカウントの登録が完了しました。

ログインURL: {login_url}
"""
        if temporary_password:
            message += f"""
仮パスワード: {temporary_password}

初回ログイン時にパスワードの変更が必要です。
"""

        message += """
ご不明な点がございましたら、お気軽にお問い合わせください。
"""

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=self.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            logger.info(f"Welcome email sent to {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send welcome email to {email}: {e}")
            return False

    def send_email_verification(self, email: str, token: str) -> bool:
        """メールアドレス確認メールを送信

        Args:
            email: 送信先メールアドレス
            token: 確認トークン

        Returns:
            成功した場合 True
        """
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        verify_url = f"{frontend_url}/verify-email?token={token}"

        subject = 'メールアドレスの確認'
        message = f"""
以下のリンクをクリックしてメールアドレスを確認してください：

{verify_url}

このリンクは24時間有効です。
"""

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=self.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            logger.info(f"Email verification sent to {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email verification to {email}: {e}")
            return False

    def send_login_notification(self, email: str, ip_address: str = None, user_agent: str = None) -> bool:
        """ログイン通知メールを送信

        Args:
            email: 送信先メールアドレス
            ip_address: ログイン元IPアドレス
            user_agent: ユーザーエージェント

        Returns:
            成功した場合 True
        """
        from django.utils import timezone

        subject = 'ログイン通知'
        message = f"""
新しいログインがありました。

日時: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        if ip_address:
            message += f"IPアドレス: {ip_address}\n"
        if user_agent:
            message += f"ブラウザ: {user_agent}\n"

        message += """
心当たりがない場合は、すぐにパスワードを変更してください。
"""

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=self.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            logger.info(f"Login notification sent to {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send login notification to {email}: {e}")
            return False
