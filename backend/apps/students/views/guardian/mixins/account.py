"""
Account Actions Mixin - アカウント管理関連アクション
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response


class AccountActionsMixin:
    """アカウント管理関連アクション"""

    @action(detail=True, methods=['post'])
    def setup_account(self, request, pk=None):
        """保護者のログインアカウントを作成（パスワードなし、電話番号ログイン用）"""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        guardian = self.get_object()

        # 既にアカウントがある場合
        if guardian.user:
            return Response({
                'message': 'この保護者には既にアカウントが設定されています',
                'email': guardian.user.email,
                'phone': guardian.phone_mobile or guardian.phone,
                'already_exists': True,
            })

        # 電話番号またはメールアドレスが必要
        phone = guardian.phone_mobile or guardian.phone
        if not guardian.email and not phone:
            return Response(
                {'error': '電話番号またはメールアドレスが設定されていません。'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # メールアドレスを決定（ない場合は電話番号ベースで生成）
        if guardian.email:
            email = guardian.email
        else:
            # 電話番号をベースに仮のメールアドレスを生成
            normalized_phone = phone.replace('-', '').replace(' ', '').replace('　', '')
            email = f"{normalized_phone}@phone.guardian.local"

        # 既存のユーザーをメールで検索
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            # 既存ユーザーを保護者に紐付ける
            guardian.user = existing_user
            guardian.save(update_fields=['user'])
            return Response({
                'message': '既存のアカウントを保護者に紐付けました',
                'email': email,
                'phone': phone,
                'existing_account': True,
            })

        # ユーザー作成（パスワードなし = 代理ログイン用）
        try:
            user = User.objects.create_user(
                email=email,
                password=None,
                first_name=guardian.first_name or '',
                last_name=guardian.last_name or '',
                user_type='GUARDIAN',  # 大文字
                tenant_id=guardian.tenant_id,
                phone=phone,
            )
            # パスワードを無効化
            user.set_unusable_password()
            user.save()

            # 保護者にユーザーを紐付ける
            guardian.user = user
            guardian.save(update_fields=['user'])

            return Response({
                'message': 'アカウントを作成しました（パスワード未設定）',
                'email': email,
                'phone': phone,
                'user_id': str(user.id),
            })

        except Exception as e:
            return Response(
                {'error': f'アカウント作成に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
