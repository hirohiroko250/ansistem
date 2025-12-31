"""
請求フロー統合テスト

請求書生成 → 入金 → 相殺の一連のフローをテストします。
ビジネスクリティカルなテストです。

実行方法:
    docker compose -f docker-compose.dev.yml exec backend pytest tests/test_billing_flow.py -v

注意:
    これらのテストはデータベースを必要とします。
    マイグレーション互換性問題が解決するまでDockerコンテナ内で実行してください。
"""
import pytest

# 統合テスト - PostgreSQL環境でのみ実行
import os
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get('USE_POSTGRES_FOR_TESTS'),
        reason="Requires PostgreSQL. Set USE_POSTGRES_FOR_TESTS=1 or run in Docker."
    ),
]
from datetime import date, timedelta
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant
from apps.schools.models import Brand, School, Grade
from apps.students.models import Student, Guardian, StudentGuardian
from apps.contracts.models import Product, Course, Contract
from apps.billing.models import (
    Invoice,
    InvoiceLine,
    Payment,
    GuardianBalance,
    OffsetLog,
    BillingPeriod,
)

User = get_user_model()


@pytest.fixture
def billing_tenant(db):
    """請求テスト用テナント"""
    return Tenant.objects.create(
        tenant_code='BILLING_TEST',
        tenant_name='請求テストテナント',
        plan_type=Tenant.PlanType.STANDARD,
        is_active=True,
    )


@pytest.fixture
def billing_admin(db, billing_tenant):
    """請求テスト用管理者"""
    return User.objects.create_user(
        email='billing_admin@test.com',
        password='testpass123',
        last_name='請求',
        first_name='管理者',
        tenant_id=billing_tenant.id,
        user_type=User.UserType.ADMIN,
        role=User.Role.ADMIN,
        is_staff=True,
    )


@pytest.fixture
def billing_brand(db, billing_tenant):
    """請求テスト用ブランド"""
    return Brand.objects.create(
        tenant_id=billing_tenant.id,
        brand_code='BILLING_BRAND',
        brand_name='請求テストブランド',
        is_active=True,
    )


@pytest.fixture
def billing_school(db, billing_tenant, billing_brand):
    """請求テスト用校舎"""
    return School.objects.create(
        tenant_id=billing_tenant.id,
        brand=billing_brand,
        school_code='BILLING_SCHOOL',
        school_name='請求テスト校舎',
        is_active=True,
    )


@pytest.fixture
def billing_grade(db, billing_tenant):
    """請求テスト用学年"""
    return Grade.objects.create(
        tenant_id=billing_tenant.id,
        grade_code='J1_BILL',
        grade_name='中学1年',
        category=Grade.GradeCategory.JUNIOR_HIGH,
        school_year=7,
        is_active=True,
    )


@pytest.fixture
def billing_student(db, billing_tenant, billing_school, billing_brand, billing_grade):
    """請求テスト用生徒"""
    return Student.objects.create(
        tenant_id=billing_tenant.id,
        student_no='BILL_ST_001',
        last_name='請求',
        first_name='生徒',
        last_name_kana='セイキュウ',
        first_name_kana='セイト',
        primary_school=billing_school,
        primary_brand=billing_brand,
        grade=billing_grade,
        status='enrolled',
    )


@pytest.fixture
def billing_guardian(db, billing_tenant, billing_student):
    """請求テスト用保護者"""
    guardian = Guardian.objects.create(
        tenant_id=billing_tenant.id,
        guardian_no='BILL_GRD_001',
        last_name='請求',
        first_name='保護者',
    )
    StudentGuardian.objects.create(
        tenant_id=billing_tenant.id,
        student=billing_student,
        guardian=guardian,
        relationship='father',
        is_primary=True,
    )
    return guardian


@pytest.fixture
def billing_product(db, billing_tenant):
    """請求テスト用商品"""
    return Product.objects.create(
        tenant_id=billing_tenant.id,
        product_code='BILL_PROD',
        product_name='テスト月謝',
        product_type='regular',
        billing_type='monthly',
        base_price=Decimal('10000'),
        is_active=True,
    )


