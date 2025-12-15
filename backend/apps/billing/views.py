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
    OffsetLog, RefundRequest, MileTransaction,
    BillingPeriod, PaymentProvider
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
        """引落データをCSV形式でエクスポート（JACCS/UFJファクター/中京ファイナンス向け）

        日付範囲で指定可能。エクスポート後、該当請求書と以前の請求書は編集ロックされる。
        """
        import csv
        from datetime import datetime
        from django.http import HttpResponse
        from apps.students.models import Guardian

        # 日付範囲パラメータ（新形式）
        start_date = request.query_params.get('start_date')  # YYYY-MM-DD
        end_date = request.query_params.get('end_date')      # YYYY-MM-DD
        provider = request.query_params.get('provider', 'jaccs')

        # 旧形式（year/month）との互換性
        billing_year = request.query_params.get('billing_year')
        billing_month = request.query_params.get('billing_month')

        if not start_date or not end_date:
            if billing_year and billing_month:
                # 旧形式の場合は月初〜月末に変換
                from calendar import monthrange
                year = int(billing_year)
                month = int(billing_month)
                last_day = monthrange(year, month)[1]
                start_date = f"{year}-{month:02d}-01"
                end_date = f"{year}-{month:02d}-{last_day:02d}"
            else:
                return Response(
                    {'error': '期間を指定してください（start_date, end_date または billing_year, billing_month）'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': '日付形式が不正です（YYYY-MM-DD）'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # バッチ番号を生成
        batch_no = f"EXP-{timezone.now().strftime('%Y%m%d%H%M%S')}-{provider.upper()}"

        # 対象請求書を取得（口座引落、発行済または一部入金、期間内）
        invoices = Invoice.objects.filter(
            tenant_id=request.user.tenant_id,
            issue_date__gte=start_dt,
            issue_date__lte=end_dt,
            payment_method=Invoice.PaymentMethod.DIRECT_DEBIT,
            status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL],
        ).select_related('guardian')

        # CSVレスポンス作成
        response = HttpResponse(content_type='text/csv; charset=shift_jis')
        filename = f"debit_export_{start_date}_{end_date}_{provider}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)

        # ヘッダー行（全銀形式ベース）
        writer.writerow([
            '顧客番号', '氏名カナ', '銀行コード', '支店コード',
            '口座種別', '口座番号', '引落金額', '備考'
        ])

        exported_invoice_ids = []

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
            exported_invoice_ids.append(inv.id)

        # エクスポートした請求書と、それ以前の請求書をロック
        now = timezone.now()
        Invoice.objects.filter(
            tenant_id=request.user.tenant_id,
            issue_date__lte=end_dt,
            is_locked=False,
        ).update(
            is_locked=True,
            locked_at=now,
            locked_by=request.user,
            export_batch_no=batch_no,
        )

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


# =============================================================================
# PaymentProvider ViewSet - 決済代行会社（締日設定）
# =============================================================================
class PaymentProviderViewSet(viewsets.ModelViewSet):
    """決済代行会社管理API（締日・引落日設定含む）"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        return PaymentProvider.objects.filter(
            tenant_id=tenant_id
        ).order_by('name')

    def get_serializer_class(self):
        from rest_framework import serializers

        class PaymentProviderSerializer(serializers.ModelSerializer):
            class Meta:
                model = PaymentProvider
                fields = [
                    'id', 'code', 'name', 'consignor_code',
                    'closing_day', 'debit_day',
                    'is_active', 'default_bank_code', 'file_encoding',
                ]

        return PaymentProviderSerializer

    @extend_schema(summary='現在の締日情報を取得')
    @action(detail=False, methods=['get'])
    def current_deadlines(self, request):
        """現在月の締日情報を取得"""
        from datetime import date

        today = date.today()
        # tenant_idフィルタを外して全プロバイダーを取得
        providers = PaymentProvider.objects.filter(is_active=True)

        deadlines = []
        for provider in providers:
            # 締日を計算
            closing_day = provider.closing_day or 25
            try:
                closing_date = date(today.year, today.month, closing_day)
            except ValueError:
                # 月末日を超える場合は月末日
                import calendar
                last_day = calendar.monthrange(today.year, today.month)[1]
                closing_date = date(today.year, today.month, last_day)

            # 引落日を計算
            debit_day = provider.debit_day or 27
            debit_month = today.month + 1 if today.month < 12 else 1
            debit_year = today.year if today.month < 12 else today.year + 1
            try:
                debit_date = date(debit_year, debit_month, debit_day)
            except ValueError:
                import calendar
                last_day = calendar.monthrange(debit_year, debit_month)[1]
                debit_date = date(debit_year, debit_month, last_day)

            # この期間が締め済みかどうか確認
            billing_period = BillingPeriod.objects.filter(
                provider=provider,
                year=today.year,
                month=today.month
            ).first()

            deadlines.append({
                'providerId': str(provider.id),
                'providerName': provider.name,
                'providerCode': provider.code,
                'closingDay': closing_day,
                'closingDate': closing_date.isoformat(),
                'closingDateDisplay': f"{today.month}月{closing_day}日",
                'debitDay': debit_day,
                'debitDate': debit_date.isoformat(),
                'debitDateDisplay': f"{debit_month}月{debit_day}日",
                'isClosed': billing_period.is_closed if billing_period else False,
                'closedAt': billing_period.closed_at.isoformat() if billing_period and billing_period.closed_at else None,
                'daysUntilClosing': (closing_date - today).days,
                'canEdit': not (billing_period and billing_period.is_closed) and closing_date >= today,
            })

        return Response({
            'today': today.isoformat(),
            'currentYear': today.year,
            'currentMonth': today.month,
            'deadlines': deadlines,
        })

    @extend_schema(summary='締日設定を更新')
    @action(detail=True, methods=['patch'])
    def update_deadline(self, request, pk=None):
        """締日・引落日の設定を更新"""
        provider = self.get_object()

        closing_day = request.data.get('closing_day')
        debit_day = request.data.get('debit_day')

        if closing_day is not None:
            if not (1 <= closing_day <= 31):
                return Response({'error': '締日は1〜31の間で設定してください'}, status=400)
            provider.closing_day = closing_day

        if debit_day is not None:
            if not (1 <= debit_day <= 31):
                return Response({'error': '引落日は1〜31の間で設定してください'}, status=400)
            provider.debit_day = debit_day

        provider.save()

        return Response({
            'success': True,
            'closing_day': provider.closing_day,
            'debit_day': provider.debit_day,
        })


# =============================================================================
# BillingPeriod ViewSet - 請求期間管理
# =============================================================================
class BillingPeriodViewSet(viewsets.ModelViewSet):
    """請求期間管理API"""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        return BillingPeriod.objects.filter(
            tenant_id=tenant_id
        ).select_related('provider', 'closed_by').order_by('-year', '-month')

    def get_serializer_class(self):
        from rest_framework import serializers

        class BillingPeriodSerializer(serializers.ModelSerializer):
            provider_name = serializers.CharField(source='provider.name', read_only=True)
            closed_by_name = serializers.SerializerMethodField()

            class Meta:
                model = BillingPeriod
                fields = [
                    'id', 'provider', 'provider_name', 'year', 'month',
                    'closing_date', 'is_closed', 'closed_at', 'closed_by', 'closed_by_name',
                    'notes',
                ]

            def get_closed_by_name(self, obj):
                if obj.closed_by:
                    return f"{obj.closed_by.last_name}{obj.closed_by.first_name}"
                return None

        return BillingPeriodSerializer

    @extend_schema(summary='締め処理実行')
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """指定期間の締め処理を実行"""
        period = self.get_object()

        if period.is_closed:
            return Response({'error': 'この期間は既に締め処理済みです'}, status=400)

        period.is_closed = True
        period.closed_at = timezone.now()
        period.closed_by = request.user
        period.save()

        return Response({
            'success': True,
            'message': f'{period.year}年{period.month}月の締め処理が完了しました',
            'closed_at': period.closed_at.isoformat(),
        })

    @extend_schema(summary='締め解除')
    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        """締め処理を解除（管理者のみ）"""
        from apps.core.permissions import is_admin_user

        if not is_admin_user(request.user):
            return Response({'error': '管理者権限が必要です'}, status=403)

        period = self.get_object()

        if not period.is_closed:
            return Response({'error': 'この期間は締め処理されていません'}, status=400)

        period.is_closed = False
        period.closed_at = None
        period.closed_by = None
        period.notes = f"{period.notes}\n{timezone.now().strftime('%Y-%m-%d %H:%M')} 締め解除: {request.user.last_name}{request.user.first_name}"
        period.save()

        return Response({
            'success': True,
            'message': f'{period.year}年{period.month}月の締め処理を解除しました',
        })
