"""
Billing Actions Mixin - 請求サマリー関連アクション
"""
import json
import logging
from decimal import Decimal

from rest_framework.decorators import action
from rest_framework.response import Response


class BillingActionsMixin:
    """請求サマリー関連アクション"""

    @action(detail=True, methods=['get'])
    def billing_summary(self, request, pk=None):
        """保護者の請求サマリー（全子供の料金・割引含む）"""
        from apps.contracts.models import StudentItem, StudentDiscount
        from apps.billing.models import Invoice, Payment, ConfirmedBilling

        guardian = self.get_object()

        # 支払い状態の確認（滞納があるか）
        overdue_invoices = 0
        unpaid_amount = 0
        payment_method = 'direct_debit'
        payment_method_display = '口座引落'
        account_balance = 0  # 残高（プラス=不足、マイナス=過払い）
        invoice_history = []  # 請求履歴
        payment_history = []  # 入金履歴

        try:
            # ConfirmedBillingから請求・残高を計算（新システム）
            confirmed_billings = ConfirmedBilling.objects.filter(
                guardian=guardian
            ).order_by('-year', '-month')

            # 未入金のConfirmedBillingをカウント
            unpaid_confirmed = confirmed_billings.filter(
                status__in=[ConfirmedBilling.Status.CONFIRMED, ConfirmedBilling.Status.UNPAID, ConfirmedBilling.Status.PARTIAL]
            )
            unpaid_amount_confirmed = sum(cb.balance or 0 for cb in unpaid_confirmed)

            # ConfirmedBillingから請求履歴と残高を計算
            total_billed_confirmed = Decimal('0')
            total_paid_confirmed = Decimal('0')

            for cb in confirmed_billings[:24]:  # 直近2年分
                billed = cb.total_amount or Decimal('0')
                paid = cb.paid_amount or Decimal('0')
                total_billed_confirmed += billed
                total_paid_confirmed += paid

                # 請求履歴を収集
                status_display_map = {
                    'confirmed': '確定',
                    'unpaid': '未入金',
                    'partial': '一部入金',
                    'paid': '入金済',
                    'cancelled': '取消',
                }
                invoice_history.append({
                    'id': str(cb.id),
                    'invoiceNo': f'CB-{cb.year}{cb.month:02d}',
                    'billingYear': cb.year,
                    'billingMonth': cb.month,
                    'billingLabel': f"{cb.year}年{cb.month}月",
                    'totalAmount': int(billed),
                    'paidAmount': int(paid),
                    'balanceDue': int(cb.balance or 0),
                    'status': cb.status,
                    'statusDisplay': status_display_map.get(cb.status, cb.status),
                    'paymentMethod': cb.payment_method or 'direct_debit',
                    'paidAt': cb.paid_at.isoformat() if cb.paid_at else None,
                    'dueDate': None,
                    'issuedAt': cb.confirmed_at.isoformat() if cb.confirmed_at else None,
                    'source': 'confirmed_billing',
                })

            # Invoiceからも取得（旧システム）
            all_invoices = Invoice.objects.filter(guardian=guardian).order_by('-billing_year', '-billing_month')
            total_billed_invoice = Decimal('0')
            total_paid_invoice = Decimal('0')

            for inv in all_invoices[:24]:  # 直近2年分
                billed = inv.total_amount or Decimal('0')
                paid = inv.paid_amount or Decimal('0')
                total_billed_invoice += billed
                total_paid_invoice += paid

                # 重複チェック（同じ年月がConfirmedBillingになければ追加）
                existing = [h for h in invoice_history if h['billingYear'] == inv.billing_year and h['billingMonth'] == inv.billing_month and h['source'] == 'confirmed_billing']
                if not existing:
                    invoice_history.append({
                        'id': str(inv.id),
                        'invoiceNo': inv.invoice_no or '',
                        'billingYear': inv.billing_year,
                        'billingMonth': inv.billing_month,
                        'billingLabel': f"{inv.billing_year}年{inv.billing_month}月",
                        'totalAmount': int(billed),
                        'paidAmount': int(paid),
                        'balanceDue': int(inv.balance_due or 0),
                        'status': inv.status,
                        'statusDisplay': inv.get_status_display() if hasattr(inv, 'get_status_display') else inv.status,
                        'paymentMethod': inv.payment_method or 'direct_debit',
                        'paidAt': inv.paid_at.isoformat() if hasattr(inv, 'paid_at') and inv.paid_at else None,
                        'dueDate': inv.due_date.isoformat() if inv.due_date else None,
                        'issuedAt': inv.issued_at.isoformat() if hasattr(inv, 'issued_at') and inv.issued_at else None,
                        'source': 'invoice',
                    })

            overdue_invoices = Invoice.objects.filter(
                guardian=guardian,
                status='overdue'
            ).count()

            # 最新の請求書から支払い方法を取得
            latest_invoice = Invoice.objects.filter(
                guardian=guardian
            ).order_by('-billing_year', '-billing_month').first()

            if latest_invoice:
                payment_method = latest_invoice.payment_method
                payment_method_display = latest_invoice.get_payment_method_display()

            # 残高計算: ConfirmedBillingがあればそちらを優先
            if confirmed_billings.exists():
                account_balance = int(total_billed_confirmed - total_paid_confirmed)
                unpaid_amount = int(unpaid_amount_confirmed)
            else:
                account_balance = int(total_billed_invoice - total_paid_invoice)
                unpaid_invoices = Invoice.objects.filter(
                    guardian=guardian,
                    status__in=['issued', 'partial']
                )
                unpaid_amount = sum(inv.balance_due or 0 for inv in unpaid_invoices)

            # 請求履歴をソート
            invoice_history.sort(key=lambda x: (x['billingYear'], x['billingMonth']), reverse=True)

            # 入金履歴を取得（Paymentモデルから）
            payments = Payment.objects.filter(
                guardian=guardian
            ).order_by('-payment_date', '-created_at')[:20]

            for pmt in payments:
                payment_history.append({
                    'id': str(pmt.id),
                    'paymentDate': pmt.payment_date.isoformat() if pmt.payment_date else None,
                    'amount': int(pmt.amount or 0),
                    'paymentMethod': pmt.method if hasattr(pmt, 'method') else (pmt.payment_method or ''),
                    'paymentMethodDisplay': pmt.get_method_display() if hasattr(pmt, 'get_method_display') else (pmt.get_payment_method_display() if hasattr(pmt, 'get_payment_method_display') else pmt.method),
                    'status': pmt.status if hasattr(pmt, 'status') else 'completed',
                    'notes': pmt.notes or '',
                })

        except Exception as e:
            # テーブルが存在しない場合などはスキップ
            logging.warning(f"billing_summary error: {e}")

        # 子供一覧
        children = guardian.children.filter(deleted_at__isnull=True).select_related('grade', 'primary_school', 'primary_brand')

        # 子供ごとの料金明細を取得
        children_billing = []
        total_amount = Decimal('0')
        total_discount = Decimal('0')

        # 曜日変換
        day_of_week_map = {
            1: '月', 2: '火', 3: '水', 4: '木', 5: '金', 6: '土', 7: '日'
        }

        # 最新の請求確定データから請求月を取得
        try:
            latest_confirmed = confirmed_billings.first() if confirmed_billings.exists() else None
        except NameError:
            latest_confirmed = None
        if latest_confirmed:
            billing_year = latest_confirmed.year
            billing_month = latest_confirmed.month
        else:
            # ConfirmedBillingがない場合は今日の日付から計算
            from datetime import date as date_cls
            today = date_cls.today()
            billing_year = today.year
            billing_month = today.month
            if today.day > 10:
                billing_month += 1
                if billing_month > 12:
                    billing_month = 1
                    billing_year += 1

        for child in children:
            child_data = self._build_child_billing_data(
                child, billing_year, billing_month, day_of_week_map,
                StudentItem, StudentDiscount
            )
            children_billing.append(child_data['billing'])
            total_amount += child_data['total']
            total_discount += child_data['discount']

        # 保護者レベルの割引（兄弟割引など）
        guardian_discount_list, guardian_discount_total = self._get_guardian_discounts(
            guardian, StudentDiscount
        )
        total_discount += guardian_discount_total

        # FS割引（友達紹介割引）
        fs_discount_list = self._get_fs_discounts(guardian)

        # マイル情報
        mile_info = self._get_mile_info(guardian)

        # 口座種別の日本語変換
        account_type_map = {
            'ordinary': '普通',
            'current': '当座',
            'savings': '貯蓄',
        }

        return Response({
            'guardianId': str(guardian.id),
            'guardianName': f"{guardian.last_name}{guardian.first_name}",
            # 請求月情報
            'billingYear': billing_year,
            'billingMonth': billing_month,
            'billingLabel': f"{billing_year}年{billing_month}月分",
            'children': children_billing,
            'guardianDiscounts': guardian_discount_list,
            'fsDiscounts': fs_discount_list,
            'mileInfo': mile_info,
            'totalAmount': int(total_amount),
            'totalDiscount': int(total_discount),
            'netAmount': int(total_amount - total_discount),
            # 支払い状態
            'paymentMethod': payment_method,
            'paymentMethodDisplay': payment_method_display,
            'isOverdue': overdue_invoices > 0,
            'overdueCount': overdue_invoices,
            'unpaidAmount': int(unpaid_amount),
            # 残高情報（プラス=不足、マイナス=過払い）
            'accountBalance': account_balance,
            'accountBalanceLabel': '過払い' if account_balance < 0 else '不足' if account_balance > 0 else '精算済',
            # 請求・入金履歴
            'invoiceHistory': invoice_history,
            'paymentHistory': payment_history,
            # 銀行口座情報
            'bankAccount': {
                'bankName': guardian.bank_name or '',
                'bankCode': guardian.bank_code or '',
                'branchName': guardian.branch_name or '',
                'branchCode': guardian.branch_code or '',
                'accountType': guardian.account_type or 'ordinary',
                'accountTypeDisplay': account_type_map.get(guardian.account_type, '普通'),
                'accountNumber': guardian.account_number or '',
                'accountHolder': guardian.account_holder or '',
                'accountHolderKana': guardian.account_holder_kana or '',
                'isRegistered': guardian.payment_registered,
                'withdrawalDay': guardian.withdrawal_day,
            },
        })

    def _build_child_billing_data(self, child, billing_year, billing_month, day_of_week_map, StudentItem, StudentDiscount):
        """子供の請求データを構築"""
        from apps.billing.models import ConfirmedBilling as CB

        child_name = f"{child.last_name} {child.first_name}"

        # ConfirmedBillingから最新請求月のデータを取得
        child_confirmed = CB.objects.filter(
            student=child,
            year=billing_year,
            month=billing_month,
            deleted_at__isnull=True
        ).first()

        child_items = []
        child_total = Decimal('0')
        enrollments = []  # 在籍情報（ブランド・曜日・時間）

        if child_confirmed and child_confirmed.items_snapshot:
            # ConfirmedBillingのスナップショットからアイテムを取得
            items_data = child_confirmed.items_snapshot
            if isinstance(items_data, str):
                items_data = json.loads(items_data)

            for item in items_data:
                unit_price = Decimal(str(item.get('unit_price', 0) or 0))
                discount_amount = Decimal(str(item.get('discount_amount', 0) or 0))
                final_price = Decimal(str(item.get('final_price', 0) or 0))
                child_total += final_price

                child_items.append({
                    'id': item.get('product_id', '') or item.get('id', ''),
                    'productName': item.get('product_name', ''),
                    'brandName': item.get('brand_name', ''),
                    'brandCode': '',
                    'schoolName': '',
                    'billingMonth': f"{billing_year}-{billing_month:02d}",
                    'unitPrice': int(unit_price),
                    'discountAmount': int(discount_amount),
                    'finalPrice': int(final_price),
                    'dayOfWeek': None,
                    'dayDisplay': '',
                    'startTime': '',
                    'className': '',
                })

                # 在籍情報を集約（授業料アイテムのみ）
                item_type = item.get('item_type', '')
                brand_name = item.get('brand_name', '')
                if item_type in ['tuition', 'TUITION'] and brand_name:
                    enrollment_key = f"{brand_name}"
                    if enrollment_key not in [e.get('key') for e in enrollments]:
                        enrollments.append({
                            'key': enrollment_key,
                            'brandName': brand_name,
                            'brandCode': '',
                            'dayOfWeek': None,
                            'dayDisplay': '',
                            'startTime': '',
                            'className': '',
                            'schoolName': '',
                        })
        else:
            # ConfirmedBillingがない場合はStudentItemから取得（フォールバック）
            items = StudentItem.objects.filter(
                student=child,
                deleted_at__isnull=True
            ).select_related('product', 'product__brand', 'contract', 'contract__school', 'class_schedule')

            for item in items:
                unit_price = item.unit_price or Decimal('0')
                discount_amount = item.discount_amount or Decimal('0')
                final_price = item.final_price or (unit_price - discount_amount)
                child_total += final_price

                # スケジュール情報
                day_display = day_of_week_map.get(item.day_of_week, '') if item.day_of_week else ''
                time_display = item.start_time.strftime('%H:%M') if item.start_time else ''
                class_name = item.class_schedule.class_name if item.class_schedule else ''

                child_items.append({
                    'id': str(item.id),
                    'productName': item.product.product_name if item.product else '',
                    'brandName': item.product.brand.brand_name if item.product and item.product.brand else '',
                    'brandCode': item.product.brand.brand_code if item.product and item.product.brand else '',
                    'schoolName': item.contract.school.school_name if item.contract and item.contract.school else '',
                    'billingMonth': item.billing_month,
                    'unitPrice': int(unit_price),
                    'discountAmount': int(discount_amount),
                    'finalPrice': int(final_price),
                    # スケジュール情報
                    'dayOfWeek': item.day_of_week,
                    'dayDisplay': day_display,
                    'startTime': time_display,
                    'className': class_name,
                })

                # 在籍情報を集約（月謝アイテムのみ）
                if item.product and item.product.item_type == 'monthly' and item.day_of_week:
                    brand_name = item.product.brand.brand_name if item.product.brand else ''
                    enrollment_key = f"{brand_name}_{item.day_of_week}_{time_display}"
                    if enrollment_key not in [e.get('key') for e in enrollments]:
                        enrollments.append({
                            'key': enrollment_key,
                            'brandName': brand_name,
                            'brandCode': item.product.brand.brand_code if item.product.brand else '',
                            'dayOfWeek': item.day_of_week,
                            'dayDisplay': day_display,
                            'startTime': time_display,
                            'className': class_name,
                            'schoolName': item.contract.school.school_name if item.contract and item.contract.school else '',
                        })

        # 生徒割引
        child_discounts = StudentDiscount.objects.filter(
            student=child,
            deleted_at__isnull=True,
            is_active=True
        ).select_related('brand')

        discount_list = []
        child_discount_total = Decimal('0')
        for disc in child_discounts:
            amount = disc.amount or Decimal('0')
            child_discount_total += abs(amount)
            discount_list.append({
                'id': str(disc.id),
                'discountName': disc.discount_name,
                'amount': int(amount),
                'discountUnit': disc.discount_unit,
                'brandName': disc.brand.brand_name if disc.brand else '',
                'startDate': disc.start_date.isoformat() if disc.start_date else None,
                'endDate': disc.end_date.isoformat() if disc.end_date else None,
            })

        return {
            'billing': {
                'studentId': str(child.id),
                'studentName': child_name,
                'studentNo': child.student_no,
                'status': child.status,
                'gradeText': child.grade_text or (child.grade.grade_name if child.grade else ''),
                'items': child_items,
                'discounts': discount_list,
                'subtotal': int(child_total),
                'enrollments': enrollments,
            },
            'total': child_total,
            'discount': child_discount_total,
        }

    def _get_guardian_discounts(self, guardian, StudentDiscount):
        """保護者レベルの割引を取得"""
        guardian_discounts = StudentDiscount.objects.filter(
            guardian=guardian,
            student__isnull=True,
            deleted_at__isnull=True,
            is_active=True
        ).select_related('brand')

        discount_list = []
        total_discount = Decimal('0')
        for disc in guardian_discounts:
            amount = disc.amount or Decimal('0')
            total_discount += abs(amount)
            discount_list.append({
                'id': str(disc.id),
                'discountName': disc.discount_name,
                'amount': int(amount),
                'discountUnit': disc.discount_unit,
                'brandName': disc.brand.brand_name if disc.brand else '',
                'startDate': disc.start_date.isoformat() if disc.start_date else None,
                'endDate': disc.end_date.isoformat() if disc.end_date else None,
            })
        return discount_list, total_discount

    def _get_fs_discounts(self, guardian):
        """FS割引（友達紹介割引）を取得"""
        fs_discount_list = []
        try:
            fs_discounts = guardian.fs_discounts.filter(status='active')
            for fs in fs_discounts:
                fs_discount_list.append({
                    'id': str(fs.id),
                    'discountType': fs.discount_type,
                    'discountTypeDisplay': fs.get_discount_type_display(),
                    'discountValue': int(fs.discount_value),
                    'status': fs.status,
                    'validFrom': fs.valid_from.isoformat() if fs.valid_from else None,
                    'validUntil': fs.valid_until.isoformat() if fs.valid_until else None,
                })
        except Exception:
            # テーブルが存在しない場合などはスキップ
            pass
        return fs_discount_list

    def _get_mile_info(self, guardian):
        """マイル情報を取得"""
        mile_info = {
            'balance': 0,
            'canUse': False,
            'potentialDiscount': 0,
            'recentTransactions': [],
        }
        try:
            from apps.billing.models import MileTransaction
            mile_balance = MileTransaction.get_balance(guardian)
            can_use = MileTransaction.can_use_miles(guardian)
            potential_discount = MileTransaction.calculate_discount(mile_balance) if mile_balance >= 4 else Decimal('0')

            # 最近のマイル取引
            recent_miles = MileTransaction.objects.filter(guardian=guardian).order_by('-created_at')[:10]
            recent_transactions = []
            for mt in recent_miles:
                recent_transactions.append({
                    'id': str(mt.id),
                    'type': mt.transaction_type,
                    'typeDisplay': mt.get_transaction_type_display(),
                    'miles': mt.miles,
                    'balanceAfter': mt.balance_after,
                    'discountAmount': int(mt.discount_amount),
                    'earnSource': mt.earn_source,
                    'earnDate': mt.earn_date.isoformat() if mt.earn_date else None,
                    'expireDate': mt.expire_date.isoformat() if mt.expire_date else None,
                    'notes': mt.notes,
                    'createdAt': mt.created_at.isoformat() if mt.created_at else None,
                })

            mile_info = {
                'balance': mile_balance,
                'canUse': can_use,
                'potentialDiscount': int(potential_discount),
                'recentTransactions': recent_transactions,
            }
        except Exception:
            # テーブルが存在しない場合などはスキップ
            pass
        return mile_info
