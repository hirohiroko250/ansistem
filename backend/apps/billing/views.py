"""
Billing Views - 請求・入金・預り金・マイル管理API
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import (
    Invoice, InvoiceLine, Payment, GuardianBalance,
    OffsetLog, RefundRequest, MileTransaction
)
from .serializers import (
    InvoiceSerializer, InvoiceLineSerializer,
    InvoicePreviewSerializer, InvoiceConfirmSerializer,
    PaymentSerializer, PaymentCreateSerializer, DirectDebitResultSerializer,
    GuardianBalanceSerializer, BalanceDepositSerializer, BalanceOffsetSerializer,
    OffsetLogSerializer,
    RefundRequestSerializer, RefundRequestCreateSerializer, RefundApproveSerializer,
    MileTransactionSerializer, MileBalanceSerializer, MileCalculateSerializer, MileUseSerializer,
)


# =============================================================================
# Invoice ViewSet
# =============================================================================
@extend_schema_view(
    list=extend_schema(summary='請求書一覧'),
    retrieve=extend_schema(summary='請求書詳細'),
)
class InvoiceViewSet(viewsets.ModelViewSet):
    """請求書管理API"""
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from apps.core.permissions import is_admin_user

        queryset = Invoice.objects.select_related('guardian', 'confirmed_by').prefetch_related('lines')

        # 管理者以外はテナントでフィルタ
        if not is_admin_user(self.request.user):
            queryset = queryset.filter(tenant_id=self.request.user.tenant_id)

        # guardian_idでフィルタ
        guardian_id = self.request.query_params.get('guardian_id')
        if guardian_id:
            queryset = queryset.filter(guardian_id=guardian_id)

        return queryset

    @extend_schema(summary='請求書プレビュー', request=InvoicePreviewSerializer)
    @action(detail=False, methods=['post'])
    def preview(self, request):
        """請求書のプレビューを生成（確定前）"""
        serializer = InvoicePreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # TODO: 請求書プレビュー生成ロジック
        # - 保護者に紐づく生徒のStudentItemを取得
        # - 対象月の請求金額を計算
        # - マイル割引を計算（use_milesが指定されている場合）

        return Response({
            'message': 'プレビュー生成ロジックは後で実装',
            'data': serializer.validated_data,
        })

    @extend_schema(summary='請求書確定', request=InvoiceConfirmSerializer)
    @action(detail=False, methods=['post'])
    def confirm(self, request):
        """請求書を確定（下書き→発行済）"""
        serializer = InvoiceConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invoice = get_object_or_404(
            Invoice,
            id=serializer.validated_data['invoice_id'],
            tenant_id=request.user.tenant_id
        )

        if invoice.status != Invoice.Status.DRAFT:
            return Response(
                {'error': 'この請求書は既に確定されています'},
                status=status.HTTP_400_BAD_REQUEST
            )

        invoice.confirm(request.user)
        return Response(InvoiceSerializer(invoice).data)

    @extend_schema(summary='保護者の請求書一覧')
    @action(detail=False, methods=['get'], url_path='by-guardian/(?P<guardian_id>[^/.]+)')
    def by_guardian(self, request, guardian_id=None):
        """保護者IDで請求書を取得"""
        invoices = self.get_queryset().filter(guardian_id=guardian_id)
        serializer = self.get_serializer(invoices, many=True)
        return Response(serializer.data)

    @extend_schema(summary='引落データCSVエクスポート')
    @action(detail=False, methods=['get'], url_path='export-debit')
    def export_debit(self, request):
        """引落データをCSV形式でエクスポート（JACCS/UFJファクター/中京ファイナンス向け）"""
        import csv
        from django.http import HttpResponse
        from apps.students.models import Guardian

        billing_year = request.query_params.get('billing_year')
        billing_month = request.query_params.get('billing_month')
        provider = request.query_params.get('provider', 'jaccs')

        if not billing_year or not billing_month:
            return Response(
                {'error': '請求年月を指定してください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 対象請求書を取得（口座引落、発行済または一部入金）
        invoices = Invoice.objects.filter(
            tenant_id=request.user.tenant_id,
            billing_year=int(billing_year),
            billing_month=int(billing_month),
            payment_method=Invoice.PaymentMethod.DIRECT_DEBIT,
            status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL],
        ).select_related('guardian')

        # CSVレスポンス作成
        response = HttpResponse(content_type='text/csv; charset=shift_jis')
        filename = f"debit_export_{billing_year}{billing_month:0>2}_{provider}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)

        # ヘッダー行（全銀形式ベース）
        writer.writerow([
            '顧客番号', '氏名カナ', '銀行コード', '支店コード',
            '口座種別', '口座番号', '引落金額', '備考'
        ])

        # データ行
        for inv in invoices:
            guardian = inv.guardian
            if not guardian:
                continue

            # 引落金額（未払額）
            amount = int(inv.balance_due)
            if amount <= 0:
                continue

            writer.writerow([
                guardian.guardian_no or '',
                guardian.full_name_kana or f"{guardian.last_name_kana or ''}{guardian.first_name_kana or ''}",
                guardian.bank_code or '',
                guardian.branch_code or '',
                '1' if guardian.account_type == 'ordinary' else '2',
                guardian.account_number or '',
                amount,
                inv.invoice_no,
            ])

        return response

    @extend_schema(summary='引落結果CSVインポート')
    @action(detail=False, methods=['post'], url_path='import-debit-result')
    def import_debit_result(self, request):
        """引落結果CSVを取り込み、請求書と入金を更新"""
        import csv
        import io
        from apps.students.models import Guardian
        from .models import DirectDebitResult

        file = request.FILES.get('file')
        if not file:
            return Response(
                {'success': False, 'imported': 0, 'errors': ['ファイルが指定されていません']},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # CSVを読み込み（Shift-JIS想定）
            content = file.read().decode('shift_jis')
            reader = csv.DictReader(io.StringIO(content))

            imported = 0
            errors = []

            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):
                    try:
                        customer_code = row.get('顧客番号', '').strip()
                        result_code = row.get('結果コード', '').strip()
                        amount = row.get('引落金額', '0').strip()
                        invoice_no = row.get('備考', '').strip()

                        # 保護者を検索
                        guardian = Guardian.objects.filter(
                            tenant_id=request.user.tenant_id,
                            guardian_no=customer_code
                        ).first()

                        if not guardian:
                            errors.append(f"行{row_num}: 顧客番号 {customer_code} が見つかりません")
                            continue

                        # 請求書を検索
                        invoice = Invoice.objects.filter(
                            tenant_id=request.user.tenant_id,
                            invoice_no=invoice_no,
                            guardian=guardian
                        ).first()

                        # 結果ステータスを判定
                        if result_code == '0':
                            result_status = DirectDebitResult.ResultStatus.SUCCESS
                            failure_reason = ''
                        elif result_code == '1':
                            result_status = DirectDebitResult.ResultStatus.FAILED
                            failure_reason = DirectDebitResult.FailureReason.INSUFFICIENT_FUNDS
                        else:
                            result_status = DirectDebitResult.ResultStatus.FAILED
                            failure_reason = DirectDebitResult.FailureReason.OTHER

                        # 引落結果を記録
                        debit_result = DirectDebitResult.objects.create(
                            tenant_id=request.user.tenant_id,
                            guardian=guardian,
                            invoice=invoice,
                            debit_date=timezone.now().date(),
                            amount=Decimal(amount) if amount else 0,
                            result_status=result_status,
                            failure_reason=failure_reason,
                        )

                        # 成功時は入金処理
                        if result_status == DirectDebitResult.ResultStatus.SUCCESS and invoice:
                            payment = Payment.objects.create(
                                tenant_id=request.user.tenant_id,
                                payment_no=Payment.generate_payment_no(request.user.tenant_id),
                                guardian=guardian,
                                invoice=invoice,
                                payment_date=timezone.now().date(),
                                amount=Decimal(amount) if amount else 0,
                                method=Payment.Method.DIRECT_DEBIT,
                                status=Payment.Status.SUCCESS,
                                notes=f"引落結果取込: {debit_result.id}",
                                registered_by=request.user,
                            )
                            payment.apply_to_invoice()

                        imported += 1

                    except Exception as e:
                        errors.append(f"行{row_num}: {str(e)}")

            return Response({
                'success': len(errors) == 0,
                'imported': imported,
                'errors': errors
            })

        except Exception as e:
            return Response(
                {'success': False, 'imported': 0, 'errors': [str(e)]},
                status=status.HTTP_400_BAD_REQUEST
            )


# =============================================================================
# Payment ViewSet
# =============================================================================
@extend_schema_view(
    list=extend_schema(summary='入金一覧'),
    retrieve=extend_schema(summary='入金詳細'),
)
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

        # 結果コードによってステータスを更新
        if result_code == '0':  # 成功
            payment.status = Payment.Status.SUCCESS
            payment.apply_to_invoice()
        else:
            payment.status = Payment.Status.FAILED

        payment.save()
        return Response(PaymentSerializer(payment).data)


# =============================================================================
# GuardianBalance ViewSet
# =============================================================================
@extend_schema_view(
    list=extend_schema(summary='預り金残高一覧'),
    retrieve=extend_schema(summary='預り金残高詳細'),
)
class GuardianBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """預り金残高管理API"""
    serializer_class = GuardianBalanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GuardianBalance.objects.filter(
            tenant_id=self.request.user.tenant_id
        ).select_related('guardian')

    @extend_schema(summary='預り金入金', request=BalanceDepositSerializer)
    @action(detail=False, methods=['post'])
    def deposit(self, request):
        """預り金に入金"""
        serializer = BalanceDepositSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        balance, created = GuardianBalance.objects.get_or_create(
            tenant_id=request.user.tenant_id,
            guardian_id=data['guardian_id'],
            defaults={'balance': Decimal('0')}
        )

        balance.add_balance(data['amount'], data.get('reason', ''))
        return Response(GuardianBalanceSerializer(balance).data)

    @extend_schema(summary='預り金相殺', request=BalanceOffsetSerializer)
    @action(detail=False, methods=['post'])
    def offset(self, request):
        """預り金を請求書に相殺"""
        serializer = BalanceOffsetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        balance = get_object_or_404(
            GuardianBalance,
            guardian_id=data['guardian_id'],
            tenant_id=request.user.tenant_id
        )
        invoice = get_object_or_404(
            Invoice,
            id=data['invoice_id'],
            tenant_id=request.user.tenant_id
        )

        try:
            with transaction.atomic():
                balance.use_balance(
                    data['amount'],
                    invoice=invoice,
                    reason=f'請求書 {invoice.invoice_no} への相殺'
                )

                # 相殺入金を作成
                Payment.objects.create(
                    tenant_id=request.user.tenant_id,
                    payment_no=Payment.generate_payment_no(request.user.tenant_id),
                    guardian=invoice.guardian,
                    invoice=invoice,
                    payment_date=timezone.now().date(),
                    amount=data['amount'],
                    method=Payment.Method.OFFSET,
                    status=Payment.Status.SUCCESS,
                    notes='預り金からの相殺',
                    registered_by=request.user,
                )

                # 請求書の入金額を更新
                invoice.paid_amount += data['amount']
                invoice.balance_due = invoice.total_amount - invoice.paid_amount
                if invoice.balance_due <= 0:
                    invoice.status = Invoice.Status.PAID
                elif invoice.paid_amount > 0:
                    invoice.status = Invoice.Status.PARTIAL
                invoice.save()

        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(GuardianBalanceSerializer(balance).data)


# =============================================================================
# OffsetLog ViewSet
# =============================================================================
@extend_schema_view(
    list=extend_schema(summary='相殺ログ一覧'),
    retrieve=extend_schema(summary='相殺ログ詳細'),
)
class OffsetLogViewSet(viewsets.ReadOnlyModelViewSet):
    """相殺ログAPI（読み取り専用）"""
    serializer_class = OffsetLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OffsetLog.objects.filter(
            tenant_id=self.request.user.tenant_id
        ).select_related('guardian', 'invoice', 'payment')

    @extend_schema(summary='保護者の相殺履歴')
    @action(detail=False, methods=['get'], url_path='by-guardian/(?P<guardian_id>[^/.]+)')
    def by_guardian(self, request, guardian_id=None):
        """保護者IDで相殺ログを取得"""
        logs = self.get_queryset().filter(guardian_id=guardian_id)
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)


# =============================================================================
# RefundRequest ViewSet
# =============================================================================
@extend_schema_view(
    list=extend_schema(summary='返金申請一覧'),
    retrieve=extend_schema(summary='返金申請詳細'),
)
class RefundRequestViewSet(viewsets.ModelViewSet):
    """返金申請管理API"""
    serializer_class = RefundRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RefundRequest.objects.filter(
            tenant_id=self.request.user.tenant_id
        ).select_related('guardian', 'invoice', 'requested_by', 'approved_by')

    @extend_schema(summary='返金申請作成', request=RefundRequestCreateSerializer)
    @action(detail=False, methods=['post'])
    def create_request(self, request):
        """返金申請を作成"""
        serializer = RefundRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 申請番号生成
        today = timezone.now()
        prefix = f"REF-{today.strftime('%Y%m%d')}-"
        last = RefundRequest.objects.filter(
            tenant_id=request.user.tenant_id,
            request_no__startswith=prefix
        ).order_by('-request_no').first()
        if last:
            new_num = int(last.request_no.split('-')[-1]) + 1
        else:
            new_num = 1
        request_no = f"{prefix}{new_num:04d}"

        refund_request = RefundRequest.objects.create(
            tenant_id=request.user.tenant_id,
            request_no=request_no,
            guardian_id=data['guardian_id'],
            invoice_id=data.get('invoice_id'),
            refund_amount=data['refund_amount'],
            refund_method=data['refund_method'],
            reason=data['reason'],
            requested_by=request.user,
        )

        return Response(
            RefundRequestSerializer(refund_request).data,
            status=status.HTTP_201_CREATED
        )

    @extend_schema(summary='返金申請承認/却下', request=RefundApproveSerializer)
    @action(detail=False, methods=['post'])
    def approve(self, request):
        """返金申請を承認または却下"""
        serializer = RefundApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        refund_request = get_object_or_404(
            RefundRequest,
            id=data['request_id'],
            tenant_id=request.user.tenant_id
        )

        if refund_request.status != RefundRequest.Status.PENDING:
            return Response(
                {'error': 'この申請は既に処理されています'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if data['approve']:
            refund_request.approve(request.user)
        else:
            refund_request.status = RefundRequest.Status.REJECTED
            refund_request.approved_by = request.user
            refund_request.approved_at = timezone.now()
            refund_request.process_notes = data.get('reject_reason', '')
            refund_request.save()

        return Response(RefundRequestSerializer(refund_request).data)


# =============================================================================
# MileTransaction ViewSet
# =============================================================================
@extend_schema_view(
    list=extend_schema(summary='マイル取引一覧'),
    retrieve=extend_schema(summary='マイル取引詳細'),
)
class MileTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """マイル取引API（読み取り専用）"""
    serializer_class = MileTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MileTransaction.objects.filter(
            tenant_id=self.request.user.tenant_id
        ).select_related('guardian', 'invoice')

    @extend_schema(summary='マイル残高取得')
    @action(detail=False, methods=['get'], url_path='balance/(?P<guardian_id>[^/.]+)')
    def balance(self, request, guardian_id=None):
        """保護者のマイル残高を取得"""
        from apps.students.models import Guardian
        guardian = get_object_or_404(Guardian, id=guardian_id)

        balance = MileTransaction.get_balance(guardian)
        can_use = MileTransaction.can_use_miles(guardian)

        return Response({
            'guardian_id': str(guardian_id),
            'balance': balance,
            'can_use': can_use,
            'min_use': 4,
        })

    @extend_schema(summary='マイル割引計算', request=MileCalculateSerializer)
    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """使用マイル数から割引額を計算"""
        serializer = MileCalculateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        miles = serializer.validated_data['miles_to_use']
        discount = MileTransaction.calculate_discount(miles)

        return Response({
            'miles_to_use': miles,
            'discount_amount': discount,
        })

    @extend_schema(summary='マイル使用', request=MileUseSerializer)
    @action(detail=False, methods=['post'])
    def use(self, request):
        """マイルを使用して割引適用"""
        serializer = MileUseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.students.models import Guardian
        guardian = get_object_or_404(Guardian, id=data['guardian_id'])
        invoice = get_object_or_404(
            Invoice,
            id=data['invoice_id'],
            tenant_id=request.user.tenant_id
        )

        # マイル使用可能チェック
        if not MileTransaction.can_use_miles(guardian):
            return Response(
                {'error': 'マイルを使用するには2つ以上のコース契約が必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 残高チェック
        current_balance = MileTransaction.get_balance(guardian)
        miles_to_use = data['miles_to_use']
        if miles_to_use > current_balance:
            return Response(
                {'error': f'マイル残高が不足しています（残高: {current_balance}pt）'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 割引額計算
        discount_amount = MileTransaction.calculate_discount(miles_to_use)

        with transaction.atomic():
            # マイル取引を記録
            new_balance = current_balance - miles_to_use
            mile_tx = MileTransaction.objects.create(
                tenant_id=request.user.tenant_id,
                guardian=guardian,
                invoice=invoice,
                transaction_type=MileTransaction.TransactionType.USE,
                miles=-miles_to_use,
                balance_after=new_balance,
                discount_amount=discount_amount,
                notes=f'請求書 {invoice.invoice_no} でのマイル使用',
            )

            # 請求書にマイル割引を適用
            invoice.miles_used = miles_to_use
            invoice.miles_discount = discount_amount
            invoice.calculate_totals()
            invoice.save()

        return Response({
            'miles_used': miles_to_use,
            'discount_amount': discount_amount,
            'new_balance': new_balance,
            'invoice': InvoiceSerializer(invoice).data,
        })

    @extend_schema(summary='保護者のマイル履歴')
    @action(detail=False, methods=['get'], url_path='by-guardian/(?P<guardian_id>[^/.]+)')
    def by_guardian(self, request, guardian_id=None):
        """保護者IDでマイル取引を取得"""
        transactions = self.get_queryset().filter(guardian_id=guardian_id)
        serializer = self.get_serializer(transactions, many=True)
        return Response(serializer.data)
