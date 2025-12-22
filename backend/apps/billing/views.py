"""
Billing Views - 請求・入金・預り金・マイル管理API
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from djangorestframework_camel_case.parser import CamelCaseMultiPartParser

logger = logging.getLogger(__name__)
from django.shortcuts import get_object_or_404
from django.db import models, transaction
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import (
    Invoice, InvoiceLine, Payment, GuardianBalance,
    OffsetLog, RefundRequest, MileTransaction,
    BillingPeriod, PaymentProvider, MonthlyBillingDeadline,
    BankTransfer, BankTransferImport, ConfirmedBilling
)
from .serializers import (
    InvoiceSerializer, InvoiceLineSerializer,
    InvoicePreviewSerializer, InvoiceConfirmSerializer,
    PaymentSerializer, PaymentCreateSerializer, DirectDebitResultSerializer,
    GuardianBalanceSerializer, BalanceDepositSerializer, BalanceOffsetSerializer,
    OffsetLogSerializer,
    RefundRequestSerializer, RefundRequestCreateSerializer, RefundApproveSerializer,
    MileTransactionSerializer, MileBalanceSerializer, MileCalculateSerializer, MileUseSerializer,
    BankTransferSerializer, BankTransferMatchSerializer, BankTransferBulkMatchSerializer,
    BankTransferImportSerializer, BankTransferImportUploadSerializer,
    ConfirmedBillingSerializer, ConfirmedBillingListSerializer,
    ConfirmedBillingCreateSerializer, BillingConfirmBatchSerializer,
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

    def check_deadline_editable(self, invoice):
        """請求書の請求月が編集可能かチェック"""
        tenant_id = getattr(self.request, 'tenant_id', None) or getattr(self.request.user, 'tenant_id', None)
        if not MonthlyBillingDeadline.is_month_editable(tenant_id, invoice.billing_year, invoice.billing_month):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                f'{invoice.billing_year}年{invoice.billing_month}月分は締め済みのため編集できません'
            )

    def update(self, request, *args, **kwargs):
        """請求書更新時に締め状態をチェック"""
        instance = self.get_object()
        self.check_deadline_editable(instance)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """請求書部分更新時に締め状態をチェック"""
        instance = self.get_object()
        self.check_deadline_editable(instance)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """請求書削除時に締め状態をチェック"""
        instance = self.get_object()
        self.check_deadline_editable(instance)
        return super().destroy(request, *args, **kwargs)

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
                        if result_status == DirectDebitResult.ResultStatus.SUCCESS:
                            payment_amount = Decimal(amount) if amount else Decimal('0')
                            payment = Payment.objects.create(
                                tenant_id=request.user.tenant_id,
                                payment_no=Payment.generate_payment_no(request.user.tenant_id),
                                guardian=guardian,
                                invoice=invoice,
                                payment_date=timezone.now().date(),
                                amount=payment_amount,
                                method=Payment.Method.DIRECT_DEBIT,
                                status=Payment.Status.SUCCESS,
                                notes=f"引落結果取込: {debit_result.id}",
                                registered_by=request.user,
                            )
                            if invoice:
                                payment.apply_to_invoice()

                            # ConfirmedBillingも更新
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
                                reason=f'口座振替による入金',
                                payment=payment,
                            )

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

    @extend_schema(summary='請求データCSVエクスポート（締日期間）')
    @action(detail=False, methods=['get'], url_path='export_csv')
    def export_csv(self, request):
        """請求データをCSV形式でエクスポート（締日期間指定）

        start_date, end_date で期間を指定
        billing_year, billing_month で請求月を指定
        close_period=true で締め確定も同時に実行
        """
        import csv
        from datetime import datetime
        from django.http import HttpResponse

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        billing_year = request.query_params.get('billing_year')
        billing_month = request.query_params.get('billing_month')
        close_period = request.query_params.get('close_period', 'false').lower() == 'true'

        if not start_date or not end_date:
            return Response(
                {'error': '期間を指定してください（start_date, end_date）'},
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

        tenant_id = request.user.tenant_id

        # 対象請求書を取得
        invoices = Invoice.objects.filter(
            tenant_id=tenant_id,
        ).select_related('guardian').prefetch_related('lines')

        # billing_year, billing_month が指定されている場合はそれでフィルタ
        if billing_year and billing_month:
            invoices = invoices.filter(
                billing_year=int(billing_year),
                billing_month=int(billing_month)
            )
        else:
            # 期間ベースでフィルタ
            from django.db.models import Q
            start_year, start_month = start_dt.year, start_dt.month
            end_year, end_month = end_dt.year, end_dt.month

            year_month_conditions = Q()
            current_year, current_month = start_year, start_month
            while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
                year_month_conditions |= Q(billing_year=current_year, billing_month=current_month)
                if current_month == 12:
                    current_year += 1
                    current_month = 1
                else:
                    current_month += 1

            invoices = invoices.filter(year_month_conditions)

        invoices = invoices.order_by('billing_year', 'billing_month', 'invoice_no')

        # CSVレスポンス作成
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        filename = f"請求データ_{start_date}_{end_date}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)

        # ヘッダー行
        writer.writerow([
            '請求番号', '請求年', '請求月', '保護者番号', '保護者名', '保護者名カナ',
            'ステータス', '支払方法', '発行日', '請求額', '入金額', '未払額',
            '生徒名', '商品名', '商品タイプ', '数量', '単価', '税込金額', '税率'
        ])

        # データ行（請求明細ごとに1行）
        for inv in invoices:
            guardian = inv.guardian
            guardian_no = guardian.guardian_no if guardian else ''
            guardian_name = guardian.full_name if guardian else ''
            guardian_name_kana = guardian.full_name_kana if guardian else ''

            status_display = dict(Invoice.Status.choices).get(inv.status, inv.status)
            method_display = dict(Invoice.PaymentMethod.choices).get(inv.payment_method, inv.payment_method)

            lines = inv.lines.all()
            if lines:
                for line in lines:
                    writer.writerow([
                        inv.invoice_no or '',
                        inv.billing_year,
                        inv.billing_month,
                        guardian_no,
                        guardian_name,
                        guardian_name_kana,
                        status_display,
                        method_display,
                        inv.issue_date.strftime('%Y-%m-%d') if inv.issue_date else '',
                        int(inv.total_amount or 0),
                        int(inv.paid_amount or 0),
                        int(inv.balance_due or 0),
                        line.student.full_name if line.student else '',
                        line.product_name or '',
                        line.product_type or '',
                        line.quantity or 1,
                        int(line.unit_price or 0),
                        int(line.price_with_tax or 0),
                        f"{int((line.tax_rate or 0) * 100)}%",
                    ])
            else:
                # 明細がない場合は請求書のみ出力
                writer.writerow([
                    inv.invoice_no or '',
                    inv.billing_year,
                    inv.billing_month,
                    guardian_no,
                    guardian_name,
                    guardian_name_kana,
                    status_display,
                    method_display,
                    inv.issue_date.strftime('%Y-%m-%d') if inv.issue_date else '',
                    int(inv.total_amount or 0),
                    int(inv.paid_amount or 0),
                    int(inv.balance_due or 0),
                    '', '', '', '', '', '', ''
                ])

        # 締め確定処理
        if close_period and billing_year and billing_month:
            try:
                # MonthlyBillingDeadlineを締め状態に更新
                deadline, created = MonthlyBillingDeadline.objects.get_or_create(
                    tenant_id=tenant_id,
                    year=int(billing_year),
                    month=int(billing_month),
                    defaults={
                        'closing_day': PaymentProvider.objects.filter(
                            tenant_id=tenant_id, is_active=True
                        ).first().closing_day if PaymentProvider.objects.filter(
                            tenant_id=tenant_id, is_active=True
                        ).exists() else 25
                    }
                )
                if not deadline.is_closed:
                    deadline.is_closed = True
                    deadline.is_manually_closed = True
                    deadline.closed_at = timezone.now()
                    deadline.closed_by = request.user
                    deadline.notes = f'CSVエクスポート時に自動締め（{start_date}〜{end_date}）'
                    deadline.save()

                # 対象請求書をロック
                Invoice.objects.filter(
                    tenant_id=tenant_id,
                    billing_year=int(billing_year),
                    billing_month=int(billing_month),
                    is_locked=False,
                ).update(
                    is_locked=True,
                    locked_at=timezone.now(),
                    locked_by=request.user,
                )
            except Exception as e:
                # 締め処理に失敗してもCSVは返す（ログのみ）
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Failed to close period: {e}')

        return response

    @extend_schema(summary='締日期間確定')
    @action(detail=False, methods=['post'], url_path='close_period')
    def close_period(self, request):
        """締日期間を確定（請求データをロック）

        確定ボタンを押したタイミングで、前回確定から現在までのデータを確定する。
        締め日は10日固定。
        """
        from datetime import datetime, date
        from dateutil.relativedelta import relativedelta

        tenant_id = request.user.tenant_id
        today = date.today()
        closing_day = 10  # 締め日は10日固定

        try:
            # 前回の確定日を取得（ConfirmedBillingの最新confirmed_at）
            last_confirmed = ConfirmedBilling.objects.filter(
                tenant_id=tenant_id
            ).order_by('-confirmed_at').first()

            if last_confirmed:
                # 前回確定日の翌日から
                start_date = last_confirmed.confirmed_at.date() + relativedelta(days=1)
            else:
                # 初回の場合は最初の請求データから
                first_invoice = Invoice.objects.filter(
                    tenant_id=tenant_id
                ).order_by('created_at').first()
                if first_invoice:
                    start_date = first_invoice.created_at.date()
                else:
                    start_date = today - relativedelta(months=1)

            end_date = today

            # 締め日（10日）を基準に請求月を計算
            # 例: 11/11〜12/10 は12月請求分、12/11〜1/10 は1月請求分
            if today.day <= closing_day:
                # 今月分
                billing_year = today.year
                billing_month = today.month
            else:
                # 翌月分
                next_month = today + relativedelta(months=1)
                billing_year = next_month.year
                billing_month = next_month.month

            # 未確定の請求書からConfirmedBillingを作成
            from apps.students.models import Student
            from apps.pricing.models import StudentItem

            students = Student.objects.filter(
                tenant_id=tenant_id,
                status='active'
            ).select_related('guardian')

            confirmed_count = 0
            for student in students:
                # 既にこの月の確定データがあればスキップ
                existing = ConfirmedBilling.objects.filter(
                    tenant_id=tenant_id,
                    student=student,
                    year=billing_year,
                    month=billing_month
                ).first()
                if existing:
                    continue

                # 生徒の請求項目を取得
                student_items = StudentItem.objects.filter(
                    student=student,
                    is_active=True
                ).select_related('product')

                if not student_items.exists():
                    continue

                # 請求金額を計算
                subtotal = sum(item.unit_price * item.quantity for item in student_items)
                discount_total = 0  # 割引計算は必要に応じて追加
                tax_amount = 0  # 税額計算は必要に応じて追加
                total_amount = subtotal - discount_total + tax_amount

                # スナップショット作成
                items_snapshot = [
                    {
                        'product_id': str(item.product.id),
                        'product_name': item.product.name,
                        'category': item.product.get_item_type_display(),
                        'unit_price': int(item.unit_price),
                        'quantity': item.quantity,
                        'amount': int(item.unit_price * item.quantity),
                    }
                    for item in student_items
                ]

                # ConfirmedBilling作成
                ConfirmedBilling.objects.create(
                    tenant_id=tenant_id,
                    student=student,
                    guardian=student.guardian,
                    year=billing_year,
                    month=billing_month,
                    subtotal=subtotal,
                    discount_total=discount_total,
                    tax_amount=tax_amount,
                    total_amount=total_amount,
                    items_snapshot=items_snapshot,
                    discounts_snapshot=[],
                    status=ConfirmedBilling.Status.CONFIRMED,
                    payment_method=ConfirmedBilling.PaymentMethod.DIRECT_DEBIT,
                    confirmed_at=timezone.now(),
                    confirmed_by=request.user,
                )
                confirmed_count += 1

            # 対象請求書をロック
            locked_count = Invoice.objects.filter(
                tenant_id=tenant_id,
                billing_year=billing_year,
                billing_month=billing_month,
                is_locked=False,
            ).update(
                is_locked=True,
                locked_at=timezone.now(),
                locked_by=request.user,
            )

            return Response({
                'success': True,
                'message': f'{billing_year}年{billing_month}月分の締め確定が完了しました',
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                },
                'billing_year': billing_year,
                'billing_month': billing_month,
                'confirmed_billings': confirmed_count,
                'locked_invoices': locked_count,
            })

        except Exception as e:
            logger.error(f'Failed to close period: {e}')
            return Response(
                {'error': f'締め確定に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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

    @extend_schema(summary='保護者の預り金残高')
    @action(detail=False, methods=['get'], url_path='by-guardian/(?P<guardian_id>[^/.]+)')
    def by_guardian(self, request, guardian_id=None):
        """保護者IDで預り金残高を取得"""
        balance = self.get_queryset().filter(guardian_id=guardian_id).first()
        if balance:
            return Response({
                'guardian_id': str(guardian_id),
                'balance': int(balance.balance),
                'last_updated': balance.last_updated.isoformat() if balance.last_updated else None,
            })
        else:
            return Response({
                'guardian_id': str(guardian_id),
                'balance': 0,
                'last_updated': None,
            })


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

    @extend_schema(summary='自分の通帳（入出金履歴）')
    @action(detail=False, methods=['get'], url_path='my-passbook')
    def my_passbook(self, request):
        """ログイン中の保護者の通帳（入出金履歴）を取得"""
        from apps.students.models import Guardian

        # ログインユーザーに紐づく保護者を取得
        guardian = Guardian.objects.filter(user=request.user).first()
        if not guardian:
            return Response({'detail': '保護者情報が見つかりません'}, status=404)

        # 相殺ログを取得（新しい順）
        logs = self.get_queryset().filter(guardian=guardian).order_by('-created_at')

        # 現在の残高も返す
        from apps.billing.models import GuardianBalance
        balance_obj = GuardianBalance.objects.filter(guardian=guardian).first()
        current_balance = int(balance_obj.balance) if balance_obj else 0

        serializer = self.get_serializer(logs, many=True)
        return Response({
            'guardian_id': str(guardian.id),
            'guardian_name': guardian.full_name,
            'current_balance': current_balance,
            'transactions': serializer.data
        })


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

    @extend_schema(summary='締日設定を新規作成')
    @action(detail=False, methods=['post'])
    def create_deadline(self, request):
        """締日・引落日の設定を新規作成（デフォルトプロバイダー）"""
        tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)

        closing_day = request.data.get('closing_day', 25)
        debit_day = request.data.get('debit_day', 27)

        if not (1 <= closing_day <= 31):
            return Response({'error': '締日は1〜31の間で設定してください'}, status=400)
        if not (1 <= debit_day <= 31):
            return Response({'error': '引落日は1〜31の間で設定してください'}, status=400)

        # デフォルトプロバイダーを作成または取得
        provider, created = PaymentProvider.objects.get_or_create(
            tenant_id=tenant_id,
            code='DEFAULT',
            defaults={
                'name': 'デフォルト',
                'closing_day': closing_day,
                'debit_day': debit_day,
                'is_active': True,
            }
        )

        if not created:
            # 既存のプロバイダーの場合は更新
            provider.closing_day = closing_day
            provider.debit_day = debit_day
            provider.save()

        return Response({
            'success': True,
            'provider_id': str(provider.id),
            'closing_day': provider.closing_day,
            'debit_day': provider.debit_day,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


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

    @extend_schema(summary='新規入会時の請求情報を取得')
    @action(detail=False, methods=['get'])
    def enrollment_billing_info(self, request):
        """新規入会時の請求月情報を取得

        締日を考慮して、どの月から請求できるかを返す。
        """
        from datetime import datetime
        from apps.billing.services.period_service import BillingPeriodService

        # 入会日（指定がなければ今日）
        enrollment_date_str = request.query_params.get('enrollment_date')
        if enrollment_date_str:
            try:
                enrollment_date = datetime.strptime(enrollment_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': '日付形式が不正です（YYYY-MM-DD）'}, status=400)
        else:
            enrollment_date = timezone.now().date()

        tenant_id = getattr(request, 'tenant_id', None)
        service = BillingPeriodService(tenant_id)

        # プロバイダー指定（指定がなければアクティブな最初のプロバイダー）
        provider_id = request.query_params.get('provider_id')
        if provider_id:
            provider = PaymentProvider.objects.filter(id=provider_id).first()
        else:
            provider = PaymentProvider.objects.filter(
                tenant_id=tenant_id,
                is_active=True
            ).first()

        billing_info = service.get_billing_info_for_new_enrollment(
            enrollment_date=enrollment_date,
            provider=provider
        )

        return Response(billing_info)

    @extend_schema(summary='チケット購入時の請求月を取得')
    @action(detail=False, methods=['get'])
    def ticket_billing_info(self, request):
        """チケット購入時の請求月を判定

        締日を考慮して、どの月の請求になるかを返す。
        """
        from datetime import datetime
        from apps.billing.services.period_service import BillingPeriodService

        # 購入日（指定がなければ今日）
        purchase_date_str = request.query_params.get('purchase_date')
        if purchase_date_str:
            try:
                purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': '日付形式が不正です（YYYY-MM-DD）'}, status=400)
        else:
            purchase_date = timezone.now().date()

        tenant_id = getattr(request, 'tenant_id', None)
        service = BillingPeriodService(tenant_id)

        # プロバイダー指定
        provider_id = request.query_params.get('provider_id')
        if provider_id:
            provider = PaymentProvider.objects.filter(id=provider_id).first()
        else:
            provider = PaymentProvider.objects.filter(
                tenant_id=tenant_id,
                is_active=True
            ).first()

        ticket_info = service.get_ticket_billing_month(
            purchase_date=purchase_date,
            provider=provider
        )

        return Response(ticket_info)


# =============================================================================
# MonthlyBillingDeadline ViewSet - 月次請求締切管理
# =============================================================================
class MonthlyBillingDeadlineViewSet(viewsets.ModelViewSet):
    """月次請求締切管理API

    内部的な締日管理。締日を過ぎると、その月の請求データは編集不可になる。
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if not tenant_id and hasattr(self.request, 'user') and hasattr(self.request.user, 'tenant_id'):
            tenant_id = self.request.user.tenant_id
        # テナントIDが取得できない場合はデフォルトテナントを使用
        if not tenant_id:
            from apps.tenants.models import Tenant
            default_tenant = Tenant.objects.first()
            if default_tenant:
                tenant_id = default_tenant.id
        if not tenant_id:
            return MonthlyBillingDeadline.objects.none()
        return MonthlyBillingDeadline.objects.filter(
            tenant_id=tenant_id
        ).order_by('-year', '-month')

    def get_serializer_class(self):
        from rest_framework import serializers

        class MonthlyBillingDeadlineSerializer(serializers.ModelSerializer):
            is_closed = serializers.SerializerMethodField()
            status = serializers.SerializerMethodField()
            status_display = serializers.SerializerMethodField()
            closing_date_display = serializers.SerializerMethodField()
            can_edit = serializers.SerializerMethodField()
            manually_closed_by_name = serializers.SerializerMethodField()
            reopened_by_name = serializers.SerializerMethodField()
            under_review_by_name = serializers.SerializerMethodField()

            class Meta:
                model = MonthlyBillingDeadline
                fields = [
                    'id', 'year', 'month', 'closing_day',
                    'auto_close', 'is_manually_closed', 'manually_closed_at',
                    'manually_closed_by', 'manually_closed_by_name',
                    'is_reopened', 'reopened_at', 'reopened_by', 'reopened_by_name',
                    'reopen_reason',
                    'is_under_review', 'under_review_at', 'under_review_by', 'under_review_by_name',
                    'notes',
                    'is_closed', 'status', 'status_display', 'closing_date_display', 'can_edit',
                ]
                read_only_fields = ['id', 'is_closed', 'status', 'status_display', 'closing_date_display', 'can_edit']

            def get_is_closed(self, obj):
                return obj.is_closed

            def get_status(self, obj):
                return obj.status

            def get_status_display(self, obj):
                return obj.status_display

            def get_closing_date_display(self, obj):
                return obj.closing_date.strftime('%Y-%m-%d')

            def get_can_edit(self, obj):
                return obj.can_edit

            def get_manually_closed_by_name(self, obj):
                if obj.manually_closed_by:
                    return f"{obj.manually_closed_by.last_name}{obj.manually_closed_by.first_name}"
                return None

            def get_reopened_by_name(self, obj):
                if obj.reopened_by:
                    return f"{obj.reopened_by.last_name}{obj.reopened_by.first_name}"
                return None

            def get_under_review_by_name(self, obj):
                if obj.under_review_by:
                    return f"{obj.under_review_by.last_name}{obj.under_review_by.first_name}"
                return None

        return MonthlyBillingDeadlineSerializer

    @extend_schema(summary='締切状態一覧を取得')
    @action(detail=False, methods=['get'])
    def status_list(self, request):
        """現在月を中心とした締切状態一覧を取得"""
        from datetime import date

        today = date.today()
        tenant_id = getattr(request, 'tenant_id', None)
        if not tenant_id and hasattr(request, 'user') and hasattr(request.user, 'tenant_id'):
            tenant_id = request.user.tenant_id

        # テナントIDが取得できない場合はデフォルトテナントを使用
        if not tenant_id:
            from apps.tenants.models import Tenant
            default_tenant = Tenant.objects.first()
            if default_tenant:
                tenant_id = default_tenant.id

        # デフォルト締日を取得（PaymentProviderから）
        default_closing_day = 25
        provider = PaymentProvider.objects.filter(
            tenant_id=tenant_id,
            is_active=True
        ).first()
        if provider:
            default_closing_day = provider.closing_day or 25

        # 請求対象月の最小値を計算（締日を基準）
        # 締日より前: 現在月 + 1
        # 締日以降: 現在月 + 2
        if today.day < default_closing_day:
            min_billing_month = today.month + 1
        else:
            min_billing_month = today.month + 2
        min_billing_year = today.year
        if min_billing_month > 12:
            min_billing_month -= 12
            min_billing_year += 1

        # 過去3ヶ月〜未来6ヶ月の締切状態を取得
        months = []
        first_open_found = False
        current_billing_year = None
        current_billing_month = None

        for offset in range(-3, 7):
            year = today.year
            month = today.month + offset
            while month <= 0:
                month += 12
                year -= 1
            while month > 12:
                month -= 12
                year += 1

            deadline, created = MonthlyBillingDeadline.get_or_create_for_month(
                tenant_id=tenant_id,
                year=year,
                month=month,
                closing_day=default_closing_day
            )

            # 最初の未確定月を現在の請求月とする
            # ただし、締日を過ぎた月はスキップ（最小請求月以降のみ対象）
            is_current = False
            if not first_open_found and not deadline.is_closed:
                # 最小請求月以降かチェック
                if (year > min_billing_year) or (year == min_billing_year and month >= min_billing_month):
                    is_current = True
                    first_open_found = True
                    current_billing_year = year
                    current_billing_month = month

            months.append({
                'id': str(deadline.id),
                'year': deadline.year,
                'month': deadline.month,
                'label': f'{deadline.year}年{deadline.month}月分',
                'closing_day': deadline.closing_day,
                'closing_date': deadline.closing_date.strftime('%Y-%m-%d'),
                'status': deadline.status,
                'status_display': deadline.status_display,
                'is_closed': deadline.is_closed,
                'is_under_review': deadline.is_under_review,
                'can_edit': deadline.can_edit,
                'is_manually_closed': deadline.is_manually_closed,
                'is_reopened': deadline.is_reopened,
                'is_current': is_current,
            })

        return Response({
            'current_year': today.year,
            'current_month': today.month,
            'billing_year': current_billing_year,
            'billing_month': current_billing_month,
            'default_closing_day': default_closing_day,
            'months': months,
        })

    @extend_schema(summary='月の編集可否をチェック')
    @action(detail=False, methods=['get'])
    def check_editable(self, request):
        """指定月が編集可能かどうかをチェック"""
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not year or not month:
            return Response({'error': 'year と month を指定してください'}, status=400)

        try:
            year = int(year)
            month = int(month)
        except ValueError:
            return Response({'error': 'year と month は整数で指定してください'}, status=400)

        tenant_id = getattr(request, 'tenant_id', None)
        if not tenant_id and hasattr(request, 'user') and hasattr(request.user, 'tenant_id'):
            tenant_id = request.user.tenant_id
        # テナントIDが取得できない場合はデフォルトテナントを使用
        if not tenant_id:
            from apps.tenants.models import Tenant
            default_tenant = Tenant.objects.first()
            if default_tenant:
                tenant_id = default_tenant.id
        is_editable = MonthlyBillingDeadline.is_month_editable(tenant_id, year, month)

        return Response({
            'year': year,
            'month': month,
            'is_editable': is_editable,
            'message': f'{year}年{month}月分は{"編集可能" if is_editable else "締め済みのため編集不可"}です',
        })

    @extend_schema(summary='手動で締める')
    @action(detail=True, methods=['post'])
    def close_manually(self, request, pk=None):
        """指定月を手動で締める（確定データも生成）"""
        deadline = self.get_object()

        if deadline.is_closed:
            return Response({'error': 'この月は既に締め済みです'}, status=400)

        notes = request.data.get('notes', '')

        # 確定データを生成
        from apps.students.models import Student
        from apps.contracts.models import Contract
        from datetime import date

        year = deadline.year
        month = deadline.month
        tenant_id = deadline.tenant_id

        # 対象月の開始日・終了日
        billing_start = date(year, month, 1)
        if month == 12:
            billing_end = date(year + 1, 1, 1)
        else:
            billing_end = date(year, month + 1, 1)

        # 該当月に有効な契約がある生徒を取得
        student_ids_with_contracts = Contract.objects.filter(
            tenant_id=tenant_id,
            status=Contract.Status.ACTIVE,
            start_date__lt=billing_end,
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=billing_start)
        ).values_list('student_id', flat=True).distinct()

        students = Student.objects.filter(
            tenant_id=tenant_id,
            id__in=student_ids_with_contracts,
            deleted_at__isnull=True
        )

        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []

        # 保護者ごとの請求額を集計
        guardian_billing_totals = {}

        with transaction.atomic():
            for student in students:
                try:
                    guardian = student.guardian
                    if not guardian:
                        skipped_count += 1
                        continue

                    confirmed, was_created = ConfirmedBilling.create_from_contracts(
                        tenant_id=tenant_id,
                        student=student,
                        guardian=guardian,
                        year=year,
                        month=month,
                        user=request.user
                    )

                    if was_created:
                        created_count += 1
                        # 新規作成時のみ請求額を集計（既存の場合は既に計上済み）
                        if guardian.id not in guardian_billing_totals:
                            guardian_billing_totals[guardian.id] = {
                                'guardian': guardian,
                                'total': Decimal('0'),
                            }
                        guardian_billing_totals[guardian.id]['total'] += confirmed.total_amount or Decimal('0')
                    else:
                        if confirmed.status == ConfirmedBilling.Status.PAID:
                            skipped_count += 1
                        else:
                            updated_count += 1
                except Exception as e:
                    errors.append(str(e))

            # 保護者ごとにGuardianBalanceを更新（請求額を減算）
            for guardian_id, data in guardian_billing_totals.items():
                if data['total'] > 0:
                    balance_obj, _ = GuardianBalance.objects.get_or_create(
                        tenant_id=tenant_id,
                        guardian=data['guardian'],
                        defaults={'balance': 0}
                    )
                    balance_obj.add_billing(
                        amount=data['total'],
                        reason=f'{year}年{month}月分請求確定',
                    )

            # 締める
            deadline.close_manually(request.user, notes)

        return Response({
            'success': True,
            'message': f'{deadline.year}年{deadline.month}月分を締めました',
            'is_closed': deadline.is_closed,
            'created_count': created_count,
            'updated_count': updated_count,
            'skipped_count': skipped_count,
            'error_count': len(errors),
        })

    @extend_schema(summary='確認中にする')
    @action(detail=True, methods=['post'])
    def start_review(self, request, pk=None):
        """指定月を確認中にする（経理確認開始）"""
        deadline = self.get_object()

        if deadline.is_closed:
            return Response({'error': 'この月は既に確定済みです'}, status=400)

        if deadline.is_under_review:
            return Response({'error': 'この月は既に確認中です'}, status=400)

        deadline.start_review(request.user)

        return Response({
            'success': True,
            'message': f'{deadline.year}年{deadline.month}月分を確認中にしました',
            'status': deadline.status,
            'status_display': deadline.status_display,
        })

    @extend_schema(summary='確認中を解除する')
    @action(detail=True, methods=['post'])
    def cancel_review(self, request, pk=None):
        """確認中を解除して通常状態に戻す"""
        deadline = self.get_object()

        if not deadline.is_under_review:
            return Response({'error': 'この月は確認中ではありません'}, status=400)

        deadline.cancel_review(request.user)

        return Response({
            'success': True,
            'message': f'{deadline.year}年{deadline.month}月分の確認を解除しました',
            'status': deadline.status,
            'status_display': deadline.status_display,
        })

    @extend_schema(summary='締めを解除する')
    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        """指定月の締めを解除する（要理由）"""
        deadline = self.get_object()

        if not deadline.is_closed:
            return Response({'error': 'この月は締め済みではありません'}, status=400)

        reason = request.data.get('reason', '')
        if not reason:
            return Response({'error': '締め解除には理由が必要です'}, status=400)

        deadline.reopen(request.user, reason)

        return Response({
            'success': True,
            'message': f'{deadline.year}年{deadline.month}月分の締めを解除しました',
            'is_closed': deadline.is_closed,
        })

    @extend_schema(summary='締日設定を更新')
    @action(detail=True, methods=['patch'])
    def update_closing_day(self, request, pk=None):
        """締日を更新"""
        deadline = self.get_object()

        closing_day = request.data.get('closing_day')
        if closing_day is None:
            return Response({'error': 'closing_day を指定してください'}, status=400)

        if not (1 <= closing_day <= 31):
            return Response({'error': '締日は1〜31の間で設定してください'}, status=400)

        deadline.closing_day = closing_day
        deadline.save()

        return Response({
            'success': True,
            'closing_day': deadline.closing_day,
            'closing_date': deadline.closing_date.strftime('%Y-%m-%d'),
        })

    @extend_schema(summary='デフォルト締日を設定')
    @action(detail=False, methods=['post'])
    def set_default_closing_day(self, request):
        """デフォルト締日を設定（PaymentProviderに保存）"""
        closing_day = request.data.get('closing_day')
        if closing_day is None:
            return Response({'error': 'closing_day を指定してください'}, status=400)

        try:
            closing_day = int(closing_day)
        except ValueError:
            return Response({'error': 'closing_day は整数で指定してください'}, status=400)

        if not (1 <= closing_day <= 31):
            return Response({'error': '締日は1〜31の間で設定してください'}, status=400)

        tenant_id = getattr(request, 'tenant_id', None)
        if not tenant_id and hasattr(request, 'user') and hasattr(request.user, 'tenant_id'):
            tenant_id = request.user.tenant_id

        # テナントIDが取得できない場合はデフォルトテナントを使用
        if not tenant_id:
            from apps.tenants.models import Tenant
            default_tenant = Tenant.objects.first()
            if default_tenant:
                tenant_id = default_tenant.id

        # PaymentProviderのデフォルト締日を更新
        provider = PaymentProvider.objects.filter(
            tenant_id=tenant_id,
            is_active=True
        ).first()

        if provider:
            provider.closing_day = closing_day
            provider.save()
        else:
            # PaymentProviderがない場合は作成
            provider = PaymentProvider.objects.create(
                tenant_id=tenant_id,
                code='default',
                name='デフォルト',
                consignor_code='0000000000',
                closing_day=closing_day,
                is_active=True
            )

        return Response({
            'success': True,
            'closing_day': closing_day,
            'message': f'デフォルト締日を{closing_day}日に設定しました',
        })