@pytest.fixture
def billing_contract(
    db, billing_tenant, billing_student, billing_school, billing_brand
):
    """請求テスト用契約"""
    return Contract.objects.create(
        tenant_id=billing_tenant.id,
        contract_no='BILL_CNT_001',
        student=billing_student,
        school=billing_school,
        brand=billing_brand,
        contract_date=date.today() - timedelta(days=30),
        start_date=date.today() - timedelta(days=30),
        status='active',
    )


@pytest.fixture
def billing_period(db, billing_tenant):
    """請求テスト用請求期間"""
    today = date.today()
    return BillingPeriod.objects.create(
        tenant_id=billing_tenant.id,
        year=today.year,
        month=today.month,
        billing_date=date(today.year, today.month, 27),
        due_date=date(today.year, today.month, 27) + timedelta(days=30),
        status='open',
    )


@pytest.fixture
def billing_client(billing_admin):
    """請求テスト用認証済みクライアント"""
    client = APIClient()
    client.force_authenticate(user=billing_admin)
    return client


@pytest.mark.django_db
class TestInvoiceCreation:
    """請求書作成テスト"""

    def test_list_invoices(self, billing_client):
        """請求書一覧取得"""
        url = '/api/v1/billing/invoices/'
        response = billing_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_create_invoice_directly(
        self, db, billing_tenant, billing_guardian, billing_period
    ):
        """請求書の直接作成（モデルレベル）"""
        invoice = Invoice.objects.create(
            tenant_id=billing_tenant.id,
            invoice_no='INV_TEST_001',
            guardian=billing_guardian,
            billing_period=billing_period,
            billing_year=billing_period.year,
            billing_month=billing_period.month,
            subtotal=Decimal('10000'),
            tax_amount=Decimal('1000'),
            total_amount=Decimal('11000'),
            status='pending',
        )

        assert invoice.id is not None
        assert invoice.total_amount == Decimal('11000')
        assert invoice.status == 'pending'

    def test_invoice_with_lines(
        self, db, billing_tenant, billing_guardian, billing_period, billing_product
    ):
        """請求明細付き請求書作成"""
        invoice = Invoice.objects.create(
            tenant_id=billing_tenant.id,
            invoice_no='INV_TEST_002',
            guardian=billing_guardian,
            billing_period=billing_period,
            billing_year=billing_period.year,
            billing_month=billing_period.month,
            subtotal=Decimal('10000'),
            tax_amount=Decimal('1000'),
            total_amount=Decimal('11000'),
            status='pending',
        )

        line = InvoiceLine.objects.create(
            tenant_id=billing_tenant.id,
            invoice=invoice,
            product=billing_product,
            description='テスト月謝 1月分',
            quantity=1,
            unit_price=Decimal('10000'),
            amount=Decimal('10000'),
            tax_rate=Decimal('0.10'),
            tax_amount=Decimal('1000'),
        )

        assert invoice.lines.count() == 1
        assert line.amount == Decimal('10000')


@pytest.mark.django_db
class TestPaymentProcessing:
    """入金処理テスト"""

    def test_list_payments(self, billing_client):
        """入金一覧取得"""
        url = '/api/v1/billing/payments/'
        response = billing_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_create_payment_directly(
        self, db, billing_tenant, billing_guardian, billing_period
    ):
        """入金の直接作成（モデルレベル）"""
        # 請求書作成
        invoice = Invoice.objects.create(
            tenant_id=billing_tenant.id,
            invoice_no='INV_PAY_001',
            guardian=billing_guardian,
            billing_period=billing_period,
            billing_year=billing_period.year,
            billing_month=billing_period.month,
            subtotal=Decimal('10000'),
            tax_amount=Decimal('1000'),
            total_amount=Decimal('11000'),
            status='pending',
        )

        # 入金作成
        payment = Payment.objects.create(
            tenant_id=billing_tenant.id,
            invoice=invoice,
            guardian=billing_guardian,
            payment_date=date.today(),
            amount=Decimal('11000'),
            payment_method='bank_transfer',
            status='completed',
        )

        assert payment.id is not None
        assert payment.amount == Decimal('11000')

    def test_partial_payment(
        self, db, billing_tenant, billing_guardian, billing_period
    ):
        """一部入金"""
        invoice = Invoice.objects.create(
            tenant_id=billing_tenant.id,
            invoice_no='INV_PARTIAL_001',
            guardian=billing_guardian,
            billing_period=billing_period,
            billing_year=billing_period.year,
            billing_month=billing_period.month,
            subtotal=Decimal('10000'),
            tax_amount=Decimal('1000'),
            total_amount=Decimal('11000'),
            status='pending',
        )

        # 一部入金
        payment = Payment.objects.create(
            tenant_id=billing_tenant.id,
            invoice=invoice,
            guardian=billing_guardian,
            payment_date=date.today(),
            amount=Decimal('5000'),
            payment_method='bank_transfer',
            status='completed',
        )

        # 残高確認
        remaining = invoice.total_amount - payment.amount
        assert remaining == Decimal('6000')


