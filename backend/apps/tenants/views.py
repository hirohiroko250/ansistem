"""
Tenants Views
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Tenant, Position, FeatureMaster, PositionPermission, Employee
from .serializers import (
    TenantSerializer, TenantDetailSerializer,
    PositionSerializer, FeatureMasterSerializer,
    PositionPermissionSerializer, BulkPermissionUpdateSerializer,
    EmployeeListSerializer, EmployeeDetailSerializer,
)


class TenantViewSet(viewsets.ReadOnlyModelViewSet):
    """テナント一覧・詳細API（読み取り専用）"""
    queryset = Tenant.objects.filter(is_active=True).order_by('tenant_code')
    serializer_class = TenantSerializer
    permission_classes = [permissions.AllowAny]  # テナント一覧は公開

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TenantDetailSerializer
        return TenantSerializer

    @action(detail=False, methods=['get'])
    def all(self, request):
        """全テナント一覧（active含む）"""
        queryset = Tenant.objects.all().order_by('tenant_code')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class PositionViewSet(viewsets.ModelViewSet):
    """役職ViewSet"""
    serializer_class = PositionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Position.objects.filter(
            tenant_ref=self.request.user.tenant_id
        ).order_by('-rank', 'position_name')

    def perform_create(self, serializer):
        serializer.save(tenant_ref=self.request.user.tenant_id)

    @action(detail=True, methods=['patch'])
    def update_global_permissions(self, request, pk=None):
        """グローバル権限（校舎制限等）を更新"""
        position = self.get_object()
        fields = [
            'school_restriction', 'brand_restriction',
            'bulk_email_restriction', 'email_approval_required', 'is_accounting'
        ]
        for field in fields:
            if field in request.data:
                setattr(position, field, request.data[field])
        position.save()
        return Response(PositionSerializer(position).data)


class FeatureMasterViewSet(viewsets.ModelViewSet):
    """機能マスタViewSet"""
    serializer_class = FeatureMasterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FeatureMaster.objects.filter(
            tenant_ref=self.request.user.tenant_id
        ).order_by('display_order', 'feature_code')

    def perform_create(self, serializer):
        serializer.save(tenant_ref=self.request.user.tenant_id)


class PositionPermissionViewSet(viewsets.ModelViewSet):
    """役職権限ViewSet"""
    serializer_class = PositionPermissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PositionPermission.objects.filter(
            tenant_ref=self.request.user.tenant_id
        ).select_related('position', 'feature').order_by(
            '-position__rank', 'feature__display_order'
        )

    def perform_create(self, serializer):
        serializer.save(tenant_ref=self.request.user.tenant_id)

    @action(detail=False, methods=['get'])
    def matrix(self, request):
        """権限マトリックスを取得"""
        tenant_id = request.user.tenant_id

        # 役職一覧
        positions = Position.objects.filter(
            tenant_ref=tenant_id, is_active=True
        ).order_by('-rank', 'position_name')

        # 機能一覧
        features = FeatureMaster.objects.filter(
            tenant_ref=tenant_id, is_active=True
        ).order_by('display_order', 'feature_code')

        # 権限マトリックス
        permissions_map = {}
        for perm in PositionPermission.objects.filter(tenant_ref=tenant_id):
            key = f"{perm.position_id}_{perm.feature_id}"
            permissions_map[key] = perm.has_permission

        # マトリックスデータを構築
        matrix = []
        for feature in features:
            row = {
                'feature_id': str(feature.id),
                'feature_code': feature.feature_code,
                'feature_name': feature.feature_name,
                'parent_code': feature.parent_code,
                'category': feature.category,
                'permissions': {}
            }
            for position in positions:
                key = f"{position.id}_{feature.id}"
                row['permissions'][str(position.id)] = permissions_map.get(key, False)
            matrix.append(row)

        return Response({
            'positions': PositionSerializer(positions, many=True).data,
            'features': FeatureMasterSerializer(features, many=True).data,
            'matrix': matrix,
        })

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """権限を一括更新"""
        serializer = BulkPermissionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tenant_id = request.user.tenant_id
        permissions_data = serializer.validated_data['permissions']

        updated_count = 0
        created_count = 0

        for perm_data in permissions_data:
            position_id = perm_data['position_id']
            feature_id = perm_data['feature_id']
            has_permission = perm_data['has_permission']

            perm, created = PositionPermission.objects.update_or_create(
                tenant_ref=tenant_id,
                position_id=position_id,
                feature_id=feature_id,
                defaults={'has_permission': has_permission}
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        return Response({
            'success': True,
            'created': created_count,
            'updated': updated_count,
        })

    @action(detail=False, methods=['post'])
    def toggle(self, request):
        """単一の権限をトグル"""
        position_id = request.data.get('position_id')
        feature_id = request.data.get('feature_id')

        if not position_id or not feature_id:
            return Response(
                {'error': 'position_id and feature_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        tenant_id = request.user.tenant_id

        perm, created = PositionPermission.objects.get_or_create(
            tenant_ref=tenant_id,
            position_id=position_id,
            feature_id=feature_id,
            defaults={'has_permission': True}
        )

        if not created:
            perm.has_permission = not perm.has_permission
            perm.save()

        return Response({
            'success': True,
            'has_permission': perm.has_permission,
        })


class EmployeeViewSet(viewsets.ModelViewSet):
    """社員ViewSet"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Employee.objects.filter(
            tenant_ref=self.request.user.tenant_id,
            is_active=True
        ).select_related('position').prefetch_related('schools', 'brands').order_by(
            'department', 'last_name', 'first_name'
        )

        # フィルター
        school_id = self.request.query_params.get('school')
        brand_id = self.request.query_params.get('brand')

        if school_id:
            queryset = queryset.filter(schools__id=school_id)
        if brand_id:
            queryset = queryset.filter(brands__id=brand_id)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EmployeeDetailSerializer
        return EmployeeListSerializer

    def perform_create(self, serializer):
        employee = serializer.save(tenant_ref=self.request.user.tenant_id)

        # 社員用のUserアカウントを自動作成（チャット機能用）
        from apps.users.models import User
        import secrets

        if employee.email and not User.objects.filter(email=employee.email).exists():
            User.objects.create_user(
                email=employee.email,
                password=secrets.token_urlsafe(16),  # ランダムパスワード
                last_name=employee.last_name,
                first_name=employee.first_name,
                user_type='STAFF',
                tenant_id=self.request.user.tenant_id,
                staff_id=employee.id,
                is_active=True,
                must_change_password=True,  # 初回ログイン時にパスワード変更を促す
            )

    @action(detail=False, methods=['get'])
    def grouped(self, request):
        """校舎・ブランド別にグループ化した社員一覧"""
        from apps.schools.models import School, Brand

        tenant_id = request.user.tenant_id

        # 校舎一覧を取得
        schools = School.objects.filter(
            tenant_ref=tenant_id, is_active=True
        ).order_by('school_name')

        # ブランド一覧を取得
        brands = Brand.objects.filter(
            tenant_ref=tenant_id, is_active=True
        ).order_by('brand_name')

        # 全社員を取得
        employees = Employee.objects.filter(
            tenant_ref=tenant_id, is_active=True
        ).select_related('position').prefetch_related('schools', 'brands').order_by(
            'last_name', 'first_name'
        )

        # 校舎別グループ化
        school_groups = []
        for school in schools:
            school_employees = [
                {
                    'id': str(e.id),
                    'name': f"{e.last_name} {e.first_name}",
                    'position': e.position.position_name if e.position else e.position_text or '',
                    'email': e.email or '',
                }
                for e in employees if school in e.schools.all()
            ]
            if school_employees:
                school_groups.append({
                    'type': 'school',
                    'id': str(school.id),
                    'name': school.school_name,
                    'employees': school_employees,
                })

        # ブランド別グループ化
        brand_groups = []
        for brand in brands:
            brand_employees = [
                {
                    'id': str(e.id),
                    'name': f"{e.last_name} {e.first_name}",
                    'position': e.position.position_name if e.position else e.position_text or '',
                    'email': e.email or '',
                }
                for e in employees if brand in e.brands.all()
            ]
            if brand_employees:
                brand_groups.append({
                    'type': 'brand',
                    'id': str(brand.id),
                    'name': brand.brand_name,
                    'employees': brand_employees,
                })

        # 所属なし（校舎・ブランドどちらもない）
        unassigned_employees = [
            {
                'id': str(e.id),
                'name': f"{e.last_name} {e.first_name}",
                'position': e.position.position_name if e.position else e.position_text or '',
                'email': e.email or '',
            }
            for e in employees
            if not e.schools.exists() and not e.brands.exists()
        ]

        return Response({
            'school_groups': school_groups,
            'brand_groups': brand_groups,
            'unassigned': unassigned_employees,
            'all_employees': EmployeeListSerializer(employees, many=True).data,
        })
