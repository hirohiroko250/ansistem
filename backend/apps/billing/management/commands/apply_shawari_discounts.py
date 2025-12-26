"""
社割を2月請求に適用するコマンド

Usage:
    python manage.py apply_shawari_discounts --dry-run
    python manage.py apply_shawari_discounts
"""
import json
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.billing.models import ConfirmedBilling
from apps.students.models import Student


class Command(BaseCommand):
    help = '社割を2月請求に適用'

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

        # 社割データ読み込み
        with open('/app/shawari_discounts.json', 'r', encoding='utf-8') as f:
            shawari_data = json.load(f)

        self.stdout.write(f'社割対象生徒: {len(shawari_data)}名')

        # 生徒マッピング作成 (old_id -> Student)
        student_map = {}
        for s in Student.objects.only('id', 'old_id').all():
            if s.old_id:
                student_map[s.old_id] = s

        # 対象月の請求を取得
        billings = ConfirmedBilling.objects.filter(year=year, month=month)
        self.stdout.write(f'{year}年{month}月請求: {billings.count()}件')

        updated_count = 0
        skipped_no_billing = 0
        skipped_zero = 0
        total_discount = Decimal('0')

        for old_id_str, discounts in shawari_data.items():
            old_id = old_id_str  # キーはすでに文字列

            # 合計割引額を計算（負の値）
            discount_amount = sum(Decimal(str(d['amount'])) for d in discounts)

            # 0円の場合はスキップ
            if discount_amount == 0:
                skipped_zero += 1
                continue

            # 生徒を取得
            student = student_map.get(old_id)
            if not student:
                self.stdout.write(f'  警告: 生徒 old_id={old_id} が見つかりません')
                continue

            # 請求を取得
            billing = billings.filter(student=student).first()
            if not billing:
                skipped_no_billing += 1
                continue

            # 割引を適用
            # discounts_snapshot に追加
            existing_discounts = billing.discounts_snapshot or []

            # 既存の社割があれば削除
            existing_discounts = [d for d in existing_discounts if '社割' not in d.get('name', '')]

            # 新しい社割を追加（各割引項目を個別に追加）
            for d in discounts:
                if d['amount'] != 0:
                    existing_discounts.append({
                        'name': d['category'],
                        'amount': float(d['amount']),  # 負の値
                        'type': 'shawari',
                    })

            if dry_run:
                self.stdout.write(
                    f'  [ドライラン] {student.full_name}: 社割 {discount_amount}円 -> 合計 {billing.total_amount + discount_amount}円'
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
            total_discount += discount_amount

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
適用件数: {updated_count}件
スキップ（請求なし）: {skipped_no_billing}件
スキップ（0円）: {skipped_zero}件
割引合計: {total_discount}円
'''))
