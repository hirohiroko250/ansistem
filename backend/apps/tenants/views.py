"""
Tenants Views
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Tenant, Position, FeatureMaster, PositionPermission, Employee, EmployeeGroup
from .serializers import (
    TenantSerializer, TenantDetailSerializer,
    PositionSerializer, FeatureMasterSerializer,
    PositionPermissionSerializer, BulkPermissionUpdateSerializer,
    EmployeeListSerializer, EmployeeDetailSerializer,
    EmployeeGroupListSerializer, EmployeeGroupDetailSerializer, EmployeeGroupCreateUpdateSerializer,
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
        # 承認/却下アクションの場合は承認待ち社員も含める
        if self.action in ['approve', 'reject', 'retrieve']:
            queryset = Employee.objects.filter(
                tenant_ref=self.request.user.tenant_id
            )
        else:
            queryset = Employee.objects.filter(
                tenant_ref=self.request.user.tenant_id,
                is_active=True
            )

        queryset = queryset.select_related('position').prefetch_related('schools', 'brands').order_by(
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
        # 承認待ち状態で社員を作成
        employee = serializer.save(
            tenant_ref=self.request.user.tenant_id,
            is_active=False,
            approval_status='pending'
        )

        # 承認タスクを自動作成
        from apps.tasks.models import Task
        Task.objects.create(
            tenant_id=self.request.user.tenant_id,
            task_type='staff_registration',
            title=f'社員登録承認: {employee.last_name} {employee.first_name}',
            description=f'新規社員「{employee.last_name} {employee.first_name}」の登録承認が必要です。\n\n'
                       f'社員番号: {employee.employee_no or "未設定"}\n'
                       f'メール: {employee.email or "未設定"}\n'
                       f'部署: {employee.department or "未設定"}',
            status='new',
            priority='normal',
            source_type='employee',
            source_id=str(employee.id),
            created_by_id=self.request.user.staff_id,
        )

        # 社員用のUserアカウントを作成（is_active=Falseで作成、承認後に有効化）
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
                is_active=False,  # 承認後に有効化
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

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """承認待ち社員一覧を取得"""
        from apps.users.models import User

        tenant_id = request.user.tenant_id

        # 承認待ちの社員を取得（is_active=False）
        pending_employees = Employee.objects.filter(
            tenant_ref=tenant_id,
            is_active=False
        ).select_related('position').prefetch_related('schools', 'brands').order_by('-id')

        result = []
        for emp in pending_employees:
            # 関連するUserを取得
            user = User.objects.filter(staff_id=emp.id).first()
            result.append({
                'id': str(emp.id),
                'employee_no': emp.employee_no,
                'last_name': emp.last_name,
                'first_name': emp.first_name,
                'full_name': f"{emp.last_name} {emp.first_name}",
                'email': emp.email,
                'phone': emp.phone,
                'department': emp.department,
                'position_name': emp.position.position_name if emp.position else emp.position_text,
                'hire_date': emp.hire_date.isoformat() if emp.hire_date else None,
                'schools': [{'id': str(s.id), 'name': s.school_name} for s in emp.schools.all()],
                'brands': [{'id': str(b.id), 'name': b.brand_name} for b in emp.brands.all()],
                'user_id': str(user.id) if user else None,
                'user_email': user.email if user else emp.email,
                'created_at': user.created_at.isoformat() if user else None,
            })

        return Response(result)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """社員を承認（有効化）"""
        from apps.users.models import User
        from apps.tasks.models import Task
        from django.utils import timezone

        employee = self.get_object()

        # 社員を有効化・承認済みに更新
        employee.is_active = True
        employee.approval_status = 'approved'
        employee.save()

        # 関連するUserも有効化
        user = User.objects.filter(staff_id=employee.id).first()
        if user:
            user.is_active = True
            user.save()

        # 関連するタスクを完了にする
        Task.objects.filter(
            tenant_id=request.user.tenant_id,
            source_type='employee',
            source_id=str(employee.id),
            task_type='staff_registration',
            status__in=['new', 'in_progress', 'waiting']
        ).update(status='completed', completed_at=timezone.now())

        return Response({
            'success': True,
            'message': f'{employee.last_name} {employee.first_name}さんを承認しました',
            'employee_id': str(employee.id),
            'user_id': str(user.id) if user else None,
        })

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """社員登録を却下（データは保持）"""
        from apps.users.models import User
        from apps.tasks.models import Task
        from django.utils import timezone

        employee = self.get_object()
        employee_id = str(employee.id)
        employee_name = f'{employee.last_name} {employee.first_name}'

        # 却下理由を取得
        reason = request.data.get('reason', '')

        # 社員を却下状態に更新（データは保持）
        employee.approval_status = 'rejected'
        employee.rejected_at = timezone.now()
        employee.rejected_reason = reason
        employee.is_active = False
        employee.save()

        # 関連するUserを無効化（削除せずに保持）
        User.objects.filter(staff_id=employee.id).update(is_active=False)

        # 関連するタスクをキャンセルにする
        Task.objects.filter(
            tenant_id=request.user.tenant_id,
            source_type='employee',
            source_id=employee_id,
            task_type='staff_registration',
            status__in=['new', 'in_progress', 'waiting']
        ).update(status='cancelled', completed_at=timezone.now())

        return Response({
            'success': True,
            'message': f'{employee_name}さんの登録を却下しました',
        })


class EmployeeGroupViewSet(viewsets.ModelViewSet):
    """社員グループViewSet"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EmployeeGroup.objects.filter(
            tenant_ref=self.request.user.tenant_id,
            is_active=True
        ).prefetch_related('members', 'members__position', 'members__schools', 'members__brands').order_by('name')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return EmployeeGroupCreateUpdateSerializer
        if self.action == 'retrieve':
            return EmployeeGroupDetailSerializer
        return EmployeeGroupListSerializer

    def perform_create(self, serializer):
        serializer.save(tenant_ref=self.request.user.tenant_id)

    def perform_destroy(self, instance):
        # 論理削除
        instance.is_active = False
        instance.save()


