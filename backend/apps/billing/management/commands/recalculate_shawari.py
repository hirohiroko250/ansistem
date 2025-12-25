"""
社割を全授業料の50%に再計算するマネジメントコマンド
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.billing.models import ConfirmedBilling
from apps.contracts.models import StudentDiscount


class Command(BaseCommand):
    help = '社割を全授業料の50%に再計算'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            required=True,
            help='対象年'
        )
        parser.add_argument(
            '--month',
            type=int,
            required=True,
            help='対象月'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='ドライラン（実際には変更しない）'
        )

    def handle(self, *args, **options):
        year = options['year']
        month = options['month']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ==='))

        # 対象の請求を取得
        billings = ConfirmedBilling.objects.filter(
            year=year, month=month, deleted_at__isnull=True
        ).select_related('student', 'guardian')

        self.stdout.write(f'対象請求: {billings.count()}件')

        updated_count = 0
        shawari_count = 0

        for billing in billings:
            items_snapshot = billing.items_snapshot or []
            discounts_snapshot = billing.discounts_snapshot or []

            # 社割があるかチェック
            has_shawari = any(
                '社割' in (d.get('discount_name', '') or '')
                for d in discounts_snapshot
            )

            if not has_shawari:
                continue  # 社割がない場合はスキップ

            # 各授業料アイテムの割引Maxを取得して社割を計算
            from apps.contracts.models import Product
            tuition_types = ['tuition', 'TUITION']
            shawari_total = Decimal('0')
            shawari_details = []

            for item in items_snapshot:
                if item.get('item_type') not in tuition_types:
                    continue
                # 社割のマイナス行は除外
                product_name = item.get('product_name', '') or ''
                if '社割' in product_name:
                    continue

                amount = Decimal(str(item.get('final_price', 0) or item.get('subtotal', 0) or item.get('unit_price', 0)))
                if amount <= 0:
                    continue

                # 商品の割引Maxを取得
                product_code = item.get('product_code', '')
                discount_max = Decimal('50')  # デフォルト50%

                if product_code:
                    product = Product.objects.filter(product_code=product_code).first()
                    if product and product.discount_max is not None:
                        # discount_max=0の場合は割引なし
                        discount_max = min(Decimal('50'), Decimal(str(product.discount_max)))

                # 割引額を計算
                item_discount = amount * discount_max / Decimal('100')
                shawari_total += item_discount
                if discount_max != Decimal('50'):
                    shawari_details.append(f'{product_code}:{discount_max}%')

            # 社割を再計算
            new_discounts = []
            shawari_applied = False
            new_discount_total = Decimal('0')

            for discount in discounts_snapshot:
                discount_name = discount.get('discount_name', '') or ''

                if '社割' in discount_name:
                    if shawari_applied:
                        continue  # 複数の社割は1回のみ適用

                    if shawari_total > 0:
                        shawari_applied = True
                        new_discount = {
                            'id': discount.get('id', ''),
                            'old_id': discount.get('old_id', ''),
                            'discount_name': discount_name,
                            'amount': str(shawari_total),
                            'discount_unit': 'yen',
                        }
                        new_discounts.append(new_discount)
                        new_discount_total += shawari_total
                        detail_str = f' ({", ".join(shawari_details)})' if shawari_details else ''
                        self.stdout.write(
                            f'  {billing.student.full_name if billing.student else "?"}: '
                            f'社割={shawari_total}円{detail_str}'
                        )
                        shawari_count += 1
                else:
                    # 社割以外はそのまま
                    amount = Decimal(str(discount.get('amount', 0)))
                    new_discounts.append(discount)
                    new_discount_total += amount

            # 合計再計算
            subtotal = Decimal(str(billing.subtotal))
            total_amount = subtotal - new_discount_total
            if total_amount < 0:
                total_amount = Decimal('0')
            balance = total_amount - Decimal(str(billing.paid_amount or 0))

            if dry_run:
                self.stdout.write(
                    f'  [ドライラン] 更新予定: 割引合計 {billing.discount_total} → {new_discount_total}'
                )
            else:
                with transaction.atomic():
                    billing.discounts_snapshot = new_discounts
                    billing.discount_total = new_discount_total
                    billing.total_amount = total_amount
                    billing.balance = balance
                    billing.save(update_fields=[
                        'discounts_snapshot', 'discount_total', 'total_amount', 'balance'
                    ])

            updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
更新した請求: {updated_count}件
社割再計算: {shawari_count}件
'''))
