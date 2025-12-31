"""
BankTransfer ViewSet - 振込入金管理API
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import models, transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view

from ..models import (
    Invoice, Payment, GuardianBalance, ConfirmedBilling,
    BankTransfer, BankTransferImport
)
from ..serializers import (
    BankTransferSerializer, BankTransferBulkMatchSerializer,
)


@extend_schema_view(
    list=extend_schema(summary='振込入金一覧'),
    retrieve=extend_schema(summary='振込入金詳細'),
)
class BankTransferViewSet(viewsets.ModelViewSet):
    """振込入金管理API"""
    serializer_class = BankTransferSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from apps.core.permissions import is_admin_user

        queryset = BankTransfer.objects.select_related(
            'guardian', 'invoice', 'matched_by'
        )

        if not is_admin_user(self.request.user):
            queryset = queryset.filter(tenant_id=self.request.user.tenant_id)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        batch_id = self.request.query_params.get('batch_id')
        if batch_id:
            queryset = queryset.filter(import_batch_id=batch_id)

        return queryset.order_by('-transfer_date', '-created_at')

    @extend_schema(summary='振込を保護者に照合')
    @action(detail=True, methods=['post'])
    def match(self, request, pk=None):
        """振込を保護者に照合する"""
        transfer = self.get_object()

        if transfer.status not in [BankTransfer.Status.PENDING, BankTransfer.Status.UNMATCHED]:
            return Response({'error': 'この振込は既に照合済みです'}, status=400)

        guardian_id = request.data.get('guardian_id')
        if not guardian_id:
            return Response({'error': 'guardian_id を指定してください'}, status=400)

        from apps.students.models import Guardian
        guardian = get_object_or_404(Guardian, id=guardian_id)

        transfer.match_to_guardian(guardian, request.user)

        return Response({
            'success': True,
            'message': f'{guardian.full_name}さんに照合しました',
            'transfer': BankTransferSerializer(transfer).data,
        })

    @extend_schema(summary='振込を請求書に適用して入金処理')
    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """振込を請求書に適用し、入金処理を行う

        invoice_idがある場合: 請求書に適用して消込
        invoice_idがない場合: 入金確認のみ（未消込入金として残る）
        """
        transfer = self.get_object()

        if transfer.status == BankTransfer.Status.APPLIED:
            return Response({'error': 'この振込は既に入金処理済みです'}, status=400)

        invoice_id = request.data.get('invoice_id')
        invoice = None
        if invoice_id:
            invoice = get_object_or_404(Invoice, id=invoice_id)

        guardian = invoice.guardian if invoice else transfer.guardian
        if not guardian:
            return Response({'error': '保護者が照合されていません。先に照合してください。'}, status=400)

        with transaction.atomic():
            payment_no = Payment.generate_payment_no(transfer.tenant_id)
            payment = Payment.objects.create(
                tenant_id=transfer.tenant_id,
                payment_no=payment_no,
                guardian=guardian,
                invoice=invoice,
                payment_date=transfer.transfer_date,
                amount=transfer.amount,
                method=Payment.Method.BANK_TRANSFER,
                status=Payment.Status.SUCCESS if invoice else Payment.Status.PENDING,
                payer_name=transfer.payer_name,
                bank_name=transfer.source_bank_name,
                notes=f'振込インポート: {transfer.import_batch_id}',
                registered_by=request.user,
            )

            if invoice:
                invoice.paid_amount += transfer.amount
                invoice.balance_due = invoice.total_amount - invoice.paid_amount
                if invoice.balance_due <= 0:
                    invoice.status = Invoice.Status.PAID
                elif invoice.paid_amount > 0:
                    invoice.status = Invoice.Status.PARTIAL
                invoice.save()

                transfer.apply_to_invoice(invoice, request.user)
                message = '入金処理を完了しました（消込済み）'
            else:
                transfer.status = BankTransfer.Status.APPLIED
                transfer.invoice = None
                if not transfer.matched_at:
                    transfer.matched_by = request.user
                    transfer.matched_at = timezone.now()
                transfer.save()
                message = '入金確認を完了しました（未消込）'

            confirmed_billings = ConfirmedBilling.objects.filter(
                guardian=guardian,
                status__in=[ConfirmedBilling.Status.CONFIRMED, ConfirmedBilling.Status.UNPAID, ConfirmedBilling.Status.PARTIAL],
            ).order_by(
                models.Case(
                    models.When(balance=transfer.amount, then=0),
                    default=1,
                ),
                'year',
                'month',
            )

            remaining_amount = transfer.amount
            for cb in confirmed_billings:
                if remaining_amount <= 0:
                    break
                apply_amount = min(remaining_amount, cb.balance)
                if apply_amount > 0:
                    cb.paid_amount += apply_amount
                    cb.balance = cb.total_amount - cb.paid_amount
                    if cb.balance <= 0:
                        cb.status = ConfirmedBilling.Status.PAID
                        cb.paid_at = timezone.now()
                    elif cb.paid_amount > 0:
                        cb.status = ConfirmedBilling.Status.PARTIAL
                    cb.save()
                    remaining_amount -= apply_amount

            balance_obj, _ = GuardianBalance.objects.get_or_create(
                tenant_id=transfer.tenant_id,
                guardian=guardian,
                defaults={'balance': 0}
            )
            balance_obj.add_payment(
                amount=transfer.amount,
                reason=f'銀行振込による入金（{transfer.payer_name}）',
                payment=payment,
            )

            if transfer.import_batch_id:
                try:
                    import_batch = BankTransferImport.objects.get(id=transfer.import_batch_id)
                    import_batch.update_counts()
                except BankTransferImport.DoesNotExist:
                    pass

        return Response({
            'success': True,
            'message': message,
            'transfer': BankTransferSerializer(transfer).data,
            'payment_id': str(payment.id),
            'matched_to_invoice': invoice is not None,
        })

    @extend_schema(summary='一括照合')
    @action(detail=False, methods=['post'])
    def bulk_match(self, request):
        """複数の振込を一括で照合する"""
        serializer = BankTransferBulkMatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.students.models import Guardian
        results = []

        with transaction.atomic():
            for match_data in serializer.validated_data['matches']:
                try:
                    transfer = BankTransfer.objects.get(id=match_data['transfer_id'])
                    guardian = Guardian.objects.get(id=match_data['guardian_id'])

                    if match_data.get('apply_payment') and match_data.get('invoice_id'):
                        invoice = Invoice.objects.get(id=match_data['invoice_id'])
                        payment = Payment.objects.create(
                            tenant_id=transfer.tenant_id,
                            guardian=guardian,
                            invoice=invoice,
                            payment_date=transfer.transfer_date,
                            amount=transfer.amount,
                            method=Payment.Method.BANK_TRANSFER,
                            status=Payment.Status.COMPLETED,
                            payer_name=transfer.payer_name,
                            bank_name=transfer.source_bank_name,
                            notes=f'振込インポート: {transfer.import_batch_id}',
                            registered_by=request.user,
                        )
                        invoice.paid_amount += transfer.amount
                        invoice.balance_due = invoice.total_amount - invoice.paid_amount
                        if invoice.balance_due <= 0:
                            invoice.status = Invoice.Status.PAID
                        elif invoice.paid_amount > 0:
                            invoice.status = Invoice.Status.PARTIAL
                        invoice.save()
                        transfer.apply_to_invoice(invoice, request.user)
                    else:
                        transfer.match_to_guardian(guardian, request.user)

                    results.append({
                        'transfer_id': str(transfer.id),
                        'success': True,
                    })
                except Exception as e:
                    results.append({
                        'transfer_id': str(match_data['transfer_id']),
                        'success': False,
                        'error': str(e),
                    })

        return Response({
            'results': results,
            'success_count': len([r for r in results if r['success']]),
            'error_count': len([r for r in results if not r['success']]),
        })
