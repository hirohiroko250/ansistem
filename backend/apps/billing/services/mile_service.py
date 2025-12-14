"""
MileCalculationService - マイル計算サービス

契約情報からマイルを計算し、MileTransactionテーブルに記録する。
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.billing.models import MileTransaction
from apps.contracts.models import Contract, ContractHistory


class MileCalculationService:
    """マイル計算・付与サービス"""

    # マイル使用の最低ポイント
    MIN_MILES_TO_USE = 4

    # 割引計算用定数
    INITIAL_DEDUCTION = 2  # 最初の控除ポイント
    POINTS_PER_DISCOUNT = 2  # 1割引単位あたりのポイント
    DISCOUNT_AMOUNT_PER_UNIT = 500  # 1割引単位あたりの金額

    @classmethod
    def calculate_monthly_miles(cls, contract):
        """契約から月間獲得マイル数を計算

        商品マスタのmileフィールドを参照して計算
        """
        total_miles = 0

        # コースから商品を取得してマイル計算
        if contract.course:
            for course_item in contract.course.course_items.filter(is_active=True):
                if course_item.product and course_item.product.mile:
                    total_miles += int(course_item.product.mile)

        # 生徒商品からもマイル計算
        for student_item in contract.student_items.filter(
            billing_month__startswith=timezone.now().strftime('%Y-%m')
        ):
            if student_item.product and student_item.product.mile:
                total_miles += int(student_item.product.mile)

        return total_miles

    @classmethod
    def earn_miles_for_contract(cls, contract, user=None, notes=''):
        """契約に対してマイルを付与

        Args:
            contract: 対象契約
            user: 操作ユーザー
            notes: 備考

        Returns:
            MileTransaction or None
        """
        if not contract.guardian:
            return None

        miles = cls.calculate_monthly_miles(contract)
        if miles <= 0:
            return None

        # 現在の残高を取得
        current_balance = MileTransaction.get_balance(contract.guardian)
        new_balance = current_balance + miles

        with transaction.atomic():
            # マイル取引を記録
            mile_tx = MileTransaction.objects.create(
                tenant_id=contract.tenant_id,
                guardian=contract.guardian,
                transaction_type=MileTransaction.TransactionType.EARN,
                miles=miles,
                balance_after=new_balance,
                earn_source=f'契約: {contract.contract_no}',
                earn_date=timezone.now().date(),
                notes=notes or f'{contract.course.course_name if contract.course else "契約"} からのマイル付与',
            )

            # 契約の月間獲得マイルを更新
            contract.mile_earn_monthly = miles
            contract.save(update_fields=['mile_earn_monthly', 'updated_at'])

            # 履歴を記録
            ContractHistory.log_change(
                contract=contract,
                action_type=ContractHistory.ActionType.MILE_APPLIED,
                change_summary=f'マイル付与: {miles}pt',
                user=user,
                is_system=user is None,
                mile_used=miles,
            )

        return mile_tx

    @classmethod
    def earn_miles_for_guardian(cls, guardian, billing_year, billing_month, user=None):
        """保護者の全契約に対してマイルを付与

        月次バッチ処理で使用

        Args:
            guardian: 対象保護者
            billing_year: 請求年
            billing_month: 請求月
            user: 操作ユーザー

        Returns:
            list of MileTransaction
        """
        transactions = []

        # 保護者の有効な契約を取得
        contracts = Contract.objects.filter(
            guardian=guardian,
            status=Contract.Status.ACTIVE,
            deleted_at__isnull=True,
        )

        total_miles = 0
        contract_names = []

        for contract in contracts:
            miles = cls.calculate_monthly_miles(contract)
            if miles > 0:
                total_miles += miles
                contract_names.append(
                    contract.course.course_name if contract.course else contract.contract_no
                )

        if total_miles <= 0:
            return transactions

        # 現在の残高を取得
        current_balance = MileTransaction.get_balance(guardian)
        new_balance = current_balance + total_miles

        with transaction.atomic():
            mile_tx = MileTransaction.objects.create(
                tenant_id=guardian.tenant_id,
                guardian=guardian,
                transaction_type=MileTransaction.TransactionType.EARN,
                miles=total_miles,
                balance_after=new_balance,
                earn_source=', '.join(contract_names),
                earn_date=timezone.now().date(),
                notes=f'{billing_year}年{billing_month}月分 マイル付与',
            )
            transactions.append(mile_tx)

        return transactions

    @classmethod
    def calculate_discount(cls, miles_to_use):
        """使用マイル数から割引額を計算

        4pt以上から利用可能
        最初の4ptで500円引（-2して開始）
        以後2ptごとに500円引

        例:
        - 4pt → 500円 ((4-2)/2 * 500 = 500)
        - 6pt → 1000円 ((6-2)/2 * 500 = 1000)
        - 8pt → 1500円 ((8-2)/2 * 500 = 1500)

        Returns:
            Decimal: 割引額
        """
        if miles_to_use < cls.MIN_MILES_TO_USE:
            return Decimal('0')

        usable_miles = miles_to_use - cls.INITIAL_DEDUCTION
        discount_units = usable_miles // cls.POINTS_PER_DISCOUNT
        return Decimal(discount_units * cls.DISCOUNT_AMOUNT_PER_UNIT)

    @classmethod
    def can_use_miles(cls, guardian):
        """マイル使用可能か判定

        条件: コース契約が2つ以上
        """
        active_contracts = Contract.objects.filter(
            guardian=guardian,
            status=Contract.Status.ACTIVE,
            deleted_at__isnull=True,
        ).count()
        return active_contracts >= 2

    @classmethod
    def use_miles(cls, guardian, miles, invoice=None, user=None, notes=''):
        """マイルを使用

        Args:
            guardian: 対象保護者
            miles: 使用マイル数
            invoice: 関連請求書
            user: 操作ユーザー
            notes: 備考

        Returns:
            tuple: (MileTransaction, discount_amount) or (None, 0)
        """
        if miles < cls.MIN_MILES_TO_USE:
            return None, Decimal('0')

        if not cls.can_use_miles(guardian):
            return None, Decimal('0')

        current_balance = MileTransaction.get_balance(guardian)
        if current_balance < miles:
            return None, Decimal('0')

        discount_amount = cls.calculate_discount(miles)
        new_balance = current_balance - miles

        with transaction.atomic():
            mile_tx = MileTransaction.objects.create(
                tenant_id=guardian.tenant_id,
                guardian=guardian,
                invoice=invoice,
                transaction_type=MileTransaction.TransactionType.USE,
                miles=-miles,
                balance_after=new_balance,
                discount_amount=discount_amount,
                notes=notes or 'マイル使用',
            )

        return mile_tx, discount_amount

    @classmethod
    def get_guardian_mile_balance(cls, guardian):
        """保護者のマイル残高を取得"""
        return MileTransaction.get_balance(guardian)

    @classmethod
    def get_guardian_mile_history(cls, guardian, limit=20):
        """保護者のマイル履歴を取得"""
        return MileTransaction.objects.filter(
            guardian=guardian
        ).order_by('-created_at')[:limit]

    @classmethod
    def process_monthly_miles(cls, tenant_id, billing_year, billing_month, user=None):
        """月次マイル付与バッチ処理

        全保護者に対して月次マイルを付与

        Args:
            tenant_id: テナントID
            billing_year: 請求年
            billing_month: 請求月
            user: 操作ユーザー

        Returns:
            dict: 処理結果 {
                'processed': 処理件数,
                'total_miles': 合計付与マイル,
                'errors': エラーリスト
            }
        """
        from apps.students.models import Guardian

        result = {
            'processed': 0,
            'total_miles': 0,
            'errors': [],
        }

        # 有効な契約を持つ保護者を取得
        guardians = Guardian.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True,
            contracts__status=Contract.Status.ACTIVE,
            contracts__deleted_at__isnull=True,
        ).distinct()

        for guardian in guardians:
            try:
                transactions = cls.earn_miles_for_guardian(
                    guardian, billing_year, billing_month, user
                )
                for tx in transactions:
                    result['processed'] += 1
                    result['total_miles'] += tx.miles
            except Exception as e:
                result['errors'].append({
                    'guardian_id': str(guardian.id),
                    'guardian_name': str(guardian),
                    'error': str(e),
                })

        return result