from rest_framework.views import APIView


class DepartmentListView(APIView):
    """部署一覧API - 社員の部署から動的に取得"""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # X-Tenant-ID ヘッダーまたは認証ユーザーからテナントIDを取得
        tenant_id = request.headers.get('X-Tenant-ID')
        if not tenant_id and hasattr(request, 'user') and request.user.is_authenticated:
            tenant_id = request.user.tenant_id

        if not tenant_id:
            return Response([])

        departments = Employee.objects.filter(
            tenant_ref=tenant_id,
            is_active=True
        ).exclude(
            department__isnull=True
        ).exclude(
            department=''
        ).values_list('department', flat=True).distinct().order_by('department')

        return Response([{'name': d} for d in departments])


class RoleListView(APIView):
    """役割一覧API - 役職マスタから取得"""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # X-Tenant-ID ヘッダーまたは認証ユーザーからテナントIDを取得
        tenant_id = request.headers.get('X-Tenant-ID')
        if not tenant_id and hasattr(request, 'user') and request.user.is_authenticated:
            tenant_id = request.user.tenant_id

        if not tenant_id:
            return Response([])

        positions = Position.objects.filter(
            tenant_ref=tenant_id,
            is_active=True
        ).values_list('position_name', flat=True).order_by('position_name')

        return Response([{'name': p} for p in positions])


class PublicPositionListView(APIView):
    """役職一覧API（公開） - 新規登録用"""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # X-Tenant-ID ヘッダーからテナントIDを取得
        tenant_id = request.headers.get('X-Tenant-ID')
        if not tenant_id:
            return Response([])

        positions = Position.objects.filter(
            tenant_ref=tenant_id,
            is_active=True
        ).order_by('position_name')

        return Response([{
            'id': str(p.id),
            'position_name': p.position_name,
            'position_code': p.position_code,
        } for p in positions])
