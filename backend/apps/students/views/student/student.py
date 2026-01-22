"""
Student Views - 生徒管理関連
StudentViewSet
"""
import uuid
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q
from django.utils import timezone

from apps.core.permissions import IsTenantUser
from apps.core.csv_utils import CSVMixin
from apps.students.models import Student
from apps.students.serializers import (
    StudentListSerializer, StudentDetailSerializer,
    StudentCreateSerializer, StudentUpdateSerializer,
    StudentWithGuardiansSerializer,
    StudentSchoolSerializer, StudentGuardianSerializer,
)
from .mixins import StudentItemsMixin


class StudentViewSet(StudentItemsMixin, CSVMixin, viewsets.ModelViewSet):
    """生徒ビューセット"""
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    # CSV設定
    csv_filename_prefix = 'students'
    csv_export_fields = [
        'student_no', 'last_name', 'first_name', 'last_name_kana', 'first_name_kana',
        'email', 'phone', 'line_id', 'birth_date', 'gender',
        'school_name', 'school_type', 'grade.grade_name',
        'primary_school.school_name', 'primary_brand.brand_name',
        'status', 'enrollment_date', 'withdrawal_date',
        'notes', 'tenant_id'
    ]
    csv_export_headers = {
        'student_no': '生徒番号',
        'last_name': '姓',
        'first_name': '名',
        'last_name_kana': '姓（カナ）',
        'first_name_kana': '名（カナ）',
        'email': 'メールアドレス',
        'phone': '電話番号',
        'line_id': 'LINE ID',
        'birth_date': '生年月日',
        'gender': '性別',
        'school_name': '在籍学校名',
        'school_type': '学校種別',
        'grade.grade_name': '学年',
        'primary_school.school_name': '主所属校舎',
        'primary_brand.brand_name': '主所属ブランド',
        'status': 'ステータス',
        'enrollment_date': '入塾日',
        'withdrawal_date': '退塾日',
        'notes': '備考',
        'tenant_id': 'テナントID',
    }
    csv_import_mapping = {
        '生徒番号': 'student_no',
        '姓': 'last_name',
        '名': 'first_name',
        '姓（カナ）': 'last_name_kana',
        '名（カナ）': 'first_name_kana',
        'メールアドレス': 'email',
        '電話番号': 'phone',
        'LINE ID': 'line_id',
        '生年月日': 'birth_date',
        '性別': 'gender',
        '在籍学校名': 'school_name',
        '学校種別': 'school_type',
        'ステータス': 'status',
        '入塾日': 'enrollment_date',
        '退塾日': 'withdrawal_date',
        '備考': 'notes',
    }
    csv_required_fields = ['生徒番号', '姓', '名']
    csv_unique_fields = ['student_no']

    def get_queryset(self):
        from apps.core.permissions import is_admin_user

        # request.tenant_id または request.user.tenant_id からテナントIDを取得
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id is None and hasattr(self.request, 'user') and hasattr(self.request.user, 'tenant_id'):
            tenant_id = self.request.user.tenant_id

        queryset = Student.objects.filter(
            deleted_at__isnull=True
        ).select_related(
            'grade', 'primary_school', 'primary_brand', 'guardian'
        ).prefetch_related(
            'contracts', 'contracts__course', 'contracts__brand',
            'school_enrollments', 'school_enrollments__school', 'school_enrollments__brand'
        )

        # 管理者以外はテナントでフィルタ
        if not is_admin_user(self.request.user):
            queryset = queryset.filter(tenant_id=tenant_id)

        # ログインユーザーが保護者の場合、その保護者に紐づく子供だけを返す
        if hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            guardian = self.request.user.guardian_profile
            queryset = queryset.filter(guardian=guardian)

        # フィルタリング
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        school_id = self.request.query_params.get('school_id') or self.request.query_params.get('primary_school_id')
        if school_id:
            # primary_schoolまたはStudentSchoolで紐づいている生徒を取得
            queryset = queryset.filter(
                Q(primary_school_id=school_id) |
                Q(school_enrollments__school_id=school_id, school_enrollments__enrollment_status='active', school_enrollments__deleted_at__isnull=True)
            ).distinct()

        brand_id = self.request.query_params.get('brand_id')
        if brand_id:
            # primary_brandまたはStudentSchool、またはbrandsで紐づいている生徒を取得
            queryset = queryset.filter(
                Q(primary_brand_id=brand_id) |
                Q(brands__id=brand_id) |
                Q(school_enrollments__brand_id=brand_id, school_enrollments__enrollment_status='active', school_enrollments__deleted_at__isnull=True)
            ).distinct()

        # ブランドカテゴリ（会社）でフィルタ
        brand_category_id = self.request.query_params.get('brand_category_id')
        if brand_category_id:
            queryset = queryset.filter(primary_brand__brand_category_id=brand_category_id)

        grade_id = self.request.query_params.get('grade_id')
        if grade_id:
            queryset = queryset.filter(grade_id=grade_id)

        # 保護者IDでフィルタ（兄弟検索用）
        guardian_id = self.request.query_params.get('guardian_id')
        if guardian_id:
            queryset = queryset.filter(guardian_id=guardian_id)

        # ID検索（完全一致）
        student_no = self.request.query_params.get('student_no')
        if student_no:
            queryset = queryset.filter(student_no=student_no.strip())

        # 名前・電話番号検索（曖昧一致）
        search = self.request.query_params.get('search')
        if search:
            # 電話番号検索用に数字のみを抽出
            search_digits = ''.join(filter(str.isdigit, search))

            # 名前・電話番号は曖昧一致
            q_filter = (
                Q(last_name__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name_kana__icontains=search) |
                Q(first_name_kana__icontains=search) |
                Q(email__icontains=search)
            )

            # 電話番号検索（数字が含まれている場合）
            if search_digits:
                q_filter |= (
                    Q(phone__icontains=search_digits) |
                    Q(phone2__icontains=search_digits) |
                    Q(guardian__phone__icontains=search_digits) |
                    Q(guardian__phone_mobile__icontains=search_digits)
                )

            queryset = queryset.filter(q_filter)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return StudentListSerializer
        elif self.action == 'create':
            return StudentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return StudentUpdateSerializer
        elif self.action == 'with_guardians':
            return StudentWithGuardiansSerializer
        return StudentDetailSerializer

    def perform_create(self, serializer):
        # ログインユーザーが保護者の場合、自動的に紐付け
        guardian = None
        if hasattr(self.request.user, 'guardian_profile') and self.request.user.guardian_profile:
            guardian = self.request.user.guardian_profile

        # tenant_idを取得（request.tenant_idまたは保護者プロファイルから）
        tenant_id = getattr(self.request, 'tenant_id', None)
        if not tenant_id and guardian:
            tenant_id = guardian.tenant_id

        student = serializer.save(tenant_id=tenant_id, guardian=guardian)
        # タスクはsignalsで自動作成される

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=False, methods=['get'])
    def export(self, request):
        """CSVエクスポート"""
        return self.export_csv(request)

    @action(detail=False, methods=['post'])
    def import_data(self, request):
        """CSVインポート"""
        return self.import_csv(request)

    @action(detail=False, methods=['get'])
    def template(self, request):
        """CSVテンプレートダウンロード"""
        return self.get_csv_template(request)

    @action(detail=False, methods=['get'])
    def with_guardians(self, request):
        """保護者情報付き生徒一覧"""
        queryset = self.get_queryset().prefetch_related(
            'guardian_relations__guardian'
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def guardians(self, request, pk=None):
        """生徒の保護者一覧"""
        student = self.get_object()
        relations = student.guardian_relations.select_related('guardian').all()
        serializer = StudentGuardianSerializer(relations, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_guardian(self, request, pk=None):
        """保護者追加"""
        student = self.get_object()
        serializer = StudentGuardianSerializer(data={
            **request.data,
            'student': student.id
        })
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=request.tenant_id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def schools(self, request, pk=None):
        """生徒の所属校舎一覧"""
        student = self.get_object()
        enrollments = student.school_enrollments.select_related('school', 'brand').all()
        serializer = StudentSchoolSerializer(enrollments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """ステータス変更"""
        student = self.get_object()
        new_status = request.data.get('status')

        if new_status not in dict(Student.Status.choices):
            return Response(
                {'error': '無効なステータスです'},
                status=status.HTTP_400_BAD_REQUEST
            )

        student.status = new_status
        if new_status == Student.Status.WITHDRAWN:
            student.withdrawal_date = request.data.get('withdrawal_date', timezone.now().date())
            student.withdrawal_reason = request.data.get('withdrawal_reason', '')

        student.save()
        return Response(StudentDetailSerializer(student).data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """生徒統計"""
        queryset = self.get_queryset()
        stats = {
            'total': queryset.count(),
            'by_status': {},
            'by_grade': {},
        }

        for status_choice in Student.Status.choices:
            stats['by_status'][status_choice[0]] = queryset.filter(
                status=status_choice[0]
            ).count()

        return Response(stats)

    @action(detail=True, methods=['get'], url_path='qr-code')
    def qr_code(self, request, pk=None):
        """生徒のQRコード情報を取得"""
        student = self.get_object()
        return Response({
            'qr_code': str(student.qr_code),
            'student_no': student.student_no,
            'student_name': student.full_name,
        })

    @action(detail=True, methods=['post'], url_path='regenerate-qr')
    def regenerate_qr(self, request, pk=None):
        """QRコードを再発行"""
        student = self.get_object()
        student.qr_code = uuid.uuid4()
        student.save(update_fields=['qr_code'])
        return Response({
            'qr_code': str(student.qr_code),
            'student_no': student.student_no,
            'student_name': student.full_name,
            'message': 'QRコードを再発行しました',
        })

    @action(detail=False, methods=['get'], url_path='my-qr')
    def my_qr(self, request):
        """ログイン中の生徒自身のQRコード情報を取得"""
        user = request.user
        if not hasattr(user, 'student_profile') or not user.student_profile:
            return Response(
                {'error': '生徒アカウントでログインしてください'},
                status=status.HTTP_403_FORBIDDEN
            )
        student = user.student_profile
        return Response({
            'qr_code': str(student.qr_code),
            'student_no': student.student_no,
            'student_name': student.full_name,
        })

    @action(detail=False, methods=['get', 'post'], url_path='children')
    def children(self, request):
        """保護者の子ども一覧を取得・子ども追加"""
        user = request.user

        # 保護者情報を取得
        guardian = getattr(user, 'guardian_profile', None)
        if not guardian:
            return Response(
                {'error': '保護者アカウントでログインしてください'},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.method == 'GET':
            # 子ども一覧を取得
            children = guardian.children.filter(deleted_at__isnull=True).select_related(
                'grade', 'primary_school', 'primary_brand'
            ).order_by('birth_date')
            serializer = StudentListSerializer(children, many=True)
            return Response({
                'students': serializer.data
            })
        else:
            # POST: 子ども追加
            serializer = StudentCreateSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                student = serializer.save(guardian=guardian)
                return Response(StudentDetailSerializer(student).data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get', 'patch'], url_path='children/(?P<child_id>[^/.]+)')
    def child_detail(self, request, child_id=None):
        """保護者の子ども詳細を取得・更新"""
        user = request.user

        # 保護者情報を取得
        guardian = getattr(user, 'guardian_profile', None)
        if not guardian:
            return Response(
                {'error': '保護者アカウントでログインしてください'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 子どもを取得
        try:
            child = guardian.children.filter(deleted_at__isnull=True).select_related(
                'grade', 'primary_school', 'primary_brand'
            ).get(id=child_id)
        except Student.DoesNotExist:
            return Response(
                {'error': 'お子様が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        if request.method == 'GET':
            serializer = StudentDetailSerializer(child)
            return Response(serializer.data)
        else:
            # PATCH: 子ども更新
            serializer = StudentUpdateSerializer(child, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                student = serializer.save()
                return Response(StudentDetailSerializer(student).data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='children/(?P<child_id>[^/.]+)/upload-photo', parser_classes=[MultiPartParser, FormParser])
    def child_upload_photo(self, request, child_id=None):
        """保護者が子どもの写真をアップロード"""
        import os
        from django.conf import settings
        from django.core.files.storage import default_storage

        user = request.user
        guardian = getattr(user, 'guardian_profile', None)
        if not guardian:
            return Response(
                {'error': '保護者アカウントでログインしてください'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            student = guardian.children.filter(deleted_at__isnull=True).get(id=child_id)
        except Student.DoesNotExist:
            return Response(
                {'error': 'お子様が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

        photo = request.FILES.get('photo')
        if not photo:
            return Response(
                {'error': '写真ファイルが必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ファイルサイズチェック（5MB以下）
        if photo.size > 5 * 1024 * 1024:
            return Response(
                {'error': 'ファイルサイズは5MB以下にしてください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 拡張子チェック
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        ext = os.path.splitext(photo.name)[1].lower()
        if ext not in allowed_extensions:
            return Response(
                {'error': 'JPG, PNG, GIF, WEBPファイルのみアップロード可能です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 既存の写真を削除
        if student.profile_image_url:
            try:
                old_path = student.profile_image_url.replace(settings.MEDIA_URL, '')
                if default_storage.exists(old_path):
                    default_storage.delete(old_path)
            except Exception:
                pass

        # 新しいファイル名を生成
        filename = f"students/{student.id}/photo{ext}"
        path = default_storage.save(filename, photo)
        url = default_storage.url(path)

        # URLを保存
        student.profile_image_url = url
        student.save(update_fields=['profile_image_url'])

        return Response({
            'profile_image_url': url,
            'message': '写真をアップロードしました',
        })

    @action(detail=True, methods=['post'], url_path='upload-photo', parser_classes=[MultiPartParser, FormParser])
    def upload_photo(self, request, pk=None):
        """生徒の証明写真をアップロード"""
        import os
        from django.conf import settings
        from django.core.files.storage import default_storage

        student = self.get_object()
        photo = request.FILES.get('photo')

        if not photo:
            return Response(
                {'error': '写真ファイルが必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ファイルサイズチェック（5MB以下）
        if photo.size > 5 * 1024 * 1024:
            return Response(
                {'error': 'ファイルサイズは5MB以下にしてください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 拡張子チェック
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        ext = os.path.splitext(photo.name)[1].lower()
        if ext not in allowed_extensions:
            return Response(
                {'error': 'JPG, PNG, GIF, WEBPファイルのみアップロード可能です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 既存の写真を削除
        if student.profile_image_url:
            try:
                old_path = student.profile_image_url.replace(settings.MEDIA_URL, '')
                if default_storage.exists(old_path):
                    default_storage.delete(old_path)
            except Exception:
                pass

        # 新しいファイル名を生成
        filename = f"students/{student.id}/photo{ext}"
        path = default_storage.save(filename, photo)
        url = default_storage.url(path)

        # URLを保存
        student.profile_image_url = url
        student.save(update_fields=['profile_image_url'])

        return Response({
            'profile_image_url': url,
            'message': '写真をアップロードしました',
        })

    @action(detail=True, methods=['delete'], url_path='delete-photo')
    def delete_photo(self, request, pk=None):
        """生徒の証明写真を削除"""
        from django.conf import settings
        from django.core.files.storage import default_storage

        student = self.get_object()

        if student.profile_image_url:
            try:
                old_path = student.profile_image_url.replace(settings.MEDIA_URL, '')
                if default_storage.exists(old_path):
                    default_storage.delete(old_path)
            except Exception:
                pass

        student.profile_image_url = ''
        student.save(update_fields=['profile_image_url'])

        return Response({
            'message': '写真を削除しました',
        })
