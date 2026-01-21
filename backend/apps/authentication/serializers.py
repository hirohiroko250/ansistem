"""
Authentication Serializers
"""
from django.db import models
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from apps.users.models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """カスタムJWTトークン取得シリアライザー"""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # カスタムクレームを追加
        token['email'] = user.email
        token['user_type'] = user.user_type
        token['role'] = user.role
        token['full_name'] = user.full_name

        if user.tenant_id:
            token['tenant_id'] = str(user.tenant_id)
        if user.primary_school_id:
            token['primary_school_id'] = str(user.primary_school_id)
        if user.primary_brand_id:
            token['primary_brand_id'] = str(user.primary_brand_id)

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # アカウントロックチェック
        if self.user.is_locked():
            raise serializers.ValidationError(
                'アカウントがロックされています。しばらくしてから再度お試しください。'
            )

        # ログイン成功時にリセット
        self.user.reset_failed_login()

        # ユーザー情報を追加
        data['user'] = {
            'id': str(self.user.id),
            'email': self.user.email,
            'phone': self.user.phone,
            'full_name': self.user.full_name,
            'user_type': self.user.user_type,
            'role': self.user.role,
            'tenant_id': str(self.user.tenant_id) if self.user.tenant_id else None,
            'primary_school_id': str(self.user.primary_school_id) if self.user.primary_school_id else None,
            'must_change_password': self.user.must_change_password,
        }

        return data


class RegisterSerializer(serializers.Serializer):
    """ユーザー登録シリアライザー（フロントエンド対応版）

    ユーザー登録と同時にGuardian（保護者）レコードも作成
    """

    # 必須フィールド
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    # 名前（フロントエンドは fullName / fullNameKana で送信）
    full_name = serializers.CharField(required=False, allow_blank=True)
    full_name_kana = serializers.CharField(required=False, allow_blank=True)

    # 個別名前フィールド（従来API互換）
    last_name = serializers.CharField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name_kana = serializers.CharField(required=False, allow_blank=True)
    first_name_kana = serializers.CharField(required=False, allow_blank=True)

    # 連絡先
    phone = serializers.CharField(required=False, allow_blank=True)

    # 住所
    postal_code = serializers.CharField(required=False, allow_blank=True)
    prefecture = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    address1 = serializers.CharField(required=False, allow_blank=True)
    address2 = serializers.CharField(required=False, allow_blank=True)

    # 登録時追加情報（保護者向け）
    nearest_school_id = serializers.UUIDField(required=False, allow_null=True)
    interested_brands = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    referral_source = serializers.CharField(required=False, allow_blank=True)
    expectations = serializers.CharField(required=False, allow_blank=True)

    # その他
    tenant_code = serializers.CharField(write_only=True, required=False)
    user_type = serializers.ChoiceField(
        choices=User.UserType.choices,
        default=User.UserType.GUARDIAN
    )

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('このメールアドレスは既に登録されています')
        return value

    def validate_phone(self, value):
        """電話番号の重複チェック"""
        if not value:
            return value

        from apps.students.models import Guardian

        # 電話番号を正規化（ハイフン除去）
        normalized_phone = value.replace('-', '').replace(' ', '')

        # 同じ電話番号の保護者を検索
        existing_guardian = Guardian.objects.filter(
            models.Q(phone_mobile__icontains=normalized_phone) |
            models.Q(phone__icontains=normalized_phone)
        ).exclude(email='').first()

        if existing_guardian:
            # 既存のメールアドレスをマスク表示（先頭3文字 + *** + @ドメイン）
            email = existing_guardian.email
            if email and '@' in email:
                local, domain = email.split('@', 1)
                masked_email = f"{local[:3]}***@{domain}" if len(local) > 3 else f"{local[0]}***@{domain}"
            else:
                masked_email = "登録済みのメールアドレス"

            raise serializers.ValidationError(
                f'この電話番号は既に登録されています。登録済みのメールアドレス: {masked_email}'
            )

        return value

    def validate(self, data):
        # fullName から last_name / first_name を分割
        full_name = data.get('full_name', '')
        if full_name and not (data.get('last_name') and data.get('first_name')):
            parts = full_name.strip().split(' ', 1)
            data['last_name'] = parts[0] if len(parts) > 0 else ''
            data['first_name'] = parts[1] if len(parts) > 1 else ''

        # fullNameKana から last_name_kana / first_name_kana を分割
        full_name_kana = data.get('full_name_kana', '')
        if full_name_kana and not (data.get('last_name_kana') and data.get('first_name_kana')):
            parts = full_name_kana.strip().split(' ', 1)
            data['last_name_kana'] = parts[0] if len(parts) > 0 else ''
            data['first_name_kana'] = parts[1] if len(parts) > 1 else ''

        # 名前の必須チェック
        if not data.get('last_name') or not data.get('first_name'):
            raise serializers.ValidationError({'full_name': '氏名は必須です'})

        return data

    def create(self, validated_data):
        from django.db import transaction
        from apps.students.models import Guardian

        # 不要なフィールドを除去
        validated_data.pop('full_name', None)
        validated_data.pop('full_name_kana', None)
        tenant_code = validated_data.pop('tenant_code', None)

        # テナント設定（指定がない場合はデフォルトテナントを使用）
        from apps.tenants.models import Tenant
        tenant_id = None
        tenant = None
        if tenant_code:
            try:
                tenant = Tenant.objects.get(tenant_code=tenant_code, is_active=True)
            except Tenant.DoesNotExist:
                raise serializers.ValidationError({'tenant_code': '無効なテナントコードです'})
        else:
            # デフォルトテナントを使用
            tenant = Tenant.objects.filter(is_active=True).first()
            if not tenant:
                raise serializers.ValidationError({'tenant_code': 'テナントが設定されていません'})

        tenant_id = tenant.id
        validated_data['tenant_id'] = tenant_id

        password = validated_data.pop('password')

        # Guardian用のデータを分離
        guardian_fields = {
            'last_name': validated_data.get('last_name', ''),
            'first_name': validated_data.get('first_name', ''),
            'last_name_kana': validated_data.get('last_name_kana') or '',
            'first_name_kana': validated_data.get('first_name_kana') or '',
            'email': validated_data.get('email', ''),
            'phone_mobile': validated_data.get('phone') or '',
            # 住所
            'postal_code': validated_data.get('postal_code') or '',
            'prefecture': validated_data.get('prefecture') or '',
            'city': validated_data.get('city') or '',
            'address1': validated_data.get('address1') or '',
            'address2': validated_data.get('address2') or '',
            # 登録時追加情報
            'nearest_school_id': validated_data.get('nearest_school_id'),
            'interested_brands': validated_data.get('interested_brands') or [],
            'referral_source': validated_data.get('referral_source') or '',
            'expectations': validated_data.get('expectations') or '',
        }

        # User モデルに存在しないフィールドを除去
        guardian_only_fields = ['postal_code', 'prefecture', 'city', 'address1', 'address2',
                                'phone', 'nearest_school_id', 'interested_brands', 'referral_source', 'expectations']
        for field in guardian_only_fields:
            validated_data.pop(field, None)

        with transaction.atomic():
            # 1. ユーザー作成（User モデルのフィールドのみ）
            user = User(**validated_data)
            user.set_password(password)
            user.save()

            # 2. 保護者（Guardian）作成
            guardian = Guardian(
                tenant_id=tenant_id,
                **guardian_fields
            )
            guardian.user = user
            guardian.save()
            # タスクはsignalsで自動作成される

        return user


