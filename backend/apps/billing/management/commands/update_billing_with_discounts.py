"""
ConfirmedBillingに割引とT5追加請求を反映するマネジメントコマンド

割引ソース:
1. AC_5 Excelの生徒IDなし・マイナス金額行（家族割、FS割引等）
2. T5追加請求CSV

Usage:
    # ドライラン
    python manage.py update_billing_with_discounts --ac5 /path/to/ac5.xlsx --t5 /path/to/t5.csv --year 2025 --month 1 --dry-run

    # 実行
    python manage.py update_billing_with_discounts --ac5 /path/to/ac5.xlsx --t5 /path/to/t5.csv --year 2025 --month 1
"""
import pandas as pd
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.billing.models import ConfirmedBilling
from apps.students.models import Student, Guardian


class Command(BaseCommand):
    help = 'ConfirmedBillingに割引とT5追加請求を反映'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ac5',
            type=str,
            help='AC_5 請求合計結果Excelファイルのパス（割引取得用）'
        )
        parser.add_argument(
            '--t5',
            type=str,
            help='T5 追加請求CSVファイルのパス'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='ドライラン（実際には変更しない）'
        )
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

    def handle(self, *args, **options):
        ac5_path = options.get('ac5')
        t5_path = options.get('t5')
        dry_run = options['dry_run']
        year = options['year']
        month = options['month']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ==='))

        # 保護者old_idマッピング
        guardian_map = {}
        for g in Guardian.objects.only('id', 'old_id').all():
            if g.old_id:
                guardian_map[str(g.old_id)] = g

        # 生徒old_idマッピング
        student_map = {}
        for s in Student.objects.only('id', 'old_id', 'guardian_id').all():
            if s.old_id:
                try:
                    student_map[int(s.old_id)] = s
                except ValueError:
                    pass

        # 保護者IDごとの割引データを収集
        guardian_discounts = {}  # guardian_old_id -> list of discounts

        # AC_5から割引を取得（生徒IDなし・マイナス金額行）
        if ac5_path:
            self.stdout.write(f'AC_5ファイル読み込み: {ac5_path}')
            df_ac5 = pd.read_excel(ac5_path, sheet_name=0)

            # 削除フラグがないマイナス金額行
            discount_rows = df_ac5[
                (df_ac5['月額料金'] < 0) &
                (df_ac5['削除フラッグ'] != 1)
            ]

            self.stdout.write(f'割引行数: {len(discount_rows)}件')

            for _, row in discount_rows.iterrows():
                guardian_id = row.get('保護者ID')
                if pd.isna(guardian_id):
                    continue
                guardian_id = str(int(guardian_id))

                amount = row.get('月額料金', 0)
                if pd.isna(amount):
                    continue
                amount = abs(Decimal(str(int(amount))))  # 絶対値に変換

                category = str(row.get('請求カテゴリ名', '') or '')
                display_name = str(row.get('顧客表示用(契約T3の「ブランド別請求カテゴリ」', '') or '')

                discount_item = {
                    'discount_name': display_name or category or '割引',
                    'discount_type': self._get_discount_type(category, display_name),
                    'amount': float(amount),
                    'notes': category,
                }

                if guardian_id not in guardian_discounts:
                    guardian_discounts[guardian_id] = []
                guardian_discounts[guardian_id].append(discount_item)

            self.stdout.write(f'保護者割引: {len(guardian_discounts)}件の保護者')

        # T5追加請求を取得
        t5_items = {}  # (guardian_old_id, student_old_id) -> list of items
        if t5_path:
            self.stdout.write(f'T5ファイル読み込み: {t5_path}')
            df_t5 = pd.read_csv(t5_path, encoding='utf-8-sig')

            # 対象月のデータをフィルタ
            # 開始日がYYYY/MM/01形式
            target_start = f'{year}/{month:02d}/01'
            target_prefix = f'{year}/{month:02d}'

            for _, row in df_t5.iterrows():
                # 有無フラグが1のもののみ
                if row.get('有無') != 1:
                    continue

                start_date = str(row.get('開始日', ''))
                if not start_date.startswith(target_prefix):
                    continue

                guardian_id = row.get('保護者ID')
                student_id = row.get('生徒ID')

                if pd.isna(guardian_id):
                    continue

                guardian_id = str(int(guardian_id))
                student_id = int(student_id) if not pd.isna(student_id) else None

                amount = row.get('金額', 0)
                if pd.isna(amount):
                    continue
                amount = Decimal(str(int(amount)))

                category = str(row.get('請求カテゴリー', '') or row.get('対象カテゴリー', '') or '')
                display_name = str(row.get('顧客表記用請求名（契約、請求IDの請求は、そのすぐ下に表記）', '') or '')
                brand_name = str(row.get('対象　同ブランド', '') or '')

                item = {
                    'billing_id': str(row.get('請求ID', '')),
                    'product_name': display_name,
                    'item_type_display': category,
                    'item_type': self._get_item_type(category),
                    'brand_name': brand_name,
                    'unit_price': float(amount),
                    'quantity': 1,
                    'subtotal': float(amount),
                }

                key = (guardian_id, student_id)
                if key not in t5_items:
                    t5_items[key] = []
                t5_items[key].append(item)

            self.stdout.write(f'T5追加請求: {len(t5_items)}件の生徒/保護者')

        # ConfirmedBillingを更新
        billings = ConfirmedBilling.objects.filter(
            year=year, month=month, deleted_at__isnull=True
        )
        total_count = billings.count()
        updated_count = 0
        discount_added_count = 0
        t5_added_count = 0

        self.stdout.write(f'対象ConfirmedBilling: {total_count}件')

        for billing in billings:
            # 保護者old_idを取得
            guardian = billing.guardian
            if not guardian:
                continue

            guardian_old_id = str(guardian.old_id) if guardian.old_id else None
            if not guardian_old_id:
                continue

            # 生徒old_idを取得
            student = billing.student
            student_old_id = None
            if student and student.old_id:
                try:
                    student_old_id = int(student.old_id)
                except ValueError:
                    pass

            items_snapshot = list(billing.items_snapshot or [])
            discounts_snapshot = list(billing.discounts_snapshot or [])
            changed = False

            # 割引を追加
            if guardian_old_id in guardian_discounts:
                for discount in guardian_discounts[guardian_old_id]:
                    # 既に追加済みかチェック
                    exists = any(
                        d.get('discount_name') == discount['discount_name'] and
                        d.get('amount') == discount['amount']
                        for d in discounts_snapshot
                    )
                    if not exists:
                        discounts_snapshot.append(discount)
                        changed = True
                        discount_added_count += 1

            # T5追加請求を追加
            key = (guardian_old_id, student_old_id)
            if key in t5_items:
                for item in t5_items[key]:
                    # 既に追加済みかチェック
                    exists = any(
                        i.get('billing_id') == item['billing_id']
                        for i in items_snapshot
                        if i.get('billing_id')
                    )
                    if not exists:
                        items_snapshot.append(item)
                        changed = True
                        t5_added_count += 1

            if changed:
                # 合計金額を再計算
                subtotal = sum(Decimal(str(i.get('subtotal', 0) or i.get('unit_price', 0) or 0))
                               for i in items_snapshot)
                discount_total = sum(Decimal(str(d.get('amount', 0)))
                                     for d in discounts_snapshot)
                total_amount = subtotal - discount_total
                balance = total_amount - billing.paid_amount

                if dry_run:
                    student_name = student.full_name if student else '不明'
                    self.stdout.write(
                        f'  [ドライラン] {billing.billing_no} ({student_name}): '
                        f'割引={len(discounts_snapshot)}件, T5={len([i for i in items_snapshot if i.get("billing_id", "").startswith("AB") or i.get("billing_id", "").startswith("NB")])}件, '
                        f'合計: {billing.subtotal} → {subtotal}, 割引合計: {discount_total}'
                    )
                else:
                    with transaction.atomic():
                        billing.items_snapshot = items_snapshot
                        billing.discounts_snapshot = discounts_snapshot
                        billing.subtotal = subtotal
                        billing.discount_total = discount_total
                        billing.total_amount = total_amount
                        billing.balance = balance
                        billing.save(update_fields=[
                            'items_snapshot', 'discounts_snapshot',
                            'subtotal', 'discount_total', 'total_amount', 'balance'
                        ])

                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
対象件数: {total_count}件
更新件数: {updated_count}件
割引追加: {discount_added_count}件
T5追加: {t5_added_count}件
'''))

    def _get_discount_type(self, category, display_name):
        """割引タイプを判定"""
        text = (category + display_name).lower()
        if 'fs' in text or 'フレンド' in text or '紹介' in text:
            return 'friendship'
        elif '家族' in text:
            return 'family'
        elif 'マイル' in text:
            return 'mile'
        elif '特別' in text:
            return 'special'
        else:
            return 'other'

    def _get_item_type(self, category):
        """請求タイプを判定"""
        if '授業料' in category:
            return 'tuition'
        elif '月会費' in category:
            return 'monthly_fee'
        elif '設備費' in category:
            return 'facility'
        elif '教材' in category:
            return 'textbook'
        elif '入会' in category:
            return 'enrollment'
        elif '講習' in category:
            return 'seminar'
        else:
            return 'other'
