"""
過去のStudentItemからConfirmedBillingを作成するスクリプト

StudentItemのデータをConfirmedBillingにコピーして、請求タブに表示されるようにする
時系列を守るため、confirmed_atは各月の25日に設定
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.billing.models import ConfirmedBilling
from apps.contracts.models import StudentItem
from apps.students.models import Student
from apps.tenants.models import Tenant


def get_tenant():
    tenant = Tenant.objects.first()
    if not tenant:
        print("テナントが見つかりません")
        sys.exit(1)
    return tenant


def create_confirmed_billings(target_months=None, dry_run=True):
    """StudentItemからConfirmedBillingを作成"""
    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name}")
    print(f"モード: {'ドライラン' if dry_run else '実行'}")

    # 対象月を取得
    if target_months is None:
        # デフォルト: 2024-04 から 2025-03 まで
        target_months = []
        for year in [2024, 2025]:
            start_month = 4 if year == 2024 else 1
            end_month = 12 if year == 2024 else 3
            for month in range(start_month, end_month + 1):
                target_months.append(f"{year}-{month:02d}")

    print(f"対象月: {target_months}")

    # 既存のConfirmedBillingを取得
    existing = set()
    for cb in ConfirmedBilling.objects.filter(tenant_id=tenant.id):
        key = f"{cb.student_id}_{cb.year}_{cb.month}"
        existing.add(key)
    print(f"既存ConfirmedBilling: {len(existing)}件")

    stats = {
        'created': 0,
        'skipped_exists': 0,
        'skipped_no_guardian': 0,
        'errors': []
    }

    with transaction.atomic():
        for billing_month in target_months:
            year = int(billing_month.split('-')[0])
            month = int(billing_month.split('-')[1])
            print(f"\n処理中: {year}年{month}月")

            # この月のStudentItemを生徒ごとに集計
            student_items = StudentItem.objects.filter(
                tenant_id=tenant.id,
                billing_month=billing_month
            ).exclude(
                student__isnull=True
            ).select_related('student', 'student__guardian', 'product', 'brand')

            # 生徒ごとにグループ化
            student_data = {}
            for item in student_items:
                student_id = str(item.student_id)
                if student_id not in student_data:
                    student_data[student_id] = {
                        'student': item.student,
                        'items': [],
                        'subtotal': Decimal('0'),
                        'discount_total': Decimal('0'),
                    }
                student_data[student_id]['items'].append(item)
                student_data[student_id]['subtotal'] += item.unit_price or Decimal('0')
                student_data[student_id]['discount_total'] += item.discount_amount or Decimal('0')

            print(f"  対象生徒数: {len(student_data)}")

            for student_id, data in student_data.items():
                student = data['student']
                guardian = student.guardian

                if not guardian:
                    stats['skipped_no_guardian'] += 1
                    continue

                # 既存チェック
                key = f"{student_id}_{year}_{month}"
                if key in existing:
                    stats['skipped_exists'] += 1
                    continue

                # 明細スナップショットを作成
                items_snapshot = []
                for item in data['items']:
                    item_data = {
                        'id': str(item.id),
                        'old_id': item.old_id or '',
                        'product_name': item.product.product_name if item.product else None,
                        'brand_name': item.brand.brand_name if item.brand else None,
                        'quantity': item.quantity,
                        'unit_price': str(item.unit_price or 0),
                        'discount_amount': str(item.discount_amount or 0),
                        'final_price': str(item.final_price or 0),
                        'notes': item.notes or '',
                    }
                    items_snapshot.append(item_data)

                total_amount = data['subtotal'] - data['discount_total']

                # 確定日時を月の15日に設定（時系列を守る）
                confirmed_at = timezone.make_aware(
                    datetime(year, month, 15, 10, 0, 0)
                )

                # ConfirmedBillingを作成
                confirmed = ConfirmedBilling(
                    tenant_id=tenant.id,
                    student=student,
                    guardian=guardian,
                    year=year,
                    month=month,
                    subtotal=data['subtotal'],
                    discount_total=data['discount_total'],
                    tax_amount=Decimal('0'),
                    total_amount=total_amount,
                    paid_amount=Decimal('0'),
                    balance=total_amount,
                    items_snapshot=items_snapshot,
                    discounts_snapshot=[],
                    status=ConfirmedBilling.Status.UNPAID,
                    payment_method=ConfirmedBilling.PaymentMethod.DIRECT_DEBIT,
                )

                if not dry_run:
                    confirmed.save()
                    # confirmed_atを手動で更新（auto_now_addを上書き）
                    ConfirmedBilling.objects.filter(id=confirmed.id).update(confirmed_at=confirmed_at)

                existing.add(key)
                stats['created'] += 1

        if dry_run:
            print("\n=== ドライラン結果 ===")
            transaction.set_rollback(True)
        else:
            print("\n=== 実行結果 ===")

    print(f"作成: {stats['created']}件")
    print(f"スキップ（既存）: {stats['skipped_exists']}件")
    print(f"スキップ（保護者なし）: {stats['skipped_no_guardian']}件")
    print(f"エラー: {len(stats['errors'])}件")

    # 最終状態
    if not dry_run:
        total = ConfirmedBilling.objects.filter(tenant_id=tenant.id).count()
        print(f"\n=== 最終状態 ===")
        print(f"ConfirmedBilling総数: {total:,}件")

    return stats


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='StudentItemからConfirmedBillingを作成')
    parser.add_argument('--months', nargs='+', help='対象月（例: 2024-04 2024-05）')
    parser.add_argument('--execute', action='store_true', help='実際に作成を実行')
    args = parser.parse_args()

    if args.execute:
        print("実際の作成を実行します...")
        create_confirmed_billings(target_months=args.months, dry_run=False)
    else:
        print("ドライランモード（--execute で実行）")
        create_confirmed_billings(target_months=args.months, dry_run=True)
