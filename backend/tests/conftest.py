"""
pytest設定とフィクスチャ
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.tenants.models import Tenant, Employee
from apps.schools.models import Brand, School, Grade, Subject
from apps.students.models import Student

User = get_user_model()


@pytest.fixture
def api_client():
    """APIクライアントを提供"""
    return APIClient()


@pytest.fixture
def tenant(db):
    """テストテナントを作成"""
    return Tenant.objects.create(
        tenant_code='TEST_TENANT',
        tenant_name='テストテナント',
        plan_type=Tenant.PlanType.STANDARD,
        is_active=True,
    )


@pytest.fixture
def admin_user(db, tenant):
    """管理者ユーザーを作成"""
    user = User.objects.create_user(
        email='testadmin@test.com',
        password='testpass123',
        last_name='テスト',
        first_name='管理者',
        tenant_id=tenant.id,
        user_type=User.UserType.ADMIN,
        role=User.Role.ADMIN,
        is_staff=True,
    )
    return user


@pytest.fixture
def instructor_user(db, tenant):
    """講師ユーザーを作成"""
    user = User.objects.create_user(
        email='testinstructor@test.com',
        password='testpass123',
        last_name='テスト',
        first_name='講師',
        tenant_id=tenant.id,
        user_type=User.UserType.TEACHER,
        role=User.Role.TEACHER,
    )
    return user


@pytest.fixture
def parent_user(db, tenant):
    """保護者ユーザーを作成"""
    user = User.objects.create_user(
        email='testparent@test.com',
        password='testpass123',
        last_name='テスト',
        first_name='保護者',
        tenant_id=tenant.id,
        user_type=User.UserType.GUARDIAN,
        role=User.Role.USER,
    )
    return user


@pytest.fixture
def authenticated_client(api_client, admin_user):
    """認証済みクライアントを提供"""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def brand(db, tenant):
    """テストブランドを作成"""
    return Brand.objects.create(
        tenant_id=tenant.id,
        brand_code='TEST_BRAND',
        brand_name='テストブランド',
        is_active=True,
    )


@pytest.fixture
def school(db, tenant, brand):
    """テスト校舎を作成"""
    return School.objects.create(
        tenant_id=tenant.id,
        brand=brand,
        school_code='TEST_SCHOOL',
        school_name='テスト校舎',
        is_active=True,
    )


@pytest.fixture
def grade(db, tenant):
    """テスト学年を作成"""
    return Grade.objects.create(
        tenant_id=tenant.id,
        grade_code='J1',
        grade_name='中学1年',
        category=Grade.GradeCategory.JUNIOR_HIGH,
        school_year=7,
        is_active=True,
    )


@pytest.fixture
def subject(db, tenant):
    """テスト教科を作成"""
    return Subject.objects.create(
        tenant_id=tenant.id,
        subject_code='MATH',
        subject_name='数学',
        category=Subject.SubjectCategory.MAIN,
        is_active=True,
    )


@pytest.fixture
def student(db, tenant, school, brand, grade):
    """テスト生徒を作成"""
    return Student.objects.create(
        tenant_id=tenant.id,
        student_no='TEST001',
        last_name='テスト',
        first_name='生徒',
        last_name_kana='テスト',
        first_name_kana='セイト',
        primary_school=school,
        primary_brand=brand,
        grade=grade,
        status='active',
    )


@pytest.fixture
def staff(db, tenant, school, instructor_user):
    """テストスタッフ（社員）を作成"""
    employee = Employee.objects.create(
        tenant_id=tenant.id,
        employee_no='EMP001',
        last_name='テスト',
        first_name='講師',
        department='講師部門',
    )
    # 校舎を紐付け
    employee.schools.add(school)
    return employee
