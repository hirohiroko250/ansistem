"""
Authentication Views
"""
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils import timezone

from .serializers import (
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    EmployeeRegisterSerializer,
    LogoutSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    PasswordChangeSerializer,
)
from .services import PasswordResetService, EmailService

User = get_user_model()


class LoginView(TokenObtainPairView):
    """ログインビュー（電話番号またはメールアドレスでログイン）"""
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # 電話番号でのログインをサポート
        data = request.data.copy()
        phone = data.get('phone', '').strip()
        email = data.get('email', '').strip()

        # 電話番号が指定されている場合、対応するメールアドレスを検索
        if phone and not email:
            from apps.students.models import Guardian
            # 電話番号の正規化（ハイフン除去）
            normalized_phone = phone.replace('-', '').replace(' ', '').replace('　', '')

            # Guardianから電話番号でユーザーを検索
            guardian = Guardian.objects.filter(
                phone_mobile=normalized_phone
            ).first()

            if not guardian:
                guardian = Guardian.objects.filter(
                    phone_mobile=phone
                ).first()

            if not guardian:
                guardian = Guardian.objects.filter(
                    phone=normalized_phone
                ).first()

            if not guardian:
                guardian = Guardian.objects.filter(
                    phone=phone
                ).first()

            if guardian and guardian.user_id:
                try:
                    data['email'] = guardian.user.email
                except User.DoesNotExist:
                    # user_idは存在するがUserが見つからない場合
                    if guardian.email:
                        data['email'] = guardian.email
                    else:
                        return Response(
                            {'detail': 'ユーザーアカウントが見つかりません'},
                            status=status.HTTP_401_UNAUTHORIZED
                        )
            elif guardian and guardian.email:
                # Guardian に紐づくユーザーがいなくても、emailがあればそれを使う
                data['email'] = guardian.email
            else:
                return Response(
                    {'detail': 'この電話番号は登録されていません'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        # username フィールドを email に設定（SimpleJWTの要求）
        if 'email' in data:
            data['username'] = data['email']

        serializer = self.get_serializer(data=data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            # ログイン失敗時の処理
            identifier = data.get('email') or phone
            if identifier:
                try:
                    user = User.objects.get(email=identifier)
                    user.increment_failed_login()
                except User.DoesNotExist:
                    pass
            raise

        # 最終ログイン日時を更新
        user = serializer.user
        try:
            # 直接クエリで更新（update_fieldsの問題を回避）
            User.objects.filter(pk=user.pk).update(last_login_at=timezone.now())
        except Exception:
            pass  # 更新失敗しても続行

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class RegisterView(GenericAPIView):
    """ユーザー登録ビュー"""
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # トークン生成
        refresh = RefreshToken.for_user(user)

        return Response({
            'message': 'ユーザー登録が完了しました',
            'user': {
                'id': str(user.id),
                'email': user.email,
                'full_name': user.full_name,
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class LogoutView(GenericAPIView):
    """ログアウトビュー"""
    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            refresh_token = serializer.validated_data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass

        return Response({'message': 'ログアウトしました'}, status=status.HTTP_200_OK)


class TokenRefreshAPIView(TokenRefreshView):
    """トークンリフレッシュビュー"""
    permission_classes = [AllowAny]


class PasswordResetRequestView(GenericAPIView):
    """パスワードリセットリクエストビュー"""
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email, is_active=True)
            # サービスを使用してトークン生成・メール送信
            password_service = PasswordResetService(user)
            token = password_service.generate_reset_token()

            email_service = EmailService()
            email_service.send_password_reset_email(user.email, token)

        except User.DoesNotExist:
            pass  # セキュリティのため、存在しないユーザーでも同じレスポンス

        return Response({
            'message': 'パスワードリセット用のメールを送信しました（登録されているメールアドレスの場合）'
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(GenericAPIView):
    """パスワードリセット確認ビュー"""
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        password_service = PasswordResetService()
        try:
            password_service.reset_password(token, new_password)
            return Response({
                'message': 'パスワードが正常に変更されました'
            }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class PasswordChangeView(GenericAPIView):
    """パスワード変更ビュー（初回ログイン時の強制変更用）"""
    serializer_class = PasswordChangeSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # 新しいトークンを発行
        refresh = RefreshToken.for_user(user)

        return Response({
            'message': 'パスワードが正常に変更されました',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': str(user.id),
                'email': user.email,
                'phone': user.phone,
                'full_name': user.full_name,
                'user_type': user.user_type,
                'role': user.role,
                'must_change_password': user.must_change_password,
            }
        }, status=status.HTTP_200_OK)


class CheckEmailView(GenericAPIView):
    """メールアドレス重複チェックビュー"""
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()

        if not email:
            return Response({
                'available': False,
                'message': 'メールアドレスを入力してください'
            }, status=status.HTTP_400_BAD_REQUEST)

        exists = User.objects.filter(email=email).exists()

        if exists:
            return Response({
                'available': False,
                'message': 'このメールアドレスは既に登録されています'
            })
        else:
            return Response({
                'available': True,
                'message': '使用可能なメールアドレスです'
            })


class CheckPhoneView(GenericAPIView):
    """電話番号重複チェックビュー"""
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get('phone', '').strip()

        if not phone:
            return Response({
                'available': False,
                'message': '電話番号を入力してください'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 電話番号の正規化（ハイフンや空白を削除）
        normalized_phone = phone.replace('-', '').replace(' ', '').replace('　', '')

        # 正規化した電話番号と元の電話番号の両方でチェック
        exists = User.objects.filter(phone=phone).exists()
        if not exists and normalized_phone != phone:
            exists = User.objects.filter(phone=normalized_phone).exists()

        if exists:
            return Response({
                'available': False,
                'message': 'この電話番号は既に登録されています'
            })
        else:
            return Response({
                'available': True,
                'message': '使用可能な電話番号です'
            })


class MeView(GenericAPIView):
    """現在のユーザー情報取得・更新ビュー"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {
            'id': str(user.id),
            'email': user.email,
            'full_name': user.full_name,
            'user_type': user.user_type,
            'role': user.role,
            'tenant_id': str(user.tenant_id) if user.tenant_id else None,
            'primary_school_id': str(user.primary_school_id) if user.primary_school_id else None,
            'primary_brand_id': str(user.primary_brand_id) if user.primary_brand_id else None,
            'permissions': user.permissions,
            'is_email_verified': user.is_email_verified,
        }

        # Guardian情報を取得（保護者ユーザーの場合）
        if hasattr(user, 'guardian_profile') and user.guardian_profile:
            guardian = user.guardian_profile
            data.update({
                'lastName': guardian.last_name,
                'firstName': guardian.first_name,
                'lastNameKana': guardian.last_name_kana or '',
                'firstNameKana': guardian.first_name_kana or '',
                'phoneNumber': guardian.phone_mobile or guardian.phone or '',
                'postalCode': guardian.postal_code or '',
                'prefecture': guardian.prefecture or '',
                'city': guardian.city or '',
                'address1': guardian.address1 or '',
                'address2': guardian.address2 or '',
                'nearestSchoolId': str(guardian.nearest_school_id) if guardian.nearest_school_id else None,
                'nearestSchoolName': guardian.nearest_school.school_name if guardian.nearest_school else None,
                'interestedBrands': guardian.interested_brands or [],
                'referralSource': guardian.referral_source or '',
                'expectations': guardian.expectations or '',
            })
        else:
            # Userモデルから名前を分割
            full_name = user.full_name or ''
            parts = full_name.split(' ', 1)
            data.update({
                'lastName': parts[0] if parts else '',
                'firstName': parts[1] if len(parts) > 1 else '',
                'lastNameKana': '',
                'firstNameKana': '',
                'phoneNumber': '',
                'postalCode': '',
                'prefecture': '',
                'city': '',
                'address1': '',
                'address2': '',
                'nearestSchoolId': None,
                'nearestSchoolName': None,
                'interestedBrands': [],
                'referralSource': '',
                'expectations': '',
            })

        return Response(data)

    def patch(self, request):
        """プロフィール更新"""
        user = request.user
        data = request.data

        # Guardian情報を更新
        if hasattr(user, 'guardian_profile') and user.guardian_profile:
            guardian = user.guardian_profile

            # 更新可能フィールド
            if 'lastName' in data:
                guardian.last_name = data['lastName']
            if 'firstName' in data:
                guardian.first_name = data['firstName']
            if 'lastNameKana' in data:
                guardian.last_name_kana = data['lastNameKana']
            if 'firstNameKana' in data:
                guardian.first_name_kana = data['firstNameKana']
            if 'phoneNumber' in data:
                guardian.phone_mobile = data['phoneNumber']
            if 'postalCode' in data:
                guardian.postal_code = data['postalCode']
            if 'prefecture' in data:
                guardian.prefecture = data['prefecture']
            if 'city' in data:
                guardian.city = data['city']
            if 'address1' in data:
                guardian.address1 = data['address1']
            if 'address2' in data:
                guardian.address2 = data['address2']

            guardian.save()

            # Userのfull_nameも更新
            user.first_name = guardian.first_name
            user.last_name = guardian.last_name
            user.save(update_fields=['first_name', 'last_name'])

        return self.get(request)


class ImpersonateGuardianView(GenericAPIView):
    """管理者が保護者としてログインするためのトークン生成"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.students.models import Guardian

        # 管理者権限チェック
        if not request.user.is_staff and not request.user.is_superuser:
            return Response(
                {'error': '管理者権限が必要です'},
                status=status.HTTP_403_FORBIDDEN
            )

        guardian_id = request.data.get('guardian_id')
        if not guardian_id:
            return Response(
                {'error': 'guardian_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            guardian = Guardian.objects.get(id=guardian_id, deleted_at__isnull=True)
        except Guardian.DoesNotExist:
            return Response(
                {'error': '保護者が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 保護者に紐づくユーザーを取得
        if not guardian.user:
            return Response(
                {'error': 'この保護者にはログインアカウントがありません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = guardian.user

        # トークン生成
        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'guardian': {
                'id': str(guardian.id),
                'name': f"{guardian.last_name} {guardian.first_name}",
            }
        }, status=status.HTTP_200_OK)


class EmployeeRegisterView(GenericAPIView):
    """社員登録ビュー（認証不要の公開API）"""
    serializer_class = EmployeeRegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response({
            'message': '社員登録が完了しました。管理者の承認後、ログインが可能になります。',
            'user': {
                'id': str(user.id),
                'email': user.email,
                'full_name': user.full_name,
            }
        }, status=status.HTTP_201_CREATED)
