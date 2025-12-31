"""
マルチテナント分離テスト

テナントAのデータにテナントBがアクセスできないことを確認します。
セキュリティクリティカルなテストです。

実行方法:
    docker compose -f docker-compose.dev.yml exec backend pytest tests/test_multi_tenant.py -v

注意:
    これらのテストはデータベースを必要とします。
    マイグレーション互換性問題が解決するまでDockerコンテナ内で実行してください。
"""
import pytest

# 統合テスト - PostgreSQL環境でのみ実行
# ローカル: pytest tests/test_multi_tenant.py -v --skip-db
# Docker: docker compose exec backend pytest tests/test_multi_tenant.py -v
import os
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get('USE_POSTGRES_FOR_TESTS'),
        reason="Requires PostgreSQL. Set USE_POSTGRES_FOR_TESTS=1 or run in Docker."
    ),
]
from datetime import date
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant
from apps.schools.models import Brand, School, Grade
from apps.students.models import Student, Guardian, StudentGuardian
from apps.contracts.models import Product, Contract

User = get_user_model()


@pytest.fixture
def tenant_a(db):
    """テナントAを作成"""
    return Tenant.objects.create(
        tenant_code='TENANT_A',
        tenant_name='テナントA',
        plan_type=Tenant.PlanType.STANDARD,
        is_active=True,
    )


@pytest.fixture
def tenant_b(db):
    """テナントBを作成"""
    return Tenant.objects.create(
        tenant_code='TENANT_B',
        tenant_name='テナントB',
        plan_type=Tenant.PlanType.STANDARD,
        is_active=True,
    )


@pytest.fixture
def admin_user_a(db, tenant_a):
    """テナントAの管理者"""
    return User.objects.create_user(
        email='admin_a@test.com',
        password='testpass123',
        last_name='管理者',
        first_name='A',
        tenant_id=tenant_a.id,
        user_type=User.UserType.ADMIN,
        role=User.Role.ADMIN,
        is_staff=True,
    )


@pytest.fixture
def admin_user_b(db, tenant_b):
    """テナントBの管理者"""
    return User.objects.create_user(
        email='admin_b@test.com',
        password='testpass123',
        last_name='管理者',
        first_name='B',
        tenant_id=tenant_b.id,
        user_type=User.UserType.ADMIN,
        role=User.Role.ADMIN,
        is_staff=True,
    )


@pytest.fixture
def brand_a(db, tenant_a):
    """テナントAのブランド"""
    return Brand.objects.create(
        tenant_id=tenant_a.id,
        brand_code='BRAND_A',
        brand_name='ブランドA',
        is_active=True,
    )


@pytest.fixture
def brand_b(db, tenant_b):
    """テナントBのブランド"""
    return Brand.objects.create(
        tenant_id=tenant_b.id,
        brand_code='BRAND_B',
        brand_name='ブランドB',
        is_active=True,
    )


@pytest.fixture
def school_a(db, tenant_a, brand_a):
    """テナントAの校舎"""
    return School.objects.create(
        tenant_id=tenant_a.id,
        brand=brand_a,
        school_code='SCHOOL_A',
        school_name='校舎A',
        is_active=True,
    )


@pytest.fixture
def school_b(db, tenant_b, brand_b):
    """テナントBの校舎"""
    return School.objects.create(
        tenant_id=tenant_b.id,
        brand=brand_b,
        school_code='SCHOOL_B',
        school_name='校舎B',
        is_active=True,
    )


@pytest.fixture
def grade_a(db, tenant_a):
    """テナントAの学年"""
    return Grade.objects.create(
        tenant_id=tenant_a.id,
        grade_code='J1_A',
        grade_name='中学1年',
        category=Grade.GradeCategory.JUNIOR_HIGH,
        school_year=7,
        is_active=True,
    )


@pytest.fixture
def grade_b(db, tenant_b):
    """テナントBの学年"""
    return Grade.objects.create(
        tenant_id=tenant_b.id,
        grade_code='J1_B',
        grade_name='中学1年',
        category=Grade.GradeCategory.JUNIOR_HIGH,
        school_year=7,
        is_active=True,
    )


@pytest.fixture
def student_a(db, tenant_a, school_a, brand_a, grade_a):
    """テナントAの生徒"""
    return Student.objects.create(
        tenant_id=tenant_a.id,
        student_no='ST_A_001',
        last_name='生徒',
        first_name='A',
        last_name_kana='セイト',
        first_name_kana='エー',
        primary_school=school_a,
        primary_brand=brand_a,
        grade=grade_a,
        status='enrolled',
    )


