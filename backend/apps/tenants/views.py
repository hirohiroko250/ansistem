"""
Tenants Views
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Tenant, Position, FeatureMaster, PositionPermission
from .serializers import (
    TenantSerializer, TenantDetailSerializer,
    PositionSerializer, FeatureMasterSerializer,
    PositionPermissionSerializer, BulkPermissionUpdateSerializer,
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
