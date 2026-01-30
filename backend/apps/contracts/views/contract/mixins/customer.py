"""
Customer Actions Mixin - 顧客向けアクション
CustomerActionsMixin
"""
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from apps.contracts.models import StudentItem
from apps.contracts.serializers import MyStudentItemSerializer


class CustomerActionsMixin:
    """顧客向けアクションMixin"""

    @action(detail=False, methods=['get'], url_path='my-contracts', permission_classes=[IsAuthenticated])
    def my_contracts(self, request):
        """顧客用：ログインユーザーの子どもの受講コース一覧"""
        from apps.students.models import Student, Guardian, StudentGuardian

        user = request.user
        request_tenant_id = getattr(request, 'tenant_id', None)

        # ユーザーに紐づく保護者を取得（tenant_idがNoneの場合はtenant_id条件なしで検索）
        try:
            if request_tenant_id:
                guardian = Guardian.objects.get(user=user, tenant_id=request_tenant_id, deleted_at__isnull=True)
            else:
                guardian = Guardian.objects.filter(user=user, deleted_at__isnull=True).first()
                if not guardian:
                    raise Guardian.DoesNotExist()
        except Guardian.DoesNotExist:
            return Response({'contracts': [], 'students': []})

        # Guardianが見つかったらそのtenant_idを使用
        tenant_id = guardian.tenant_id

        # 保護者に紐づく生徒を取得
        # 1. StudentGuardian中間テーブル経由
        student_ids_from_sg = set(StudentGuardian.objects.filter(
            guardian=guardian,
            tenant_id=tenant_id
        ).values_list('student_id', flat=True))

        # 2. Student.guardian直接参照（主保護者）
        student_ids_from_direct = set(Student.objects.filter(
            guardian=guardian,
            tenant_id=tenant_id,
            deleted_at__isnull=True
        ).values_list('id', flat=True))

        # 両方を統合
        all_student_ids = student_ids_from_sg | student_ids_from_direct

        students = Student.objects.filter(
            id__in=all_student_ids,
            tenant_id=tenant_id,
            deleted_at__isnull=True
        )

        # 生徒のStudentItem（受講コース）を取得 — 退会済みは除外
        student_items = StudentItem.objects.filter(
            student__in=students,
            tenant_id=tenant_id,
            deleted_at__isnull=True,
        ).filter(
            Q(course__isnull=False) | Q(brand__isnull=False)
        ).exclude(
            contract__status='cancelled'
        ).select_related(
            'student', 'student__grade',
            'school', 'brand', 'course', 'contract'
        ).order_by('student__last_name', 'student__first_name', '-created_at')

        # 重複を排除（同じ生徒・コース・校舎の組み合わせは1つにまとめる）
        seen = set()
        unique_items = []
        for item in student_items:
            key = (item.student_id, item.course_id, item.school_id)
            if key not in seen:
                seen.add(key)
                unique_items.append(item)

        from apps.students.serializers import StudentListSerializer

        return Response({
            'students': StudentListSerializer(students, many=True).data,
            'contracts': MyStudentItemSerializer(unique_items, many=True).data
        })
