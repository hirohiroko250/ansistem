"""
Payment ViewSet - 入金管理API
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import models, transaction
from django.utils import timezone
from decimal import Decimal
from drf_spectacular.utils import extend_schema, extend_schema_view

from ..models import (
    Invoice, Payment, GuardianBalance, ConfirmedBilling
)
from ..serializers import (
    InvoiceSerializer, PaymentSerializer, PaymentCreateSerializer,
    DirectDebitResultSerializer,
)

logger = logging.getLogger(__name__)


class PaymentViewSet(viewsets.ModelViewSet):
    """入金管理API"""
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(
            tenant_id=self.request.user.tenant_id
        ).select_related('guardian', 'invoice', 'registered_by')

    @extend_schema(summary='入金登録', request=PaymentCreateSerializer)
    @action(detail=False, methods=['post'])
    def register(self, request):
        """入金を登録"""
        from apps.students.models import Guardian

        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            payment = Payment.objects.create(
                tenant_id=request.user.tenant_id,
                payment_no=Payment.generate_payment_no(request.user.tenant_id),
                guardian_id=data['guardian_id'],
                invoice_id=data.get('invoice_id'),
                payment_date=data['payment_date'],
                amount=data['amount'],
                method=data['method'],
                status=Payment.Status.SUCCESS,
                payer_name=data.get('payer_name', ''),
                bank_name=data.get('bank_name', ''),
                notes=data.get('notes', ''),
                registered_by=request.user,
            )

            # 請求書に入金を適用
            payment.apply_to_invoice()

            # ConfirmedBillingも更新
            guardian = Guardian.objects.get(id=data['guardian_id'])
            payment_amount = data['amount']

            confirmed_billings = ConfirmedBilling.objects.filter(
                guardian=guardian,
                status__in=[ConfirmedBilling.Status.CONFIRMED, ConfirmedBilling.Status.UNPAID, ConfirmedBilling.Status.PARTIAL],
            ).order_by(
                models.Case(
                    models.When(balance=payment_amount, then=0),
                    default=1,
                ),
                'year',
                'month',
            )

            remaining_amount = payment_amount
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

            # GuardianBalanceに入金を記録
            balance_obj, _ = GuardianBalance.objects.get_or_create(
                tenant_id=request.user.tenant_id,
                guardian=guardian,
                defaults={'balance': 0}
            )
            balance_obj.add_payment(
                amount=payment_amount,
                reason=f'手動入金登録',
                payment=payment,
            )

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary='口座振替結果取込', request=DirectDebitResultSerializer)
    @action(detail=False, methods=['post'])
    def import_debit_result(self, request):
        """口座振替結果を取込"""
        serializer = DirectDebitResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment = get_object_or_404(
            Payment,
            id=serializer.validated_data['payment_id'],
            tenant_id=request.user.tenant_id
        )

        result_code = serializer.validated_data['result_code']
        payment.debit_result_code = result_code
        payment.debit_result_message = serializer.validated_data.get('result_message', '')

        with transaction.atomic():
            # 結果コードによってステータスを更新
            if result_code == '0':  # 成功
                payment.status = Payment.Status.SUCCESS
                payment.apply_to_invoice()

                # ConfirmedBillingも更新
                if payment.guardian:
                    confirmed_billings = ConfirmedBilling.objects.filter(
                        guardian=payment.guardian,
                        status__in=[ConfirmedBilling.Status.CONFIRMED, ConfirmedBilling.Status.UNPAID, ConfirmedBilling.Status.PARTIAL],
                    ).order_by(
                        models.Case(
                            models.When(balance=payment.amount, then=0),
                            default=1,
                        ),
                        'year',
                        'month',
                    )

                    remaining_amount = payment.amount
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

                    # GuardianBalanceに入金を記録
                    balance_obj, _ = GuardianBalance.objects.get_or_create(
                        tenant_id=request.user.tenant_id,
                        guardian=payment.guardian,
                        defaults={'balance': 0}
                    )
                    balance_obj.add_payment(
                        amount=payment.amount,
                        reason=f'口座振替による入金',
                        payment=payment,
                    )
            else:
                payment.status = Payment.Status.FAILED

            payment.save()

        return Response(PaymentSerializer(payment).data)

    @extend_schema(summary='未消込入金一覧')
    @action(detail=False, methods=['get'])
    def unmatched(self, request):
        """未消込入金（請求書未紐付け）の一覧を取得"""
        payments = self.get_queryset().filter(
            invoice__isnull=True,
            status__in=[Payment.Status.SUCCESS, Payment.Status.PENDING]
        ).order_by('-payment_date')

        serializer = PaymentSerializer(payments, many=True)
        return Response({
            'count': payments.count(),
            'payments': serializer.data
        })

    @extend_schema(summary='入金消込候補を取得')
    @action(detail=True, methods=['get'])
    def match_candidates(self, request, pk=None):
        """指定入金に対する消込候補の請求書を取得

        金額と振込名義から候補をマッチング
        """
        payment = self.get_object()
        from apps.students.models import Guardian

        candidates = []

        # 金額で一致する請求書を探す
        amount_matches = Invoice.objects.filter(
            tenant_id=request.user.tenant_id,
            status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL],
            balance_due=payment.amount
        ).select_related('guardian')

        for invoice in amount_matches:
            candidates.append({
                'invoice': InvoiceSerializer(invoice).data,
                'match_type': 'amount',
                'match_score': 100,
                'match_reason': f'金額完全一致（¥{payment.amount:,.0f}）'
            })

        # 振込名義からカナ検索
        if payment.payer_name:
            # カナ名で保護者を検索
            payer_kana = payment.payer_name.strip()
            name_matches = Guardian.objects.filter(
                tenant_id=request.user.tenant_id,
                full_name_kana__icontains=payer_kana
            )

            for guardian in name_matches:
                # この保護者の未払い請求書を取得
                guardian_invoices = Invoice.objects.filter(
                    guardian=guardian,
                    status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL]
                )
                for invoice in guardian_invoices:
                    # 既に候補に入っていない場合追加
                    existing_ids = [c['invoice']['id'] for c in candidates]
                    if str(invoice.id) not in existing_ids:
                        score = 80
                        if invoice.balance_due == payment.amount:
                            score = 100
                        candidates.append({
                            'invoice': InvoiceSerializer(invoice).data,
                            'match_type': 'name',
                            'match_score': score,
                            'match_reason': f'振込名義一致（{payer_kana}）'
                        })

        # スコア順にソート
        candidates.sort(key=lambda x: x['match_score'], reverse=True)

        return Response({
            'payment': PaymentSerializer(payment).data,
            'candidates': candidates[:20]  # 上位20件まで
        })

    @extend_schema(summary='入金を請求書に消込')
    @action(detail=True, methods=['post'])
    def match_invoice(self, request, pk=None):
        """入金を指定の請求書に消込"""
        payment = self.get_object()
        invoice_id = request.data.get('invoice_id')

        if not invoice_id:
            return Response(
                {'error': '請求書IDが必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        invoice = get_object_or_404(
            Invoice,
            id=invoice_id,
            tenant_id=request.user.tenant_id
        )

        if payment.invoice:
            return Response(
                {'error': 'この入金は既に消込済みです'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            payment.invoice = invoice
            payment.guardian = invoice.guardian
            payment.save()

            # 請求書に入金を適用
            payment.apply_to_invoice()

            # ConfirmedBillingも更新（入金を対応する請求月に適用）
            if invoice.guardian:
                confirmed_billings = ConfirmedBilling.objects.filter(
                    guardian=invoice.guardian,
                    status__in=[ConfirmedBilling.Status.CONFIRMED, ConfirmedBilling.Status.UNPAID, ConfirmedBilling.Status.PARTIAL],
                ).order_by(
                    models.Case(
                        models.When(balance=payment.amount, then=0),
                        default=1,
                    ),
                    'year',
                    'month',
                )

                remaining_amount = payment.amount
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

        return Response({
            'success': True,
            'payment': PaymentSerializer(payment).data,
            'invoice': InvoiceSerializer(invoice).data
        })
