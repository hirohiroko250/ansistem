"""
BankTransferImport Search Mixin - 保護者検索機能
"""
from decimal import Decimal, InvalidOperation

from django.db import models
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.billing.models import Invoice, ConfirmedBilling


class BankTransferImportSearchMixin:
    """振込照合用保護者検索機能"""

    @extend_schema(summary='保護者検索（振込照合用）')
    @action(detail=False, methods=['get'])
    def search_guardians(self, request):
        """振込照合のための保護者検索

        検索パラメータ:
        - q: 名前（姓・名・カナ）で検索
        - guardian_no: 保護者番号で検索
        - amount: 金額で検索（未払い請求のbalance_dueと一致）
        """
        from apps.students.models import Guardian

        query = request.query_params.get('q', '')
        guardian_no = request.query_params.get('guardian_no', '')
        amount = request.query_params.get('amount', '')

        if not query and not guardian_no and not amount:
            return Response({'error': '検索条件を指定してください'}, status=400)

        tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)

        if not tenant_id:
            from apps.tenants.models import Tenant
            default_tenant = Tenant.objects.first()
            if default_tenant:
                tenant_id = default_tenant.id

        guardians = Guardian.objects.filter(deleted_at__isnull=True)
        if tenant_id:
            guardians = guardians.filter(tenant_id=tenant_id)

        if guardian_no:
            guardians = guardians.filter(
                models.Q(guardian_no__icontains=guardian_no) |
                models.Q(old_id__icontains=guardian_no)
            )

        if query and len(query) >= 1:
            guardians = guardians.filter(
                models.Q(last_name__icontains=query) |
                models.Q(first_name__icontains=query) |
                models.Q(last_name_kana__icontains=query) |
                models.Q(first_name_kana__icontains=query)
            )

        if amount:
            guardians = self._filter_by_amount(guardians, tenant_id, amount)
            if guardians is None:
                return Response({'error': '金額の形式が正しくありません'}, status=400)

        guardians = guardians[:20]

        results = self._build_guardian_results(guardians)

        return Response({'guardians': results})

    def _filter_by_amount(self, guardians, tenant_id, amount):
        """金額でフィルタ"""
        try:
            amount_decimal = Decimal(amount)
            guardian_ids_with_amount = Invoice.objects.filter(
                tenant_id=tenant_id,
                status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL, Invoice.Status.OVERDUE],
                balance_due=amount_decimal
            ).values_list('guardian_id', flat=True).distinct()

            cb_guardian_ids = ConfirmedBilling.objects.filter(
                tenant_id=tenant_id,
                status__in=[ConfirmedBilling.Status.CONFIRMED, ConfirmedBilling.Status.UNPAID, ConfirmedBilling.Status.PARTIAL],
                balance=amount_decimal
            ).values_list('guardian_id', flat=True).distinct()

            all_guardian_ids = set(guardian_ids_with_amount) | set(cb_guardian_ids)
            return guardians.filter(id__in=all_guardian_ids)
        except (ValueError, InvalidOperation):
            return None

    def _build_guardian_results(self, guardians):
        """保護者検索結果を構築"""
        results = []
        for g in guardians:
            invoices = Invoice.objects.filter(
                guardian=g,
                status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL, Invoice.Status.OVERDUE]
            ).order_by('-billing_year', '-billing_month')[:5]

            confirmed_billings = ConfirmedBilling.objects.filter(
                guardian=g,
                status__in=[ConfirmedBilling.Status.CONFIRMED, ConfirmedBilling.Status.UNPAID, ConfirmedBilling.Status.PARTIAL]
            ).order_by('-year', '-month')[:5]

            invoice_list = [{
                'invoiceId': str(inv.id),
                'invoiceNo': inv.invoice_no or '',
                'billingLabel': f"{inv.billing_year}年{inv.billing_month}月分",
                'totalAmount': int(inv.total_amount or 0),
                'balanceDue': int(inv.balance_due or 0),
                'status': inv.status,
                'statusDisplay': inv.get_status_display(),
                'source': 'invoice',
            } for inv in invoices]

            existing_months = {(inv.billing_year, inv.billing_month) for inv in invoices}
            for cb in confirmed_billings:
                if (cb.year, cb.month) not in existing_months:
                    invoice_list.append({
                        'invoiceId': str(cb.id),
                        'invoiceNo': f'CB-{cb.year}{cb.month:02d}',
                        'billingLabel': f"{cb.year}年{cb.month}月分",
                        'totalAmount': int(cb.total_amount or 0),
                        'balanceDue': int(cb.balance or 0),
                        'status': cb.status,
                        'statusDisplay': {'confirmed': '確定', 'unpaid': '未入金', 'partial': '一部入金'}.get(cb.status, cb.status),
                        'source': 'confirmed_billing',
                    })

            results.append({
                'guardianId': str(g.id),
                'guardianNo': g.guardian_no or g.old_id or '',
                'guardianName': g.full_name,
                'guardianNameKana': g.full_name_kana or '',
                'invoices': invoice_list,
            })

        return results