# =============================================================================
# BankTransfer ViewSet
# =============================================================================
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

        # 管理者以外はテナントでフィルタ
        if not is_admin_user(self.request.user):
            queryset = queryset.filter(tenant_id=self.request.user.tenant_id)

        # ステータスでフィルタ
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # バッチIDでフィルタ
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

        # 保護者を特定（invoiceから、またはtransferから）
        guardian = invoice.guardian if invoice else transfer.guardian
        if not guardian:
            return Response({'error': '保護者が照合されていません。先に照合してください。'}, status=400)

        with transaction.atomic():
            from apps.billing.models import GuardianBalance, OffsetLog

            # 入金レコード作成
            payment_no = Payment.generate_payment_no(transfer.tenant_id)
            payment = Payment.objects.create(
                tenant_id=transfer.tenant_id,
                payment_no=payment_no,
                guardian=guardian,
                invoice=invoice,  # Noneの場合は未消込
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
                # 請求書の入金額を更新
                invoice.paid_amount += transfer.amount
                invoice.balance_due = invoice.total_amount - invoice.paid_amount
                if invoice.balance_due <= 0:
                    invoice.status = Invoice.Status.PAID
                elif invoice.paid_amount > 0:
                    invoice.status = Invoice.Status.PARTIAL
                invoice.save()

                # 振込ステータス更新（消込完了）
                transfer.apply_to_invoice(invoice, request.user)
                message = '入金処理を完了しました（消込済み）'
            else:
                # 請求書なしの場合は入金確認のみ
                transfer.status = BankTransfer.Status.APPLIED
                transfer.invoice = None
                # matched_by/matched_at を使用（applied_by/applied_at フィールドは存在しない）
                if not transfer.matched_at:
                    transfer.matched_by = request.user
                    transfer.matched_at = timezone.now()
                transfer.save()
                message = '入金確認を完了しました（未消込）'

            # ConfirmedBillingも更新（未入金のものを探す）
            confirmed_billings = ConfirmedBilling.objects.filter(
                guardian=guardian,
                status__in=[ConfirmedBilling.Status.CONFIRMED, ConfirmedBilling.Status.UNPAID, ConfirmedBilling.Status.PARTIAL],
            ).order_by(
                # 残高が振込額と一致するものを優先
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

            # GuardianBalanceに入金を記録（常に実行）
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

            # バッチのカウント更新
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
                        # 入金処理
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


# =============================================================================
# BankTransferImport ViewSet
# =============================================================================
@extend_schema_view(
    list=extend_schema(summary='振込インポートバッチ一覧'),
    retrieve=extend_schema(summary='振込インポートバッチ詳細'),
)
class BankTransferImportViewSet(viewsets.ModelViewSet):
    """振込インポート管理API"""
    serializer_class = BankTransferImportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from apps.core.permissions import is_admin_user

        queryset = BankTransferImport.objects.select_related('imported_by', 'confirmed_by')

        # 管理者以外はテナントでフィルタ
        if not is_admin_user(self.request.user):
            queryset = queryset.filter(tenant_id=self.request.user.tenant_id)

        return queryset.order_by('-imported_at')

    def _detect_and_parse_bank_raw_csv(self, file_content):
        """銀行の生CSVフォーマットを検出してパース

        銀行の生データ形式:
        - 行タイプ1: ヘッダー情報
        - 行タイプ2: 振込データ (日付, 空, 振込種別, 振込人名義, 金額, ...)
        """
        import csv
        import io
        import re

        # Shift-JISでデコード
        try:
            content = file_content.decode('shift_jis')
        except:
            try:
                content = file_content.decode('utf-8-sig')
            except:
                content = file_content.decode('utf-8')

        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        if not rows:
            return None, "ファイルにデータがありません"

        # 行タイプ2で始まる行があれば銀行生データと判定
        is_bank_raw = any(row and row[0] == '2' for row in rows)

        if not is_bank_raw:
            return None, None  # 通常のCSVとして処理

        # 銀行生データをパース
        # フォーマット検出: 最初のデータ行を確認
        # パターン1: 2,日付,,振込種別,名義,金額,... (row[2]が空)
        # パターン2: 2,日付,振込種別,名義,?,金額,... (row[2]が振込種別)
        first_data_row = None
        for row in rows:
            if row and row[0] == '2':
                first_data_row = row
                break

        if not first_data_row:
            return [], None  # データなし

        # フォーマット判定: row[2]が空かどうか
        is_pattern1 = len(first_data_row) > 2 and first_data_row[2] == ''

        transfers = []
        for row in rows:
            if not row or row[0] != '2':
                continue

            # 日付（row[1]）: 2024.12.23 → 2024-12-23
            date_str = row[1] if len(row) > 1 else ""
            if date_str:
                date_str = date_str.replace(".", "-")

            if is_pattern1:
                # パターン1: 2,日付,,振込種別,名義,金額,...
                payer_raw = row[4] if len(row) > 4 else ""
                amount_str = row[5] if len(row) > 5 else "0"
            else:
                # パターン2: 2,日付,振込種別,名義,?,金額,...
                payer_raw = row[3] if len(row) > 3 else ""
                amount_str = row[5] if len(row) > 5 else "0"

            guardian_id, payer_name = self._parse_payer_name(payer_raw)

            try:
                amount = int(amount_str.replace(',', ''))
            except:
                amount = 0

            if date_str and amount > 0:
                transfers.append({
                    'transfer_date': date_str,
                    'amount': amount,
                    'payer_name': payer_name,
                    'payer_name_kana': payer_name,  # 名義カナも同じ
                    'guardian_id_hint': guardian_id,  # マッチング用のヒント
                    'source_bank_name': '',
                    'source_branch_name': '',
                })

        return transfers, None

    def _parse_payer_name(self, name_str):
        """振込人名義を解析（ID部分を分離）

        例: ８２１８８５９コジマ → ID: 8218859, 名義: コジマ
        例: カワカミ　ユミコ → ID: なし, 名義: カワカミ ユミコ
        """
        import re

        if not name_str:
            return "", ""

        # 全角数字を半角に変換
        name_str = name_str.translate(str.maketrans('０１２３４５６７８９', '0123456789'))

        # 先頭の数字部分を抽出
        match = re.match(r'^(\d+)\s*(.*)$', name_str)
        if match:
            guardian_id = match.group(1)
            name = match.group(2).strip()
            # 名前の全角スペースを半角に
            name = name.replace('　', ' ')
            return guardian_id, name
        else:
            # 数字がない場合はそのまま名前として使用
            name = name_str.replace('　', ' ')
            return "", name

    @extend_schema(summary='振込データをインポート')
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser])
    def upload(self, request):
        """CSVまたはExcelファイルから振込データをインポート

        銀行の生CSVデータ（Shift-JIS、行タイプ形式）にも対応。
        """
        import pandas as pd
        from datetime import datetime
        import io
        import traceback

        if 'file' not in request.FILES:
            return Response({'error': 'ファイルを指定してください'}, status=400)

        file = request.FILES['file']
        logger.warning(f"[BankTransferImport] File size: {file.size}")
        file_name = file.name.lower()

        # カラムマッピング取得
        date_col = request.data.get('date_column', '振込日')
        amount_col = request.data.get('amount_column', '金額')
        payer_name_col = request.data.get('payer_name_column', '振込人名義')
        payer_kana_col = request.data.get('payer_name_kana_column', '振込人名義カナ')
        bank_col = request.data.get('bank_name_column', '銀行名')
        branch_col = request.data.get('branch_name_column', '支店名')

        try:
            logger.warning(f"[BankTransferImport] Processing file: {file_name}")
            # CSVの場合、まず銀行生データかどうかを検出
            if file_name.endswith('.csv'):
                file_content = file.read()
                logger.warning(f"[BankTransferImport] File content length: {len(file_content)} bytes")

                try:
                    bank_transfers, error = self._detect_and_parse_bank_raw_csv(file_content)
                    logger.warning(f"[BankTransferImport] Parse result: transfers={len(bank_transfers) if bank_transfers else None}, error={error}")
                except Exception as parse_e:
                    logger.error(f"[BankTransferImport] Parse exception: {parse_e}")
                    raise

                if error:
                    logger.warning(f"[BankTransferImport] Parse error: {error}")
                    return Response({'error': error}, status=400)

                if bank_transfers is not None:
                    logger.warning(f"[BankTransferImport] Detected bank raw format, {len(bank_transfers)} transfers")
                    # 銀行生データとして処理
                    original_file_name = file.name
                    return self._import_bank_raw_data(request, bank_transfers, original_file_name)

                # 通常のCSVとして処理
                file.seek(0)  # ファイルポインタをリセット
                try:
                    df = pd.read_csv(io.BytesIO(file_content), encoding='utf-8-sig')
                except:
                    df = pd.read_csv(io.BytesIO(file_content), encoding='utf-8')
                file_type = 'csv'
            elif file_name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file)
                file_type = 'excel'
            else:
                return Response({'error': 'CSVまたはExcelファイルのみ対応しています'}, status=400)

            if len(df) == 0:
                return Response({'error': 'ファイルにデータがありません'}, status=400)

            tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)

            # インポートバッチ作成
            import_batch = BankTransferImport.objects.create(
                tenant_id=tenant_id,
                file_name=file.name,
                file_type=file_type,
                imported_by=request.user,
            )

            transfers_created = []
            errors = []

            for idx, row in df.iterrows():
                try:
                    # 日付パース
                    transfer_date = row.get(date_col)
                    if pd.isna(transfer_date):
                        errors.append({'row': idx + 2, 'error': '振込日が空です'})
                        continue

                    if isinstance(transfer_date, str):
                        transfer_date = datetime.strptime(transfer_date, '%Y-%m-%d').date()
                    elif hasattr(transfer_date, 'date'):
                        transfer_date = transfer_date.date()

                    # 金額パース
                    amount = row.get(amount_col)
                    if pd.isna(amount):
                        errors.append({'row': idx + 2, 'error': '金額が空です'})
                        continue
                    amount = Decimal(str(amount).replace(',', ''))

                    # 振込人名義
                    payer_name = row.get(payer_name_col, '')
                    if pd.isna(payer_name) or not payer_name:
                        errors.append({'row': idx + 2, 'error': '振込人名義が空です'})
                        continue

                    # 振込データ作成
                    transfer = BankTransfer.objects.create(
                        tenant_id=tenant_id,
                        transfer_date=transfer_date,
                        amount=amount,
                        payer_name=str(payer_name),
                        payer_name_kana=str(row.get(payer_kana_col, '')) if not pd.isna(row.get(payer_kana_col)) else '',
                        source_bank_name=str(row.get(bank_col, '')) if not pd.isna(row.get(bank_col)) else '',
                        source_branch_name=str(row.get(branch_col, '')) if not pd.isna(row.get(branch_col)) else '',
                        status=BankTransfer.Status.PENDING,
                        import_batch_id=str(import_batch.id),
                        import_row_no=idx + 1,
                    )
                    transfers_created.append(transfer)

                except Exception as e:
                    errors.append({'row': idx + 2, 'error': str(e)})

            # バッチカウント更新
            import_batch.update_counts()

            # 自動照合を試みる
            auto_matched = self._auto_match_transfers(transfers_created, request.user)

            # バッチカウント再更新
            import_batch.update_counts()

            return Response({
                'success': True,
                'batch_id': str(import_batch.id),
                'batch_no': import_batch.batch_no,
                'total_count': len(transfers_created),
                'error_count': len(errors),
                'auto_matched_count': auto_matched,
                'errors': errors[:10],  # 最初の10件のエラーのみ返す
            })

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            return Response({'error': f'ファイルの処理中にエラーが発生しました: {str(e)}', 'traceback': tb}, status=400)

    def _auto_match_transfers(self, transfers, user):
        """振込データを自動照合"""
        from apps.students.models import Guardian
        matched_count = 0

        for transfer in transfers:
            # 振込人名義で完全一致する保護者を探す
            payer_name = transfer.payer_name.replace('　', ' ').strip()

            # 姓名を分割
            name_parts = payer_name.split()
            if len(name_parts) >= 2:
                last_name = name_parts[0]
                first_name = name_parts[-1]

                # 完全一致検索
                guardian = Guardian.objects.filter(
                    tenant_id=transfer.tenant_id,
                    deleted_at__isnull=True,
                    last_name=last_name,
                    first_name=first_name,
                ).first()

                if not guardian and transfer.payer_name_kana:
                    # カナでも検索
                    kana_parts = transfer.payer_name_kana.replace('　', ' ').split()
                    if len(kana_parts) >= 2:
                        guardian = Guardian.objects.filter(
                            tenant_id=transfer.tenant_id,
                            deleted_at__isnull=True,
                            last_name_kana=kana_parts[0],
                            first_name_kana=kana_parts[-1],
                        ).first()

                if guardian:
                    # 金額が一致する未払い請求書を探す
                    matching_invoice = Invoice.objects.filter(
                        guardian=guardian,
                        status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL, Invoice.Status.OVERDUE],
                        balance_due=transfer.amount,
                    ).order_by('billing_year', 'billing_month').first()

                    if matching_invoice:
                        transfer.guardian = guardian
                        transfer.status = BankTransfer.Status.MATCHED
                        transfer.matched_by = user
                        transfer.matched_at = timezone.now()
                        transfer.save()
                        matched_count += 1
                    else:
                        # 金額が一致しなくても保護者だけ照合
                        transfer.guardian = guardian
                        transfer.status = BankTransfer.Status.MATCHED
                        transfer.matched_by = user
                        transfer.matched_at = timezone.now()
                        transfer.save()
                        matched_count += 1

        return matched_count

    def _import_bank_raw_data(self, request, transfers_data, file_name):
        """銀行生データをインポート"""
        from datetime import datetime
        from apps.students.models import Guardian
        from apps.tenants.models import Tenant

        tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)

        # テナントIDがない場合はデフォルトテナントを使用
        if not tenant_id:
            default_tenant = Tenant.objects.first()
            if default_tenant:
                tenant_id = default_tenant.id

        # インポートバッチ作成
        import_batch = BankTransferImport.objects.create(
            tenant_id=tenant_id,
            file_name=file_name,
            file_type='csv',
            imported_by=request.user,
        )

        transfers_created = []
        errors = []
        auto_matched_count = 0

        for idx, data in enumerate(transfers_data):
            try:
                # 日付パース
                transfer_date = datetime.strptime(data['transfer_date'], '%Y-%m-%d').date()

                # 振込データ作成
                guardian_id_hint = data.get('guardian_id_hint', '')

                transfer = BankTransfer.objects.create(
                    tenant_id=tenant_id,
                    transfer_date=transfer_date,
                    amount=Decimal(str(data['amount'])),
                    payer_name=data['payer_name'],
                    payer_name_kana=data['payer_name_kana'],
                    guardian_no_hint=guardian_id_hint,
                    source_bank_name=data['source_bank_name'],
                    source_branch_name=data['source_branch_name'],
                    status=BankTransfer.Status.PENDING,
                    import_batch_id=str(import_batch.id),
                    import_row_no=idx + 1,
                )

                # guardian_id_hintがあれば、それで自動照合を試みる
                if guardian_id_hint:
                    # guardian_noで検索
                    guardian = Guardian.objects.filter(
                        tenant_id=tenant_id,
                        guardian_no=guardian_id_hint,
                        deleted_at__isnull=True,
                    ).first()

                    if guardian:
                        transfer.guardian = guardian
                        transfer.status = BankTransfer.Status.MATCHED
                        transfer.matched_by = request.user
                        transfer.matched_at = timezone.now()
                        transfer.save()
                        auto_matched_count += 1

                transfers_created.append(transfer)

            except Exception as e:
                errors.append({'row': idx + 1, 'error': str(e)})

        # まだマッチしていない振込に対して通常の自動照合を実行
        unmatched_transfers = [t for t in transfers_created if t.status == BankTransfer.Status.PENDING]
        if unmatched_transfers:
            auto_matched_count += self._auto_match_transfers(unmatched_transfers, request.user)

        # バッチカウント更新
        import_batch.update_counts()

        return Response({
            'success': True,
            'batch_id': str(import_batch.id),
            'batch_no': import_batch.batch_no,
            'total_count': len(transfers_created),
            'error_count': len(errors),
            'auto_matched_count': auto_matched_count,
            'format_detected': 'bank_raw',
            'errors': errors[:10],
        })

    @extend_schema(summary='インポートバッチを確定')
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """インポートバッチを確定し、照合済みの振込を入金処理する"""
        import_batch = self.get_object()

        if import_batch.confirmed_at:
            return Response({'error': 'このバッチは既に確定済みです'}, status=400)

        # 照合済みの振込を取得
        matched_transfers = BankTransfer.objects.filter(
            import_batch_id=str(import_batch.id),
            status=BankTransfer.Status.MATCHED,
            guardian__isnull=False,
        )

        applied_count = 0
        errors = []

        with transaction.atomic():
            for transfer in matched_transfers:
                try:
                    # 未払い請求書を取得（金額一致優先）
                    invoice = Invoice.objects.filter(
                        guardian=transfer.guardian,
                        status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL, Invoice.Status.OVERDUE],
                    ).order_by(
                        # 金額一致するものを優先
                        models.Case(
                            models.When(balance_due=transfer.amount, then=0),
                            default=1,
                        ),
                        'billing_year',
                        'billing_month',
                    ).first()

                    # 入金処理（Invoiceがなくても実行）
                    payment_no = Payment.generate_payment_no(transfer.tenant_id)
                    payment = Payment.objects.create(
                        tenant_id=transfer.tenant_id,
                        payment_no=payment_no,
                        guardian=transfer.guardian,
                        invoice=invoice,  # Noneの場合もあり
                        payment_date=transfer.transfer_date,
                        amount=transfer.amount,
                        method=Payment.Method.BANK_TRANSFER,
                        status=Payment.Status.SUCCESS,
                        payer_name=transfer.payer_name,
                        bank_name=transfer.source_bank_name,
                        notes=f'振込インポート確定: {import_batch.batch_no}',
                        registered_by=request.user,
                    )

                    if invoice:
                        # 請求書更新
                        invoice.paid_amount += transfer.amount
                        invoice.balance_due = invoice.total_amount - invoice.paid_amount
                        if invoice.balance_due <= 0:
                            invoice.status = Invoice.Status.PAID
                        elif invoice.paid_amount > 0:
                            invoice.status = Invoice.Status.PARTIAL
                        invoice.save()

                        # 振込ステータス更新
                        transfer.invoice = invoice

                    # ConfirmedBillingも更新（未入金のものを探す）
                    confirmed_billings = ConfirmedBilling.objects.filter(
                        guardian=transfer.guardian,
                        status__in=[ConfirmedBilling.Status.CONFIRMED, ConfirmedBilling.Status.UNPAID, ConfirmedBilling.Status.PARTIAL],
                    ).order_by(
                        # 残高が振込額と一致するものを優先
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

                    # GuardianBalanceに入金を記録
                    balance_obj, _ = GuardianBalance.objects.get_or_create(
                        tenant_id=transfer.tenant_id,
                        guardian=transfer.guardian,
                        defaults={'balance': 0}
                    )
                    balance_obj.add_payment(
                        amount=transfer.amount,
                        reason=f'銀行振込による入金（{transfer.payer_name}）',
                        payment=payment,
                    )

                    transfer.status = BankTransfer.Status.APPLIED
                    transfer.save()
                    applied_count += 1

                except Exception as e:
                    errors.append({
                        'transfer_id': str(transfer.id),
                        'payer_name': transfer.payer_name,
                        'error': str(e),
                    })

            # バッチ確定
            import_batch.confirm(request.user)
            import_batch.update_counts()

        return Response({
            'success': True,
            'applied_count': applied_count,
            'error_count': len(errors),
            'errors': errors[:10],
        })

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

        # 検索条件がない場合
        if not query and not guardian_no and not amount:
            return Response({'error': '検索条件を指定してください'}, status=400)

        tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)

        # テナントIDが取得できない場合はデフォルトテナントを使用
        if not tenant_id:
            from apps.tenants.models import Tenant
            default_tenant = Tenant.objects.first()
            if default_tenant:
                tenant_id = default_tenant.id

        guardians = Guardian.objects.filter(
            deleted_at__isnull=True,
        )
        if tenant_id:
            guardians = guardians.filter(tenant_id=tenant_id)

        # 複数条件での検索（すべてAND条件）

        # 保護者番号で検索
        if guardian_no:
            guardians = guardians.filter(
                models.Q(guardian_no__icontains=guardian_no) |
                models.Q(old_id__icontains=guardian_no)
            )

        # 名前で検索
        if query and len(query) >= 1:
            guardians = guardians.filter(
                models.Q(last_name__icontains=query) |
                models.Q(first_name__icontains=query) |
                models.Q(last_name_kana__icontains=query) |
                models.Q(first_name_kana__icontains=query)
            )

        # 金額で検索（未払い請求金額と一致する保護者を取得）
        if amount:
            try:
                amount_decimal = Decimal(amount)
                # 未払い金額が一致する請求書を持つ保護者を取得
                guardian_ids_with_amount = Invoice.objects.filter(
                    tenant_id=tenant_id,
                    status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL, Invoice.Status.OVERDUE],
                    balance_due=amount_decimal
                ).values_list('guardian_id', flat=True).distinct()

                # ConfirmedBillingからも検索
                cb_guardian_ids = ConfirmedBilling.objects.filter(
                    tenant_id=tenant_id,
                    status__in=[ConfirmedBilling.Status.CONFIRMED, ConfirmedBilling.Status.UNPAID, ConfirmedBilling.Status.PARTIAL],
                    balance=amount_decimal
                ).values_list('guardian_id', flat=True).distinct()

                all_guardian_ids = set(guardian_ids_with_amount) | set(cb_guardian_ids)
                guardians = guardians.filter(id__in=all_guardian_ids)
            except (ValueError, InvalidOperation):
                return Response({'error': '金額の形式が正しくありません'}, status=400)

        guardians = guardians[:20]

        results = []
        for g in guardians:
            # 未払い請求書を取得（Invoice）
            invoices = Invoice.objects.filter(
                guardian=g,
                status__in=[Invoice.Status.ISSUED, Invoice.Status.PARTIAL, Invoice.Status.OVERDUE]
            ).order_by('-billing_year', '-billing_month')[:5]

            # 未払いConfirmedBillingも取得
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

            # ConfirmedBillingからも請求情報を追加（重複を避ける）
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

        return Response({'guardians': results})