@pytest.mark.django_db
class TestGuardianBalance:
    """預り金管理テスト"""

    def test_list_balances(self, billing_client):
        """預り金一覧取得"""
        url = '/api/v1/billing/balances/'
        response = billing_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_create_balance_directly(self, db, billing_tenant, billing_guardian):
        """預り金の直接作成（モデルレベル）"""
        balance = GuardianBalance.objects.create(
            tenant_id=billing_tenant.id,
            guardian=billing_guardian,
            balance=Decimal('10000'),
        )

        assert balance.id is not None
        assert balance.balance == Decimal('10000')

    def test_deposit_increases_balance(self, db, billing_tenant, billing_guardian):
        """入金で預り金が増加"""
        # 初期残高
        balance, _ = GuardianBalance.objects.get_or_create(
            tenant_id=billing_tenant.id,
            guardian=billing_guardian,
            defaults={'balance': Decimal('0')}
        )
        initial = balance.balance

        # 入金
        deposit_amount = Decimal('5000')
        balance.balance += deposit_amount
        balance.save()

        balance.refresh_from_db()
        assert balance.balance == initial + deposit_amount


@pytest.mark.django_db
class TestOffsetProcess:
    """相殺処理テスト"""

    def test_list_offset_logs(self, billing_client):
        """相殺ログ一覧取得"""
        url = '/api/v1/billing/offset-logs/'
        response = billing_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_offset_from_balance(
        self, db, billing_tenant, billing_guardian, billing_period
    ):
        """預り金からの相殺"""
        # 預り金を設定
        balance = GuardianBalance.objects.create(
            tenant_id=billing_tenant.id,
            guardian=billing_guardian,
            balance=Decimal('20000'),
        )

        # 請求書作成
        invoice = Invoice.objects.create(
            tenant_id=billing_tenant.id,
            invoice_no='INV_OFFSET_001',
            guardian=billing_guardian,
            billing_period=billing_period,
            billing_year=billing_period.year,
            billing_month=billing_period.month,
            subtotal=Decimal('10000'),
            tax_amount=Decimal('1000'),
            total_amount=Decimal('11000'),
            status='pending',
        )

        # 相殺処理（ロジックのシミュレーション）
        offset_amount = min(balance.balance, invoice.total_amount)

        # 相殺ログ作成
        offset_log = OffsetLog.objects.create(
            tenant_id=billing_tenant.id,
            guardian=billing_guardian,
            invoice=invoice,
            offset_amount=offset_amount,
            balance_before=balance.balance,
            balance_after=balance.balance - offset_amount,
        )

        # 預り金を減らす
        balance.balance -= offset_amount
        balance.save()

        assert offset_log.offset_amount == Decimal('11000')
        assert balance.balance == Decimal('9000')

    def test_partial_offset(
        self, db, billing_tenant, billing_guardian, billing_period
    ):
        """一部相殺（預り金不足）"""
        # 預り金を設定（請求額より少ない）
        balance = GuardianBalance.objects.create(
            tenant_id=billing_tenant.id,
            guardian=billing_guardian,
            balance=Decimal('5000'),
        )

        # 請求書作成
        invoice = Invoice.objects.create(
            tenant_id=billing_tenant.id,
            invoice_no='INV_PART_OFFSET_001',
            guardian=billing_guardian,
            billing_period=billing_period,
            billing_year=billing_period.year,
            billing_month=billing_period.month,
            subtotal=Decimal('10000'),
            tax_amount=Decimal('1000'),
            total_amount=Decimal('11000'),
            status='pending',
        )

        # 相殺処理（預り金全額使用）
        offset_amount = min(balance.balance, invoice.total_amount)

        offset_log = OffsetLog.objects.create(
            tenant_id=billing_tenant.id,
            guardian=billing_guardian,
            invoice=invoice,
            offset_amount=offset_amount,
            balance_before=balance.balance,
            balance_after=Decimal('0'),
        )

        balance.balance = Decimal('0')
        balance.save()

        remaining = invoice.total_amount - offset_amount

        assert offset_amount == Decimal('5000')
        assert remaining == Decimal('6000')
        assert balance.balance == Decimal('0')


