"""
Student Services Tests - 生徒サービスのユニットテスト
"""
import os
import pytest
from datetime import date
from unittest.mock import Mock, patch
from django.utils import timezone

# PostgreSQL必須テストのマーカー
requires_postgres = pytest.mark.skipif(
    not os.environ.get('USE_POSTGRES_FOR_TESTS'),
    reason="Requires PostgreSQL. Set USE_POSTGRES_FOR_TESTS=1 or run in Docker."
)


class TestStudentStatusService:
    """生徒ステータス遷移サービスのテスト"""

    def test_allowed_transitions_from_lead(self):
        """リードからの遷移可能ステータス"""
        from apps.students.services.status_service import StudentStatusService

        allowed = StudentStatusService.ALLOWED_TRANSITIONS['lead']
        assert 'trial' in allowed
        assert 'enrolled' in allowed
        assert 'withdrawn' in allowed
        assert 'suspended' not in allowed

    def test_allowed_transitions_from_trial(self):
        """体験からの遷移可能ステータス"""
        from apps.students.services.status_service import StudentStatusService

        allowed = StudentStatusService.ALLOWED_TRANSITIONS['trial']
        assert 'enrolled' in allowed
        assert 'withdrawn' in allowed
        assert 'suspended' not in allowed

    def test_allowed_transitions_from_enrolled(self):
        """在籍からの遷移可能ステータス"""
        from apps.students.services.status_service import StudentStatusService

        allowed = StudentStatusService.ALLOWED_TRANSITIONS['enrolled']
        assert 'suspended' in allowed
        assert 'withdrawn' in allowed
        assert 'trial' not in allowed

    def test_allowed_transitions_from_suspended(self):
        """休会からの遷移可能ステータス"""
        from apps.students.services.status_service import StudentStatusService

        allowed = StudentStatusService.ALLOWED_TRANSITIONS['suspended']
        assert 'enrolled' in allowed
        assert 'withdrawn' in allowed
        assert 'trial' not in allowed

    def test_withdrawn_no_transitions(self):
        """退会後は遷移不可"""
        from apps.students.services.status_service import StudentStatusService

        allowed = StudentStatusService.ALLOWED_TRANSITIONS['withdrawn']
        assert len(allowed) == 0

    @pytest.mark.django_db
    @requires_postgres
    def test_can_transition_to(self):
        """遷移可否チェック"""
        from apps.students.services.status_service import StudentStatusService
        from apps.students.models import Student
        from apps.tenants.models import Tenant

        tenant = Tenant.objects.create(
            tenant_code='TEST_STATUS',
            tenant_name='テスト',
            is_active=True
        )

        student = Student.objects.create(
            tenant_id=tenant.id,
            student_no='ST_STATUS_001',
            last_name='テスト',
            first_name='生徒',
            status='enrolled'
        )

        service = StudentStatusService(student)

        # 在籍→休会: OK
        assert service.can_transition_to('suspended') is True
        # 在籍→退会: OK
        assert service.can_transition_to('withdrawn') is True
        # 在籍→体験: NG
        assert service.can_transition_to('trial') is False

    @pytest.mark.django_db
    @requires_postgres
    def test_transition_to_suspended(self):
        """休会への遷移"""
        from apps.students.services.status_service import StudentStatusService
        from apps.students.models import Student
        from apps.tenants.models import Tenant

        tenant = Tenant.objects.create(
            tenant_code='TEST_SUSPEND',
            tenant_name='テスト',
            is_active=True
        )

        student = Student.objects.create(
            tenant_id=tenant.id,
            student_no='ST_SUSPEND_001',
            last_name='テスト',
            first_name='生徒',
            status='enrolled'
        )

        service = StudentStatusService(student)
        result = service.suspend(suspended_date=date(2025, 1, 31))

        assert result is True
        student.refresh_from_db()
        assert student.status == 'suspended'
        assert student.suspended_date == date(2025, 1, 31)

    @pytest.mark.django_db
    @requires_postgres
    def test_transition_to_enrolled_from_suspended(self):
        """休会から復会への遷移"""
        from apps.students.services.status_service import StudentStatusService
        from apps.students.models import Student
        from apps.tenants.models import Tenant

        tenant = Tenant.objects.create(
            tenant_code='TEST_RESUME',
            tenant_name='テスト',
            is_active=True
        )

        student = Student.objects.create(
            tenant_id=tenant.id,
            student_no='ST_RESUME_001',
            last_name='テスト',
            first_name='生徒',
            status='suspended',
            suspended_date=date(2025, 1, 1)
        )

        service = StudentStatusService(student)
        result = service.resume()

        assert result is True
        student.refresh_from_db()
        assert student.status == 'enrolled'
        assert student.suspended_date is None

    @pytest.mark.django_db
    @requires_postgres
    def test_invalid_transition_raises_error(self):
        """無効な遷移でエラー発生"""
        from apps.students.services.status_service import StudentStatusService
        from apps.students.models import Student
        from apps.tenants.models import Tenant

        tenant = Tenant.objects.create(
            tenant_code='TEST_INVALID',
            tenant_name='テスト',
            is_active=True
        )

        student = Student.objects.create(
            tenant_id=tenant.id,
            student_no='ST_INVALID_001',
            last_name='テスト',
            first_name='生徒',
            status='withdrawn'
        )

        service = StudentStatusService(student)

        with pytest.raises(ValueError, match='ステータス遷移が許可されていません'):
            service.transition_to('enrolled')