# =============================================================================
# ConfirmedBilling ViewSet - 請求確定データ管理
# =============================================================================
@extend_schema_view(
    list=extend_schema(summary='請求確定一覧'),
    retrieve=extend_schema(summary='請求確定詳細'),
)
class ConfirmedBillingViewSet(viewsets.ModelViewSet):
    """請求確定データ管理API

    締日確定時に生徒ごとの請求データをスナップショットとして保存。
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from apps.core.permissions import is_admin_user

        queryset = ConfirmedBilling.objects.select_related(
            'student', 'guardian', 'billing_deadline', 'confirmed_by'
        )

        # 管理者以外はテナントでフィルタ
        if not is_admin_user(self.request.user):
            queryset = queryset.filter(tenant_id=self.request.user.tenant_id)

        # 年月でフィルタ
        year = self.request.query_params.get('year')
        month = self.request.query_params.get('month')
        if year:
            queryset = queryset.filter(year=int(year))
        if month:
            queryset = queryset.filter(month=int(month))

        # ステータスでフィルタ
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # 保護者でフィルタ
        guardian_id = self.request.query_params.get('guardian_id')
        if guardian_id:
            queryset = queryset.filter(guardian_id=guardian_id)

        # 生徒でフィルタ
        student_id = self.request.query_params.get('student_id')
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        # 検索（名前・ID）
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(student__last_name__icontains=search) |
                models.Q(student__first_name__icontains=search) |
                models.Q(student__last_name_kana__icontains=search) |
                models.Q(student__first_name_kana__icontains=search) |
                models.Q(student__student_no__icontains=search) |
                models.Q(student__old_id__icontains=search) |
                models.Q(guardian__last_name__icontains=search) |
                models.Q(guardian__first_name__icontains=search) |
                models.Q(guardian__guardian_no__icontains=search) |
                models.Q(guardian__old_id__icontains=search)
            )

        return queryset.order_by('-year', '-month', '-confirmed_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return ConfirmedBillingListSerializer
        return ConfirmedBillingSerializer

    @extend_schema(summary='請求確定データを生成')
    @action(detail=False, methods=['post'])
    def create_confirmed_billing(self, request):
        """指定月の請求確定データを生成

        締日確定時に呼び出される。StudentItemのスナップショットを作成。
        """
        serializer = ConfirmedBillingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        year = data['year']
        month = data['month']
        student_ids = data.get('student_ids')

        tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)
        if not tenant_id:
            from apps.tenants.models import Tenant
            default_tenant = Tenant.objects.first()
            if default_tenant:
                tenant_id = default_tenant.id

        from apps.students.models import Student
        from apps.contracts.models import StudentItem

        # 対象生徒を取得
        from datetime import date
        from apps.contracts.models import Contract

        # 対象月の開始日・終了日
        billing_start = date(year, month, 1)
        if month == 12:
            billing_end = date(year + 1, 1, 1)
        else:
            billing_end = date(year, month + 1, 1)

        if student_ids:
            students = Student.objects.filter(
                tenant_id=tenant_id,
                id__in=student_ids,
                deleted_at__isnull=True
            )
        else:
            # 該当月に有効な契約がある生徒を取得
            student_ids_with_contracts = Contract.objects.filter(
                tenant_id=tenant_id,
                status=Contract.Status.ACTIVE,
                start_date__lt=billing_end,
            ).filter(
                models.Q(end_date__isnull=True) | models.Q(end_date__gte=billing_start)
            ).values_list('student_id', flat=True).distinct()

            students = Student.objects.filter(
                tenant_id=tenant_id,
                id__in=student_ids_with_contracts,
                deleted_at__isnull=True
            )

        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []

        with transaction.atomic():
            for student in students:
                try:
                    # 保護者を取得
                    guardian = student.guardian

                    if not guardian:
                        errors.append({
                            'student_id': str(student.id),
                            'student_name': student.full_name,
                            'error': '保護者が設定されていません'
                        })
                        skipped_count += 1
                        continue

                    # 確定データを作成（Contractベース）
                    confirmed, was_created = ConfirmedBilling.create_from_contracts(
                        tenant_id=tenant_id,
                        student=student,
                        guardian=guardian,
                        year=year,
                        month=month,
                        user=request.user
                    )

                    if was_created:
                        created_count += 1
                    else:
                        if confirmed.status == ConfirmedBilling.Status.PAID:
                            skipped_count += 1
                        else:
                            updated_count += 1

                except Exception as e:
                    errors.append({
                        'student_id': str(student.id),
                        'student_name': student.full_name,
                        'error': str(e)
                    })

        return Response({
            'success': True,
            'year': year,
            'month': month,
            'created_count': created_count,
            'updated_count': updated_count,
            'skipped_count': skipped_count,
            'error_count': len(errors),
            'errors': errors[:10],
        })

    @extend_schema(summary='締日確定一括処理')
    @action(detail=False, methods=['post'])
    def confirm_batch(self, request):
        """締日確定一括処理

        1. 請求確定データを生成
        2. 締日を締める（オプション）
        """
        serializer = BillingConfirmBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        year = data['year']
        month = data['month']
        close_deadline = data.get('close_deadline', True)

        tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)
        if not tenant_id:
            from apps.tenants.models import Tenant
            default_tenant = Tenant.objects.first()
            if default_tenant:
                tenant_id = default_tenant.id

        # 締日を取得または作成
        deadline, _ = MonthlyBillingDeadline.get_or_create_for_month(
            tenant_id=tenant_id,
            year=year,
            month=month
        )

        if deadline.is_closed:
            return Response({
                'error': f'{year}年{month}月分は既に締め済みです'
            }, status=400)

        # 請求確定データを生成
        create_result = self.create_confirmed_billing(request)

        # 締日を締める
        if close_deadline:
            deadline.close_manually(request.user, f'一括確定処理により締め')

        return Response({
            'success': True,
            'year': year,
            'month': month,
            'billing_result': create_result.data,
            'deadline_closed': close_deadline,
            'is_closed': deadline.is_closed,
        })

    @extend_schema(summary='入金を記録')
    @action(detail=True, methods=['post'])
    def record_payment(self, request, pk=None):
        """確定データに入金を記録"""
        confirmed = self.get_object()
        amount = request.data.get('amount')

        if not amount:
            return Response({'error': '金額を指定してください'}, status=400)

        try:
            amount = Decimal(str(amount))
        except:
            return Response({'error': '金額の形式が不正です'}, status=400)

        if amount <= 0:
            return Response({'error': '金額は正の数で指定してください'}, status=400)

        confirmed.paid_amount += amount
        confirmed.update_payment_status()

        return Response({
            'success': True,
            'paid_amount': int(confirmed.paid_amount),
            'balance': int(confirmed.balance),
            'status': confirmed.status,
            'status_display': confirmed.get_status_display(),
        })

    @extend_schema(summary='月別サマリを取得')
    @action(detail=False, methods=['get'])
    def monthly_summary(self, request):
        """指定月の請求確定サマリを取得"""
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not year or not month:
            return Response({'error': 'year と month を指定してください'}, status=400)

        tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)
        if not tenant_id:
            from apps.tenants.models import Tenant
            default_tenant = Tenant.objects.first()
            if default_tenant:
                tenant_id = default_tenant.id

        confirmed_billings = ConfirmedBilling.objects.filter(
            tenant_id=tenant_id,
            year=int(year),
            month=int(month),
            deleted_at__isnull=True
        )

        total_count = confirmed_billings.count()
        total_amount = sum(c.total_amount for c in confirmed_billings)
        total_paid = sum(c.paid_amount for c in confirmed_billings)
        total_balance = sum(c.balance for c in confirmed_billings)

        # ステータス別集計
        status_counts = {}
        for status_choice in ConfirmedBilling.Status.choices:
            status_code = status_choice[0]
            count = confirmed_billings.filter(status=status_code).count()
            status_counts[status_code] = {
                'label': status_choice[1],
                'count': count,
            }

        # 支払方法別集計
        payment_method_counts = {}
        for method_choice in ConfirmedBilling.PaymentMethod.choices:
            method_code = method_choice[0]
            count = confirmed_billings.filter(payment_method=method_code).count()
            amount = sum(c.total_amount for c in confirmed_billings.filter(payment_method=method_code))
            payment_method_counts[method_code] = {
                'label': method_choice[1],
                'count': count,
                'amount': int(amount),
            }

        return Response({
            'year': int(year),
            'month': int(month),
            'total_count': total_count,
            'total_amount': int(total_amount),
            'total_paid': int(total_paid),
            'total_balance': int(total_balance),
            'collection_rate': round(float(total_paid / total_amount * 100), 1) if total_amount > 0 else 0,
            'status_counts': status_counts,
            'payment_method_counts': payment_method_counts,
        })

    @extend_schema(summary='確定データをCSVエクスポート')
    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """指定月の請求確定データをCSVでエクスポート"""
        import csv
        from django.http import HttpResponse

        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not year or not month:
            return Response({'error': 'year と month を指定してください'}, status=400)

        tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)
        if not tenant_id:
            from apps.tenants.models import Tenant
            default_tenant = Tenant.objects.first()
            if default_tenant:
                tenant_id = default_tenant.id

        confirmed_billings = ConfirmedBilling.objects.filter(
            tenant_id=tenant_id,
            year=int(year),
            month=int(month),
            deleted_at__isnull=True
        ).select_related('student', 'guardian').order_by('guardian__guardian_no', 'student__student_no')

        # CSVレスポンスを作成
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="confirmed_billing_{year}_{month}.csv"'

        writer = csv.writer(response)

        # ヘッダー行
        writer.writerow([
            '生徒番号',
            '生徒名',
            '生徒名カナ',
            '保護者番号',
            '保護者名',
            '保護者名カナ',
            '請求年',
            '請求月',
            '請求額',
            '入金済',
            '残高',
            '支払方法',
            'ステータス',
            '確定日時',
        ])

        # データ行
        for billing in confirmed_billings:
            student = billing.student
            guardian = billing.guardian

            writer.writerow([
                student.student_no if student else '',
                f'{student.last_name} {student.first_name}' if student else '',
                f'{student.last_name_kana} {student.first_name_kana}' if student else '',
                guardian.guardian_no if guardian else '',
                f'{guardian.last_name} {guardian.first_name}' if guardian else '',
                f'{guardian.last_name_kana} {guardian.first_name_kana}' if guardian else '',
                billing.year,
                billing.month,
                int(billing.total_amount),
                int(billing.paid_amount),
                int(billing.balance),
                billing.get_payment_method_display(),
                billing.get_status_display(),
                billing.confirmed_at.strftime('%Y/%m/%d %H:%M') if billing.confirmed_at else '',
            ])

        return response
