"""
Billing Export Mixin - CSVエクスポート
"""
import csv
from datetime import datetime

from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema

from apps.billing.models import ConfirmedBilling, PaymentProvider, GuardianBalance
from apps.core.exceptions import ValidationException


def _get_tenant_id(request):
    """リクエストからテナントIDを取得"""
    tenant_id = getattr(request, 'tenant_id', None) or getattr(request.user, 'tenant_id', None)
    if not tenant_id:
        from apps.tenants.models import Tenant
        default_tenant = Tenant.objects.first()
        if default_tenant:
            tenant_id = default_tenant.id
    return tenant_id


class BillingExportMixin:
    """CSVエクスポート関連アクション"""

    @extend_schema(summary='確定データをCSVエクスポート')
    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """指定月の請求確定データをCSVでエクスポート"""
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        if not year or not month:
            raise ValidationException('year と month を指定してください')

        tenant_id = _get_tenant_id(request)

        confirmed_billings = ConfirmedBilling.objects.filter(
            tenant_id=tenant_id,
            year=int(year),
            month=int(month),
            deleted_at__isnull=True
        ).select_related('student', 'guardian').order_by('guardian__guardian_no', 'student__student_no')

        # 保護者残高を取得
        guardian_balances = {}
        for gb in GuardianBalance.objects.filter(tenant_id=tenant_id, deleted_at__isnull=True).select_related('guardian'):
            if gb.guardian_id:
                guardian_balances[gb.guardian_id] = gb.balance

        balance_exported_guardians = set()

        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="confirmed_billing_{year}_{month}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            '保護者ID', '生徒ID', '保護者', '学年', '生徒名',
            '契約ID', 'テーブル名', 'ブランド名', '契約名', '削除',
            '請求ID', '請求カテ', '顧客表示用(明細T3のブランド月額料金)', '合計',
            'ブランド退会日', '全退会日', '休会日', '復会日',
        ])

        for billing in confirmed_billings:
            self._write_billing_rows(writer, billing, guardian_balances, balance_exported_guardians)

        return response

    def _write_billing_rows(self, writer, billing, guardian_balances, balance_exported_guardians):
        """請求データの行を書き込み"""
        student = billing.student
        guardian = billing.guardian
        items_snapshot = billing.items_snapshot or []
        discounts_snapshot = billing.discounts_snapshot or []

        student_no = student.student_no if student else ''
        student_name = f'{student.last_name}{student.first_name}' if student else ''
        guardian_no = guardian.guardian_no if guardian else ''
        guardian_last_name = guardian.last_name if guardian else ''
        grade_text = student.grade_text if student else ''

        withdrawal_date_str = billing.withdrawal_date.isoformat() if billing.withdrawal_date else ''
        brand_withdrawal_dates = billing.brand_withdrawal_dates or {}
        suspension_date_str = billing.suspension_date.isoformat() if billing.suspension_date else ''
        return_date_str = billing.return_date.isoformat() if billing.return_date else ''

        # アイテム行
        if items_snapshot:
            for item in items_snapshot:
                contract_id = item.get('old_id', '') or item.get('contract_no', '')
                if contract_id and '_契約情報' not in contract_id and '_10T3' not in contract_id:
                    parts = contract_id.split('_')
                    if len(parts) >= 1:
                        contract_id = f"{parts[0]}_10T3_契約情報"

                billing_id = item.get('old_id', '') or item.get('id', '')
                contract_name = item.get('course_name', '') or item.get('product_name_short', '') or ''
                item_type_display = item.get('item_type_display', '') or item.get('item_type', '') or ''
                product_display = item.get('product_name', '') or ''
                brand_id = item.get('brand_id', '')
                brand_withdrawal_date = brand_withdrawal_dates.get(brand_id, '') if brand_id else ''

                writer.writerow([
                    guardian_no, student_no, guardian_last_name, grade_text, student_name,
                    contract_id, 'T3_契約情報', item.get('brand_name', ''), contract_name, '',
                    billing_id, item_type_display, product_display,
                    int(float(item.get('final_price') or item.get('subtotal') or item.get('unit_price') or 0)),
                    brand_withdrawal_date, withdrawal_date_str, suspension_date_str, return_date_str,
                ])

        # 割引行
        if discounts_snapshot:
            for discount in discounts_snapshot:
                discount_amount = int(float(discount.get('amount', 0) or 0))
                discount_name = discount.get('discount_name', '')

                if 'FS' in discount_name or '友達' in discount_name or '紹介' in discount_name:
                    table_name = 'T6_割引情報'
                elif 'マイル' in discount_name or '家族' in discount_name:
                    table_name = '家族割'
                else:
                    table_name = 'T6_割引情報'

                writer.writerow([
                    guardian_no, '', guardian_last_name, '', '',
                    '', table_name, '', discount_name, '',
                    discount.get('old_id', ''), '割引', discount_name, -discount_amount,
                    '', '', '', '',
                ])

        # 過不足金行
        if guardian and guardian.id not in balance_exported_guardians:
            balance = guardian_balances.get(guardian.id)
            if balance and balance != 0:
                writer.writerow([
                    guardian_no, '', guardian_last_name, '', '',
                    '', '過不足金', '', '過不足金（前月繰越）', '',
                    '', '過不足金', '過不足金（前月繰越）', int(balance),
                    '', '', '', '',
                ])
            balance_exported_guardians.add(guardian.id)

    @extend_schema(summary='引落データCSVエクスポート')
    @action(detail=False, methods=['get'], url_path='export-debit')
    def export_debit(self, request):
        """ConfirmedBillingから引落データをCSV形式でエクスポート"""
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        provider = request.query_params.get('provider', 'jaccs')

        tenant_id = _get_tenant_id(request)

        # クエリセット構築
        queryset = self._build_debit_queryset(
            tenant_id, year, month, start_date, end_date, request.query_params
        )
        if isinstance(queryset, Response):
            return queryset  # エラーレスポンス

        # プロバイダーフィルター
        provider_filter_map = {
            'jaccs': 'jaccs',
            'ufj_factor': 'ufjfactors',
            'chukyo_finance': 'chukyo_finance',
        }
        if provider in provider_filter_map:
            queryset = queryset.filter(guardian__payment_provider=provider_filter_map[provider])

        # 保護者ごとに集計
        guardian_totals = {}
        for billing in queryset:
            guardian_id = billing.guardian_id
            if guardian_id not in guardian_totals:
                guardian_totals[guardian_id] = {
                    'guardian': billing.guardian,
                    'total_amount': 0,
                    'billings': [],
                }
            guardian_totals[guardian_id]['total_amount'] += int(billing.total_amount)
            guardian_totals[guardian_id]['billings'].append(billing)

        # CSVレスポンス作成
        response = HttpResponse(content_type='text/csv; charset=shift_jis')
        filename = f"debit_export_{provider}_{year or start_date}_{month or end_date}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)

        # 対象期間
        target_period = self._get_target_period(year, month, start_date)

        # JACCS委託者コード
        jaccs_consignor_code = self._get_jaccs_consignor_code()

        # データ出力
        for guardian_id, data in guardian_totals.items():
            self._write_debit_row(writer, data, provider, jaccs_consignor_code, target_period)

        return response

    def _build_debit_queryset(self, tenant_id, year, month, start_date, end_date, query_params):
        """引落データクエリセットを構築"""
        queryset = ConfirmedBilling.objects.filter(
            tenant_id=tenant_id,
            deleted_at__isnull=True,
            total_amount__gt=0,
        ).select_related('student', 'guardian')

        if year and month:
            queryset = queryset.filter(year=int(year), month=int(month))
        elif start_date and end_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')

                year_months = []
                current = start_dt.replace(day=1)
                while current <= end_dt:
                    year_months.append((current.year, current.month))
                    if current.month == 12:
                        current = current.replace(year=current.year + 1, month=1)
                    else:
                        current = current.replace(month=current.month + 1)

                from django.db.models import Q
                q_filter = Q()
                for y, m in year_months:
                    q_filter |= Q(year=y, month=m)
                queryset = queryset.filter(q_filter)
            except ValueError:
                raise ValidationException('日付形式が不正です（YYYY-MM-DD）')
        else:
            raise ValidationException('期間を指定してください（year, month または start_date, end_date）')

        payment_method = query_params.get('payment_method')
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)

        return queryset

    def _get_target_period(self, year, month, start_date):
        """対象期間文字列を取得"""
        if year and month:
            return f"{year}{int(month):02d}"
        elif start_date:
            try:
                dt = datetime.strptime(start_date, '%Y-%m-%d')
                return f"{dt.year}{dt.month:02d}"
            except Exception:
                pass
        return timezone.now().strftime('%Y%m')

    def _get_jaccs_consignor_code(self):
        """JACCS委託者コードを取得"""
        jaccs_consignor_code = '490508'
        try:
            jaccs_provider = PaymentProvider.objects.filter(code='jaccs').first()
            if jaccs_provider and jaccs_provider.consignor_code:
                jaccs_consignor_code = jaccs_provider.consignor_code
        except Exception:
            pass
        return jaccs_consignor_code

    def _write_debit_row(self, writer, data, provider, jaccs_consignor_code, target_period):
        """引落データ行を書き込み"""
        guardian = data['guardian']
        if not guardian:
            return

        if not guardian.bank_code or not guardian.bank_account_number:
            return

        amount = data['total_amount']
        if amount <= 0:
            return

        if provider == 'jaccs':
            writer.writerow([
                '2',
                jaccs_consignor_code,
                guardian.guardian_no or '',
                guardian.bank_code or '',
                guardian.bank_branch_code or '',
                '1',  # 口座種別（普通）
                guardian.bank_account_number or '',
                guardian.full_name_kana or guardian.full_name or '',
                amount,
                '',
            ])
        elif provider == 'ufj_factor':
            writer.writerow([
                '2',
                '91',
                '0',
                guardian.bank_code or '',
                guardian.bank_branch_code or '',
                '',
                '1',
                guardian.bank_account_number or '',
                guardian.full_name_kana or '',
                amount,
                '0',
                target_period,
            ])