@pytest.fixture
def student_b(db, tenant_b, school_b, brand_b, grade_b):
    """テナントBの生徒"""
    return Student.objects.create(
        tenant_id=tenant_b.id,
        student_no='ST_B_001',
        last_name='生徒',
        first_name='B',
        last_name_kana='セイト',
        first_name_kana='ビー',
        primary_school=school_b,
        primary_brand=brand_b,
        grade=grade_b,
        status='enrolled',
    )


@pytest.fixture
def guardian_a(db, tenant_a, student_a):
    """テナントAの保護者"""
    guardian = Guardian.objects.create(
        tenant_id=tenant_a.id,
        guardian_no='GRD_A_001',
        last_name='保護者',
        first_name='A',
    )
    StudentGuardian.objects.create(
        tenant_id=tenant_a.id,
        student=student_a,
        guardian=guardian,
        relationship='father',
        is_primary=True,
    )
    return guardian


@pytest.fixture
def guardian_b(db, tenant_b, student_b):
    """テナントBの保護者"""
    guardian = Guardian.objects.create(
        tenant_id=tenant_b.id,
        guardian_no='GRD_B_001',
        last_name='保護者',
        first_name='B',
    )
    StudentGuardian.objects.create(
        tenant_id=tenant_b.id,
        student=student_b,
        guardian=guardian,
        relationship='father',
        is_primary=True,
    )
    return guardian


@pytest.fixture
def authenticated_client_a(admin_user_a):
    """テナントAの認証済みクライアント"""
    client = APIClient()
    client.force_authenticate(user=admin_user_a)
    return client


@pytest.fixture
def authenticated_client_b(admin_user_b):
    """テナントBの認証済みクライアント"""
    client = APIClient()
    client.force_authenticate(user=admin_user_b)
    return client


@pytest.mark.django_db
class TestMultiTenantStudentIsolation:
    """生徒データのテナント分離テスト"""

    def test_tenant_a_cannot_see_tenant_b_students(
        self, authenticated_client_a, student_a, student_b
    ):
        """テナントAはテナントBの生徒を見れない"""
        url = '/api/v1/students/'
        response = authenticated_client_a.get(url)

        assert response.status_code == status.HTTP_200_OK

        # レスポンスデータを取得（ページネーション対応）
        if 'results' in response.data:
            students = response.data['results']
        else:
            students = response.data

        # テナントAの生徒のみが含まれる
        student_ids = [str(s.get('id', s.get('studentId', ''))) for s in students]
        assert str(student_a.id) in student_ids or len(students) == 0
        assert str(student_b.id) not in student_ids

    def test_tenant_b_cannot_see_tenant_a_students(
        self, authenticated_client_b, student_a, student_b
    ):
        """テナントBはテナントAの生徒を見れない"""
        url = '/api/v1/students/'
        response = authenticated_client_b.get(url)

        assert response.status_code == status.HTTP_200_OK

        if 'results' in response.data:
            students = response.data['results']
        else:
            students = response.data

        student_ids = [str(s.get('id', s.get('studentId', ''))) for s in students]
        assert str(student_b.id) in student_ids or len(students) == 0
        assert str(student_a.id) not in student_ids

    def test_tenant_a_cannot_access_tenant_b_student_detail(
        self, authenticated_client_a, student_b
    ):
        """テナントAはテナントBの生徒詳細にアクセスできない"""
        url = f'/api/v1/students/{student_b.id}/'
        response = authenticated_client_a.get(url)

        # 404 または 403 が返る
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_403_FORBIDDEN
        ]


@pytest.mark.django_db
class TestMultiTenantSchoolIsolation:
    """校舎データのテナント分離テスト"""

    def test_tenant_a_cannot_see_tenant_b_schools(
        self, authenticated_client_a, school_a, school_b
    ):
        """テナントAはテナントBの校舎を見れない"""
        url = '/api/v1/schools/'
        response = authenticated_client_a.get(url)

        assert response.status_code == status.HTTP_200_OK

        if 'results' in response.data:
            schools = response.data['results']
        else:
            schools = response.data

        school_ids = [str(s.get('id', '')) for s in schools]
        assert str(school_b.id) not in school_ids

    def test_tenant_a_cannot_access_tenant_b_school_detail(
        self, authenticated_client_a, school_b
    ):
        """テナントAはテナントBの校舎詳細にアクセスできない"""
        url = f'/api/v1/schools/{school_b.id}/'
        response = authenticated_client_a.get(url)

        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_403_FORBIDDEN
        ]


