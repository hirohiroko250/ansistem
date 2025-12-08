"""
User Serializers
"""
from rest_framework import serializers
from .models import User


class UserSummarySerializer(serializers.ModelSerializer):
    """ユーザーサマリー（一覧表示用）"""
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'user_type', 'role', 'is_active']


class UserDetailSerializer(serializers.ModelSerializer):
    """ユーザー詳細"""
    full_name = serializers.CharField(read_only=True)
    full_name_kana = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'user_type', 'user_no',
            'last_name', 'first_name', 'last_name_kana', 'first_name_kana',
            'full_name', 'full_name_kana', 'display_name',
            'phone', 'line_id', 'profile_image_url',
            'birth_date', 'gender',
            'primary_school_id', 'primary_brand_id',
            'role', 'is_active', 'is_email_verified',
            'last_login_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_login_at']


class UserCreateSerializer(serializers.ModelSerializer):
    """ユーザー作成"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm',
            'last_name', 'first_name', 'last_name_kana', 'first_name_kana',
            'user_type', 'phone',
        ]

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'パスワードが一致しません'})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """ユーザー更新"""

    class Meta:
        model = User
        fields = [
            'last_name', 'first_name', 'last_name_kana', 'first_name_kana',
            'display_name', 'phone', 'line_id', 'profile_image_url',
            'birth_date', 'gender',
        ]


class PasswordChangeSerializer(serializers.Serializer):
    """パスワード変更"""
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': '新しいパスワードが一致しません'})
        return data


class ProfileSerializer(serializers.ModelSerializer):
    """自分のプロフィール"""
    full_name = serializers.CharField(read_only=True)
    child_accounts = serializers.SerializerMethodField()
    is_parent_account = serializers.BooleanField(read_only=True)
    is_child_account = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'user_type', 'role',
            'last_name', 'first_name', 'full_name', 'display_name',
            'phone', 'profile_image_url',
            'primary_school_id', 'primary_brand_id',
            'tenant_id', 'is_email_verified',
            'parent_user', 'is_parent_account', 'is_child_account', 'child_accounts',
        ]
        read_only_fields = ['id', 'email', 'tenant_id', 'user_type', 'role', 'parent_user']

    def get_child_accounts(self, obj):
        children = obj.get_children()
        return ChildAccountSerializer(children, many=True).data


class ChildAccountSerializer(serializers.ModelSerializer):
    """子アカウント（簡易表示）"""
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'user_type', 'full_name', 'display_name',
            'profile_image_url', 'is_active'
        ]


class ChildAccountCreateSerializer(serializers.ModelSerializer):
    """子アカウント作成（保護者が生徒アカウントを作成）"""
    password = serializers.CharField(write_only=True, min_length=8, required=False)

    class Meta:
        model = User
        fields = [
            'email', 'password',
            'last_name', 'first_name', 'last_name_kana', 'first_name_kana',
            'display_name', 'phone', 'birth_date', 'gender',
            'profile_image_url',
        ]

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        request = self.context.get('request')

        # 親アカウントの情報を継承
        parent_user = request.user
        validated_data['tenant_id'] = parent_user.tenant_id
        validated_data['parent_user'] = parent_user
        validated_data['user_type'] = User.UserType.STUDENT
        validated_data['role'] = User.Role.USER

        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            # パスワード未設定の場合はランダム生成（後で変更必須）
            user.set_unusable_password()
        user.save()
        return user


class SwitchAccountSerializer(serializers.Serializer):
    """アカウント切り替え用"""
    target_user_id = serializers.UUIDField()