class LoginSerializer(serializers.Serializer):
    """ログインシリアライザー"""
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()

        if not email and not phone:
            raise serializers.ValidationError('メールアドレスまたは電話番号を入力してください')

        return data


class LogoutSerializer(serializers.Serializer):
    """ログアウトシリアライザー"""
    refresh = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    """パスワードリセットリクエスト"""
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value, is_active=True).exists():
            # セキュリティのためエラーは返さない
            pass
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """パスワードリセット確認"""
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)
    new_password_confirm = serializers.CharField()

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'パスワードが一致しません'})
        return data


class PasswordChangeSerializer(serializers.Serializer):
    """パスワード変更シリアライザー（初回ログイン時の強制変更用）"""
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context.get('request').user
        if not user.check_password(value):
            raise serializers.ValidationError('現在のパスワードが正しくありません')
        return value

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'パスワードが一致しません'})

        # 新しいパスワードが現在のパスワードと同じでないことを確認
        if data['current_password'] == data['new_password']:
            raise serializers.ValidationError({'new_password': '新しいパスワードは現在のパスワードと異なる必要があります'})

        return data

    def save(self, **kwargs):
        user = self.context.get('request').user
        user.set_password(self.validated_data['new_password'])
        user.must_change_password = False
        user.save(update_fields=['password', 'must_change_password', 'updated_at'])
        return user