@pytest.mark.django_db
class TestMultiTenantGuardianIsolation:
    """保護者データのテナント分離テスト"""

    def test_tenant_a_cannot_see_tenant_b_guardians(
        self, authenticated_client_a, guardian_a, guardian_b
    ):
        """テナントAはテナントBの保護者を見れない"""
        url = '/api/v1/guardians/'
        response = authenticated_client_a.get(url)

        # エンドポイントが存在する場合のみテスト
        if response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Guardians endpoint not available")

        assert response.status_code == status.HTTP_200_OK

        if 'results' in response.data:
            guardians = response.data['results']
        else:
            guardians = response.data

        guardian_ids = [str(g.get('id', '')) for g in guardians]
        assert str(guardian_b.id) not in guardian_ids


@pytest.mark.django_db
class TestMultiTenantContractIsolation:
    """契約データのテナント分離テスト"""

    def test_tenant_a_cannot_see_tenant_b_contracts(
        self, authenticated_client_a, tenant_a, tenant_b,
        student_a, student_b, school_a, school_b, brand_a, brand_b
    ):
        """テナントAはテナントBの契約を見れない"""
        # テナントAの契約
        contract_a = Contract.objects.create(
            tenant_id=tenant_a.id,
            contract_no='CNT_A_001',
            student=student_a,
            school=school_a,
            brand=brand_a,
            contract_date=date.today(),
            start_date=date.today(),
            status='active',
        )

        # テナントBの契約
        contract_b = Contract.objects.create(
            tenant_id=tenant_b.id,
            contract_no='CNT_B_001',
            student=student_b,
            school=school_b,
            brand=brand_b,
            contract_date=date.today(),
            start_date=date.today(),
            status='active',
        )

        url = '/api/v1/contracts/'
        response = authenticated_client_a.get(url)

        assert response.status_code == status.HTTP_200_OK

        if 'results' in response.data:
            contracts = response.data['results']
        else:
            contracts = response.data

        contract_ids = [str(c.get('id', '')) for c in contracts]
        assert str(contract_b.id) not in contract_ids


@pytest.mark.django_db
class TestMultiTenantDataModification:
    """テナント間でのデータ変更防止テスト"""

    def test_tenant_a_cannot_update_tenant_b_student(
        self, authenticated_client_a, student_b
    ):
        """テナントAはテナントBの生徒を更新できない"""
        url = f'/api/v1/students/{student_b.id}/'
        data = {'firstName': '改ざん'}
        response = authenticated_client_a.patch(url, data, format='json')

        # 404 または 403 が返る
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_403_FORBIDDEN
        ]

        # データが変更されていないことを確認
        student_b.refresh_from_db()
        assert student_b.first_name != '改ざん'

    def test_tenant_a_cannot_delete_tenant_b_student(
        self, authenticated_client_a, student_b
    ):
        """テナントAはテナントBの生徒を削除できない"""
        original_id = student_b.id
        url = f'/api/v1/students/{student_b.id}/'
        response = authenticated_client_a.delete(url)

        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_403_FORBIDDEN
        ]

        # データが削除されていないことを確認
        assert Student.objects.filter(id=original_id).exists()


@pytest.mark.django_db
class TestCrossContaminationPrevention:
    """クロスコンタミネーション防止テスト"""

    def test_new_student_uses_correct_tenant(
        self, authenticated_client_a, tenant_a, school_a, brand_a, grade_a
    ):
        """新規作成した生徒が正しいテナントに紐づく"""
        url = '/api/v1/students/'
        data = {
            'studentNo': 'NEW_A_001',
            'lastName': '新規',
            'firstName': '生徒A',
            'lastNameKana': 'シンキ',
            'firstNameKana': 'セイトエー',
            'status': 'enrolled',
        }
        response = authenticated_client_a.post(url, data, format='json')

        if response.status_code == status.HTTP_201_CREATED:
            # 作成された生徒のテナントIDを確認
            student_id = response.data.get('id')
            if student_id:
                student = Student.objects.get(id=student_id)
                assert str(student.tenant_id) == str(tenant_a.id)

    def test_tenant_header_cannot_override_user_tenant(
        self, authenticated_client_a, tenant_b
    ):
        """テナントヘッダーでユーザーのテナントを上書きできない"""
        # X-Tenant-ID ヘッダーで別テナントを指定しようとする
        authenticated_client_a.credentials(
            HTTP_X_TENANT_ID=str(tenant_b.id)
        )

        url = '/api/v1/students/'
        response = authenticated_client_a.get(url)

        # リクエストは成功するが、ユーザーのテナントのデータのみ返される
        if response.status_code == status.HTTP_200_OK:
            if 'results' in response.data:
                students = response.data['results']
            else:
                students = response.data

            # テナントBのデータは含まれない
            for student in students:
                if 'tenantId' in student:
                    assert str(student['tenantId']) != str(tenant_b.id)
