"""
保護者レベルの割引（FS割引・家族割）を2月請求に適用するコマンド

Usage:
    python manage.py apply_guardian_discounts --dry-run
    python manage.py apply_guardian_discounts
"""
import json
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.billing.models import ConfirmedBilling
from apps.students.models import Student, Guardian


class Command(BaseCommand):
    help = '保護者レベルの割引を2月請求に適用'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='ドライラン（実際には変更しない）'
        )
        parser.add_argument(
            '--year',
            type=int,
            default=2026,
            help='対象年'
        )
        parser.add_argument(
            '--month',
            type=int,
            default=2,
            help='対象月'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        year = options['year']
        month = options['month']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ==='))

        # 保護者レベル割引データ読み込み
        with open('/app/guardian_discounts.json', 'r', encoding='utf-8') as f:
            guardian_data = json.load(f)

        self.stdout.write(f'保護者レベル割引対象: {len(guardian_data)}名')

        # 保護者マッピング作成 (old_id -> Guardian)
        guardian_map = {}
        for g in Guardian.objects.only('id', 'old_id').all():
            if g.old_id:
                guardian_map[g.old_id] = g

        # 対象月の請求を取得
        billings = ConfirmedBilling.objects.filter(year=year, month=month).select_related('student', 'guardian')
        self.stdout.write(f'{year}年{month}月請求: {billings.count()}件')

        updated_count = 0
        skipped_no_guardian = 0
        skipped_no_billing = 0
        total_fs_discount = Decimal('0')
        total_kazoku_discount = Decimal('0')

        for old_id_str, data in guardian_data.items():
            guardian_name = data['name']
            discounts = data['discounts']

            # 保護者を取得
            guardian = guardian_map.get(old_id_str)
            if not guardian:
                skipped_no_guardian += 1
                continue

            # この保護者の生徒の請求を取得（最初の1件）
            guardian_billings = billings.filter(guardian=guardian)
            if not guardian_billings.exists():
                skipped_no_billing += 1
                continue

            # 最初の請求に割引を適用
            billing = guardian_billings.first()

            # 割引を適用
            existing_discounts = billing.discounts_snapshot or []

            # 既存のFS割引と家族割を削除
            existing_discounts = [
                d for d in existing_discounts
                if d.get('type') not in ('fs_discount', 'kazoku_discount')
            ]

            # 新しい割引を追加
            for d in discounts:
                if d['amount'] != 0:
                    existing_discounts.append({
                        'name': d['category'],
                        'amount': float(d['amount']),
                        'type': d['type'],
                    })
                    if d['type'] == 'fs_discount':
                        total_fs_discount += Decimal(str(d['amount']))
                    elif d['type'] == 'kazoku_discount':
                        total_kazoku_discount += Decimal(str(d['amount']))

            if dry_run:
                discount_amount = sum(Decimal(str(d['amount'])) for d in discounts)
                self.stdout.write(
                    f'  [ドライラン] {guardian_name} -> {billing.student.full_name}: 割引 {discount_amount}円'
                )
            else:
                with transaction.atomic():
                    billing.discounts_snapshot = existing_discounts
                    # discount_total を再計算（すべての割引の合計、負の値）
                    billing.discount_total = sum(
                        Decimal(str(d.get('amount', 0))) for d in existing_discounts
                    )
                    # total_amount を再計算
                    billing.total_amount = billing.subtotal + billing.discount_total
                    billing.save(update_fields=['discounts_snapshot', 'discount_total', 'total_amount'])

            updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
適用件数: {updated_count}件
スキップ（保護者なし）: {skipped_no_guardian}件
スキップ（請求なし）: {skipped_no_billing}件
FS割引合計: {total_fs_discount}円
家族割合計: {total_kazoku_discount}円
'''))