class EmployeeRegisterSerializer(serializers.Serializer):
    """社員登録シリアライザー（認証不要の公開API用）"""

    # 必須フィールド
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    last_name = serializers.CharField()
    first_name = serializers.CharField()
    tenant_id = serializers.UUIDField()

    # 任意フィールド
    phone = serializers.CharField(required=False, allow_blank=True)
    department = serializers.CharField(required=False, allow_blank=True)
    position_id = serializers.UUIDField(required=False, allow_null=True)
    position_text = serializers.CharField(required=False, allow_blank=True)

    # 対応校舎・ブランド
    school_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list
    )
    brand_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list
    )

    # 雇用情報
    hire_date = serializers.DateField(required=False, allow_null=True)
    birth_date = serializers.DateField(required=False, allow_null=True)

    # 住所情報
    postal_code = serializers.CharField(required=False, allow_blank=True)
    prefecture = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    nationality = serializers.CharField(required=False, default='日本')

    # 通勤情報
    nearest_station = serializers.CharField(required=False, allow_blank=True)
    commuting_method = serializers.CharField(required=False, allow_blank=True)

    # 顔写真
    profile_image = serializers.ImageField(required=False, allow_null=True)

    def validate_email(self, value):
        # 既にSTAFFとして登録されている場合のみエラー
        # GUARDIANとして登録されている場合は、社員情報を追加できるようにする
        existing_user = User.objects.filter(email=value).first()
        if existing_user:
            if existing_user.user_type == User.UserType.STAFF:
                raise serializers.ValidationError('このメールアドレスは既に社員として登録されています')
            if existing_user.staff_id:
                raise serializers.ValidationError('このメールアドレスは既に社員情報が紐付けられています')
        return value

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'パスワードが一致しません'})

        # テナントの存在確認
        from apps.tenants.models import Tenant
        try:
            Tenant.objects.get(id=data['tenant_id'], is_active=True)
        except Tenant.DoesNotExist:
            raise serializers.ValidationError({'tenant_id': '無効な会社IDです'})

        return data

    def create(self, validated_data):
        from django.db import transaction
        from apps.tenants.models import Employee, Position
        from apps.schools.models import School, Brand

        # 除外するフィールド
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        tenant_id = validated_data.pop('tenant_id')
        school_ids = validated_data.pop('school_ids', [])
        brand_ids = validated_data.pop('brand_ids', [])
        position_id = validated_data.pop('position_id', None)

        # Employee用のデータ
        employee_data = {
            'last_name': validated_data.get('last_name', ''),
            'first_name': validated_data.get('first_name', ''),
            'email': validated_data.get('email', ''),
            'phone': validated_data.get('phone', ''),
            'department': validated_data.get('department', ''),
            'position_text': validated_data.get('position_text', ''),
            'hire_date': validated_data.get('hire_date'),
            'birth_date': validated_data.get('birth_date'),
            'postal_code': validated_data.get('postal_code', ''),
            'prefecture': validated_data.get('prefecture', ''),
            'city': validated_data.get('city', ''),
            'address': validated_data.get('address', ''),
            'nationality': validated_data.get('nationality', '日本'),
            'nearest_station': validated_data.get('nearest_station', ''),
            'commuting_method': validated_data.get('commuting_method', ''),
            'is_active': False,  # 管理者の承認待ち
        }

        # プロフィール画像の処理（アップロードされている場合）
        profile_image = validated_data.get('profile_image')
        # TODO: 画像ストレージへの保存処理を実装

        with transaction.atomic():
            # 1. 社員（Employee）作成
            employee = Employee(tenant_ref_id=tenant_id, **employee_data)

            # 役職を設定
            if position_id:
                try:
                    position = Position.objects.get(id=position_id, tenant_ref_id=tenant_id)
                    employee.position = position
                except Position.DoesNotExist:
                    pass

            employee.save()

            # 対応校舎を設定
            if school_ids:
                schools = School.objects.filter(id__in=school_ids)
                employee.schools.set(schools)

            # 対応ブランドを設定
            if brand_ids:
                brands = Brand.objects.filter(id__in=brand_ids)
                employee.brands.set(brands)

            # 2. ユーザー（User）作成または更新
            existing_user = User.objects.filter(email=validated_data['email']).first()

            if existing_user:
                # 既存ユーザー（GUARDIAN等）に社員情報を追加
                # user_typeは変更しない（保護者のまま社員情報も持てる）
                existing_user.staff_id = employee.id
                if not existing_user.tenant_id:
                    existing_user.tenant_id = tenant_id
                # パスワードは更新しない（既存のパスワードを維持）
                existing_user.save()
                user = existing_user
            else:
                # 新規ユーザー作成 - 承認待ちで無効化
                user = User(
                    email=validated_data['email'],
                    last_name=validated_data['last_name'],
                    first_name=validated_data['first_name'],
                    phone=validated_data.get('phone', ''),
                    user_type=User.UserType.STAFF,
                    role=User.Role.USER,  # 社員はUSERロールで登録
                    tenant_id=tenant_id,
                    staff_id=employee.id,
                    is_active=False,  # 管理者の承認待ち
                    must_change_password=False,
                )
                user.set_password(password)
                user.save()

        return user
