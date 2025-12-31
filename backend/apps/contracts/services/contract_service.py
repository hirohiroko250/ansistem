"""
Contract Service - 契約管理サービス
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class ContractService:
    """契約管理サービス

    契約の作成・更新・ステータス変更を一元管理
    """

    # ステータス定義
    STATUS_DRAFT = 'draft'
    STATUS_PENDING = 'pending'
    STATUS_ACTIVE = 'active'
    STATUS_PAUSED = 'paused'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'

    def __init__(self, contract):
        self.contract = contract
        self.tenant_id = contract.tenant_id

    def activate(self) -> bool:
        """契約を有効化"""
        from ..models import Contract

        self.contract.status = Contract.Status.ACTIVE
        self.contract.save()

        logger.info(f"Contract {self.contract.id} activated")
        return True

    def pause(self) -> bool:
        """契約を休止"""
        from ..models import Contract

        self.contract.status = Contract.Status.PAUSED
        self.contract.save()

        logger.info(f"Contract {self.contract.id} paused")
        return True

    def cancel(self, end_date=None) -> bool:
        """契約を解約"""
        from ..models import Contract

        self.contract.status = Contract.Status.CANCELLED
        self.contract.end_date = end_date or timezone.now().date()
        self.contract.save()

        logger.info(f"Contract {self.contract.id} cancelled")
        return True

    @transaction.atomic
    def update_textbooks(self, textbook_ids: list) -> bool:
        """選択教材を更新

        Args:
            textbook_ids: 選択する教材商品IDのリスト

        Returns:
            成功した場合 True
        """
        from ..models import Product

        # 教材商品のみ許可
        valid_textbooks = Product.objects.filter(
            id__in=textbook_ids,
            item_type=Product.ItemType.TEXTBOOK
        )

        # 選択教材を更新
        self.contract.selected_textbooks.set(valid_textbooks)

        # 月額合計を再計算
        self._recalculate_monthly_total()

        logger.info(
            f"Contract {self.contract.id} textbooks updated: "
            f"{len(valid_textbooks)} items"
        )

        return True

    def _recalculate_monthly_total(self):
        """月額合計を再計算（選択教材のみ含む）"""
        from ..models import Product

        if not self.contract.course:
            return

        total = Decimal('0')
        selected_textbook_ids = set(
            self.contract.selected_textbooks.values_list('id', flat=True)
        )

        for ci in self.contract.course.course_items.filter(is_active=True):
            if not ci.product:
                continue

            # 教材費の場合は選択されているもののみ
            if ci.product.item_type == Product.ItemType.TEXTBOOK:
                if ci.product_id not in selected_textbook_ids:
                    continue

            total += ci.get_price() * ci.quantity

        self.contract.monthly_total = total
        self.contract.save()

    @staticmethod
    def generate_contract_no(tenant_id) -> str:
        """契約番号を生成

        Args:
            tenant_id: テナントID

        Returns:
            生成された契約番号
        """
        from ..models import Contract
        from datetime import datetime

        prefix = datetime.now().strftime('%Y%m')
        last_contract = Contract.objects.filter(
            tenant_id=tenant_id,
            contract_no__startswith=prefix
        ).order_by('-contract_no').first()

        if last_contract and last_contract.contract_no:
            try:
                seq = int(last_contract.contract_no[-4:]) + 1
            except ValueError:
                seq = 1
        else:
            seq = 1

        return f"{prefix}{seq:04d}"