class TestSuspensionService:
    """休会申請サービスのテスト"""

    @pytest.mark.django_db
    @requires_postgres
    def test_cancel_pending_request(self):
        """申請中の休会をキャンセル"""
        from apps.students.services.request_service import SuspensionService
        from apps.students.models import Student, SuspensionRequest
        from apps.tenants.models import Tenant

        tenant = Tenant.objects.create(
            tenant_code='TEST_CANCEL',
            tenant_name='テスト',
            is_active=True
        )

        student = Student.objects.create(
            tenant_id=tenant.id,
            student_no='ST_CANCEL_001',
            last_name='テスト',
            first_name='生徒',
            status='enrolled'
        )

        request = SuspensionRequest.objects.create(
            tenant_id=tenant.id,
            student=student,
            suspend_from=date(2025, 2, 1),
            status='pending'
        )

        service = SuspensionService(request)
        result = service.cancel()

        assert result is True
        request.refresh_from_db()
        assert request.status == 'cancelled'

    @pytest.mark.django_db
    @requires_postgres
    def test_cancel_non_pending_raises_error(self):
        """申請中以外のキャンセルでエラー"""
        from apps.students.services.request_service import SuspensionService
        from apps.students.models import Student, SuspensionRequest
        from apps.tenants.models import Tenant

        tenant = Tenant.objects.create(
            tenant_code='TEST_CANCEL_ERR',
            tenant_name='テスト',
            is_active=True
        )

        student = Student.objects.create(
            tenant_id=tenant.id,
            student_no='ST_CANCEL_ERR_001',
            last_name='テスト',
            first_name='生徒',
            status='enrolled'
        )

        request = SuspensionRequest.objects.create(
            tenant_id=tenant.id,
            student=student,
            suspend_from=date(2025, 2, 1),
            status='approved'  # 既に承認済み
        )

        service = SuspensionService(request)

        with pytest.raises(ValueError, match='申請中のもののみキャンセルできます'):
            service.cancel()


class TestWithdrawalService:
    """退会申請サービスのテスト"""

    @pytest.mark.django_db
    @requires_postgres
    def test_cancel_pending_withdrawal(self):
        """申請中の退会をキャンセル"""
        from apps.students.services.request_service import WithdrawalService
        from apps.students.models import Student, WithdrawalRequest
        from apps.tenants.models import Tenant

        tenant = Tenant.objects.create(
            tenant_code='TEST_WITHDRAW',
            tenant_name='テスト',
            is_active=True
        )

        student = Student.objects.create(
            tenant_id=tenant.id,
            student_no='ST_WITHDRAW_001',
            last_name='テスト',
            first_name='生徒',
            status='enrolled'
        )

        request = WithdrawalRequest.objects.create(
            tenant_id=tenant.id,
            student=student,
            withdrawal_date=date(2025, 3, 31),
            status='pending'
        )

        service = WithdrawalService(request)
        result = service.cancel()

        assert result is True
        request.refresh_from_db()
        assert request.status == 'cancelled'