@pytest.mark.django_db
class TestBillingFlowIntegration:
    """請求フロー統合テスト"""

    def test_complete_billing_flow(
        self, db, billing_tenant, billing_guardian, billing_period, billing_product
    ):
        """完全な請求フロー：請求書生成 → 入金 → 消込"""
        # Step 1: 請求書生成
        invoice = Invoice.objects.create(
            tenant_id=billing_tenant.id,
            invoice_no='INV_FLOW_001',
            guardian=billing_guardian,
            billing_period=billing_period,
            billing_year=billing_period.year,
            billing_month=billing_period.month,
            subtotal=Decimal('10000'),
            tax_amount=Decimal('1000'),
            total_amount=Decimal('11000'),
            status='pending',
        )

        InvoiceLine.objects.create(
            tenant_id=billing_tenant.id,
            invoice=invoice,
            product=billing_product,
            description='月謝',
            quantity=1,
            unit_price=Decimal('10000'),
            amount=Decimal('10000'),
            tax_rate=Decimal('0.10'),
            tax_amount=Decimal('1000'),
        )

        assert invoice.status == 'pending'

        # Step 2: 入金
        payment = Payment.objects.create(
            tenant_id=billing_tenant.id,
            invoice=invoice,
            guardian=billing_guardian,
            payment_date=date.today(),
            amount=Decimal('11000'),
            payment_method='bank_transfer',
            status='completed',
        )

        # Step 3: 請求書ステータス更新（全額入金済み）
        total_paid = Payment.objects.filter(
            invoice=invoice,
            status='completed'
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

        if total_paid >= invoice.total_amount:
            invoice.status = 'paid'
            invoice.save()

        invoice.refresh_from_db()
        assert invoice.status == 'paid'

    def test_overpayment_to_balance(
        self, db, billing_tenant, billing_guardian, billing_period
    ):
        """過払い分が預り金に入る"""
        # 請求書作成（10,000円）
        invoice = Invoice.objects.create(
            tenant_id=billing_tenant.id,
            invoice_no='INV_OVER_001',
            guardian=billing_guardian,
            billing_period=billing_period,
            billing_year=billing_period.year,
            billing_month=billing_period.month,
            subtotal=Decimal('10000'),
            tax_amount=Decimal('0'),
            total_amount=Decimal('10000'),
            status='pending',
        )

        # 過払い入金（12,000円）
        payment_amount = Decimal('12000')
        overpayment = payment_amount - invoice.total_amount

        # 請求書への入金（10,000円分）
        Payment.objects.create(
            tenant_id=billing_tenant.id,
            invoice=invoice,
            guardian=billing_guardian,
            payment_date=date.today(),
            amount=invoice.total_amount,
            payment_method='bank_transfer',
            status='completed',
        )

        # 過払い分を預り金に
        balance, _ = GuardianBalance.objects.get_or_create(
            tenant_id=billing_tenant.id,
            guardian=billing_guardian,
            defaults={'balance': Decimal('0')}
        )
        balance.balance += overpayment
        balance.save()

        assert overpayment == Decimal('2000')
        assert balance.balance == Decimal('2000')


# モデルのSum用にインポート
from django.db import models
