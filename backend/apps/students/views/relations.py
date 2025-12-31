"""
Student Relations Views - 生徒関連付け管理
StudentGuardianViewSet, StudentSchoolViewSet
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
import csv
import io

from apps.core.permissions import IsTenantUser
from apps.core.csv_utils import CSVMixin
from ..models import Student, Guardian, StudentGuardian, StudentSchool
from ..serializers import StudentGuardianSerializer, StudentSchoolSerializer


class StudentGuardianViewSet(CSVMixin, viewsets.ModelViewSet):
    """生徒保護者関連ビューセット"""
    serializer_class = StudentGuardianSerializer
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    # CSV設定
    csv_filename_prefix = 'student_guardians'
    csv_export_fields = [
        'student.student_no', 'student.last_name', 'student.first_name',
        'guardian.guardian_no', 'guardian.last_name', 'guardian.first_name',
        'relationship', 'is_primary', 'is_emergency_contact', 'is_billing_target',
        'contact_priority', 'notes', 'tenant_id'
    ]
    csv_export_headers = {
        'student.student_no': '生徒番号',
        'student.last_name': '生徒姓',
        'student.first_name': '生徒名',
        'guardian.guardian_no': '保護者番号',
        'guardian.last_name': '保護者姓',
        'guardian.first_name': '保護者名',
        'relationship': '続柄',
        'is_primary': '主保護者',
        'is_emergency_contact': '緊急連絡先',
        'is_billing_target': '請求先',
        'contact_priority': '連絡優先順位',
        'notes': '備考',
        'tenant_id': 'テナントID',
    }
    csv_import_mapping = {
        '生徒番号': 'student_no',
        '保護者番号': 'guardian_no',
        '続柄': 'relationship',
        '主保護者': 'is_primary',
        '緊急連絡先': 'is_emergency_contact',
        '請求先': 'is_billing_target',
        '連絡優先順位': 'contact_priority',
        '備考': 'notes',
    }
    csv_required_fields = ['生徒番号', '保護者番号']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        return StudentGuardian.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('student', 'guardian')

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=['get'])
    def export(self, request):
        """CSVエクスポート"""
        return self.export_csv(request)

    @action(detail=False, methods=['post'])
    def import_data(self, request):
        """CSVインポート（生徒番号・保護者番号で紐付け）"""
        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response(
                {'error': 'CSVファイルが指定されていません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        tenant_id = getattr(request, 'tenant_id', None)

        content = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))

        created_count = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):
            student_no = row.get('生徒番号', '').strip()
            guardian_no = row.get('保護者番号', '').strip()

            if not student_no or not guardian_no:
                errors.append({'row': row_num, 'message': '生徒番号または保護者番号が空です'})
                continue

            try:
                student = Student.objects.get(tenant_id=tenant_id, student_no=student_no)
                guardian = Guardian.objects.get(tenant_id=tenant_id, guardian_no=guardian_no)

                relation, created = StudentGuardian.objects.update_or_create(
                    tenant_id=tenant_id,
                    student=student,
                    guardian=guardian,
                    defaults={
                        'relationship': row.get('続柄', 'other'),
                        'is_primary': row.get('主保護者', '').lower() in ('true', '1', 'yes', 'はい'),
                        'is_emergency_contact': row.get('緊急連絡先', '').lower() in ('true', '1', 'yes', 'はい'),
                        'is_billing_target': row.get('請求先', '').lower() in ('true', '1', 'yes', 'はい'),
                        'contact_priority': int(row.get('連絡優先順位', 1) or 1),
                        'notes': row.get('備考', ''),
                    }
                )
                if created:
                    created_count += 1

            except Student.DoesNotExist:
                errors.append({'row': row_num, 'message': f'生徒番号 {student_no} が見つかりません'})
            except Guardian.DoesNotExist:
                errors.append({'row': row_num, 'message': f'保護者番号 {guardian_no} が見つかりません'})
            except Exception as e:
                errors.append({'row': row_num, 'message': str(e)})

        return Response({
            'success': len(errors) == 0,
            'created': created_count,
            'errors': errors
        })

    @action(detail=False, methods=['get'])
    def template(self, request):
        """CSVテンプレートダウンロード"""
        return self.get_csv_template(request)


class StudentSchoolViewSet(CSVMixin, viewsets.ModelViewSet):
    """生徒所属ビューセット"""
    serializer_class = StudentSchoolSerializer
    permission_classes = [IsAuthenticated, IsTenantUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    # CSV設定
    csv_filename_prefix = 'student_schools'
    csv_export_fields = [
        'student.student_no', 'school.school_code', 'brand.brand_code',
        'enrollment_status', 'start_date', 'end_date', 'is_primary',
        'day_of_week', 'start_time', 'end_time', 'notes', 'tenant_id'
    ]
    csv_export_headers = {
        'student.student_no': '生徒番号',
        'school.school_code': '校舎コード',
        'brand.brand_code': 'ブランドコード',
        'enrollment_status': '在籍状況',
        'start_date': '開始日',
        'end_date': '終了日',
        'is_primary': '主所属',
        'day_of_week': '曜日',
        'start_time': '開始時間',
        'end_time': '終了時間',
        'notes': '備考',
        'tenant_id': 'テナントID',
    }

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        return StudentSchool.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).select_related('student', 'school', 'brand', 'class_schedule')

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=['get'])
    def export(self, request):
        """CSVエクスポート"""
        return self.export_csv(request)

    @action(detail=False, methods=['get'])
    def template(self, request):
        """CSVテンプレートダウンロード"""
        return self.get_csv_template(request)
