"""
T5追加請求CSVをインポートするマネジメントコマンド

- 契約IDあり → ContractにStudentItemとして紐付け
- 契約IDなし → 保護者ID+生徒IDでConfirmedBillingに追加

Usage:
    # ドライラン
    python manage.py import_t5_charges --csv /path/to/t5.csv --year 2025 --month 1 --dry-run

    # 実行
    python manage.py import_t5_charges --csv /path/to/t5.csv --year 2025 --month 1
"""
import csv
import pandas as pd
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.billing.models import ConfirmedBilling
from apps.contracts.models import Contract, StudentItem
from apps.students.models import Student, Guardian
from apps.schools.models import Brand
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = 'T5追加請求CSVをインポート'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            required=True,
            help='T5追加請求CSVファイルのパス'
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
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='ドライラン（実際には変更しない）'
        )
        parser.add_argument(
            '--skip-output',
            type=str,
            default='skipped_t5.csv',
            help='スキップしたデータの出力先CSVファイル'
        )

    def handle(self, *args, **options):
        csv_path = options['csv']
        year = options['year']
        month = options['month']
        dry_run = options['dry_run']
        skip_output = options.get('skip_output', 'skipped_t5.csv')

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ==='))

        # テナント取得
        tenant = Tenant.objects.first()
        if not tenant:
            self.stdout.write(self.style.ERROR('テナントが見つかりません'))
            return

        # マッピング作成
        self.stdout.write('マッピングデータ作成中...')

        # 生徒マッピング (old_id -> Student)
        student_map = {}
        for s in Student.objects.only('id', 'old_id', 'guardian_id', 'primary_school_id').all():
            if s.old_id:
                try:
                    student_map[int(s.old_id)] = s
                except ValueError:
                    pass
        self.stdout.write(f'  生徒: {len(student_map)}件')

        # 保護者マッピング (old_id -> Guardian)
        guardian_map = {}
        for g in Guardian.objects.only('id', 'old_id').all():
            if g.old_id:
                guardian_map[str(g.old_id)] = g
        self.stdout.write(f'  保護者: {len(guardian_map)}件')

        # 契約マッピング (contract_no -> Contract)
        # contract_noは「契約ID_生徒ID」形式
        contract_map = {}
        for c in Contract.objects.only('id', 'contract_no', 'old_id', 'student_id', 'brand_id').all():
            if c.contract_no:
                contract_map[c.contract_no] = c
            if c.old_id:
                contract_map[c.old_id] = c
        self.stdout.write(f'  契約: {len(contract_map)}件')

        # ブランドマッピング
        brand_map = {}
        for b in Brand.objects.all():
            brand_map[b.brand_code] = b
        default_brand = Brand.objects.filter(brand_code='DEFAULT').first() or Brand.objects.first()

        # ConfirmedBillingマッピング (student_id -> billing)
        billing_map = {}
        for b in ConfirmedBilling.objects.filter(year=year, month=month, deleted_at__isnull=True):
            if b.student_id:
                billing_map[b.student_id] = b
        self.stdout.write(f'  請求データ: {len(billing_map)}件')

        # CSV読み込み
        self.stdout.write(f'CSV読み込み: {csv_path}')
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        self.stdout.write(f'  行数: {len(df)}件')

        # 統計
        linked_to_contract = 0
        linked_to_billing = 0
        skipped_no_student = 0
        skipped_no_contract = 0
        skipped_no_billing = 0
        skipped_rows = []

        for _, row in df.iterrows():
            guardian_id = row.get('保護者ID')
            student_id = row.get('生徒ID')
            contract_id = row.get('対象　契約ID')
            amount = row.get('金額', 0)
            category = str(row.get('対象カテゴリー', '') or '')
            display_name = str(row.get('顧客表記用請求名（契約、請求IDの請求は、そのすぐ下に表記）', '') or '')
            brand_name = str(row.get('対象　同ブランド', '') or '')
            start_date_str = str(row.get('開始日', '') or '')

            # 金額チェック
            if pd.isna(amount) or amount == 0:
                continue

            amount = Decimal(str(int(amount)))

            # 生徒ID確認
            if pd.isna(student_id):
                skipped_no_student += 1
                skipped_rows.append({**row.to_dict(), 'skip_reason': '生徒IDなし'})
                continue

            try:
                student_id_int = int(student_id)
            except ValueError:
                skipped_no_student += 1
                skipped_rows.append({**row.to_dict(), 'skip_reason': '生徒ID不正'})
                continue

            student = student_map.get(student_id_int)
            if not student:
                skipped_no_student += 1
                skipped_rows.append({**row.to_dict(), 'skip_reason': '生徒未発見'})
                continue

            # ブランド抽出
            brand = None
            if contract_id and not pd.isna(contract_id) and '_' in str(contract_id):
                prefix = str(contract_id).split('_')[0]
                if prefix.startswith('24') and len(prefix) > 2:
                    brand_code = prefix[2:]
                else:
                    brand_code = prefix
                brand = brand_map.get(brand_code) or brand_map.get(prefix)
            if not brand:
                brand = default_brand

            # 契約IDがある場合 → Contractに紐付け
            if contract_id and not pd.isna(contract_id) and str(contract_id).strip():
                # contract_no形式で検索 (契約ID_生徒ID)
                contract_no = f'{contract_id}_{student_id_int}'
                contract = contract_map.get(contract_no) or contract_map.get(str(contract_id))

                if contract:
                    if dry_run:
                        self.stdout.write(
                            f'  [ドライラン] Contract紐付け: {contract_no} - {display_name} ({amount}円)'
                        )
                    else:
                        # StudentItemを作成
                        StudentItem.objects.create(
                            tenant_id=tenant.id,
                            tenant_ref=tenant,
                            old_id=f't5_{contract_no}_{category}',
                            student=student,
                            contract=contract,
                            brand=brand,
                            start_date=pd.to_datetime(start_date_str).date() if start_date_str and start_date_str != 'nan' else None,
                            billing_month=f'{year}-{month:02d}',
                            quantity=1,
                            unit_price=amount,
                            discount_amount=Decimal('0'),
                            final_price=amount,
                            notes=display_name or category,
                        )
                    linked_to_contract += 1
                else:
                    # 契約が見つからない場合はConfirmedBillingに追加
                    billing = billing_map.get(student.id)
                    if billing:
                        if dry_run:
                            self.stdout.write(
                                f'  [ドライラン] Billing追加(契約なし): {student.full_name} - {display_name} ({amount}円)'
                            )
                        else:
                            self._add_to_billing(billing, row, amount, category, display_name, brand_name)
                        linked_to_billing += 1
                    else:
                        skipped_no_billing += 1
                        skipped_rows.append({**row.to_dict(), 'skip_reason': '請求データなし'})
            else:
                # 契約IDなし → ConfirmedBillingに直接追加
                billing = billing_map.get(student.id)
                if billing:
                    if dry_run:
                        self.stdout.write(
                            f'  [ドライラン] Billing追加: {student.full_name} - {display_name} ({amount}円)'
                        )
                    else:
                        self._add_to_billing(billing, row, amount, category, display_name, brand_name)
                    linked_to_billing += 1
                else:
                    skipped_no_billing += 1
                    skipped_rows.append({**row.to_dict(), 'skip_reason': '請求データなし'})

        # スキップしたデータをCSVに出力
        if skipped_rows and not dry_run:
            with open(skip_output, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=skipped_rows[0].keys())
                writer.writeheader()
                writer.writerows(skipped_rows)
            self.stdout.write(f'スキップデータを {skip_output} に出力しました')

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
Contract紐付け: {linked_to_contract}件
Billing追加: {linked_to_billing}件
スキップ（生徒なし）: {skipped_no_student}件
スキップ（請求なし）: {skipped_no_billing}件
'''))

    def _add_to_billing(self, billing, row, amount, category, display_name, brand_name):
        """ConfirmedBillingのitems_snapshotに追加"""
        items_snapshot = list(billing.items_snapshot or [])

        item = {
            'billing_id': str(row.get('対象　請求ID', '')),
            'product_name': display_name or category,
            'item_type_display': category,
            'item_type': self._get_item_type(category),
            'brand_name': brand_name,
            'unit_price': float(amount),
            'quantity': 1,
            'subtotal': float(amount),
            'source': 'T5',
        }

        # 既に追加済みかチェック
        exists = any(
            i.get('billing_id') == item['billing_id'] and
            i.get('product_name') == item['product_name'] and
            i.get('subtotal') == item['subtotal']
            for i in items_snapshot
        )

        if not exists:
            items_snapshot.append(item)

            # 合計金額を再計算
            subtotal = sum(Decimal(str(i.get('subtotal', 0) or i.get('unit_price', 0) or 0))
                           for i in items_snapshot)
            discount_total = sum(Decimal(str(d.get('amount', 0)))
                                 for d in (billing.discounts_snapshot or []))
            total_amount = subtotal - discount_total
            balance = total_amount - billing.paid_amount

            with transaction.atomic():
                billing.items_snapshot = items_snapshot
                billing.subtotal = subtotal
                billing.total_amount = total_amount
                billing.balance = balance
                billing.save(update_fields=['items_snapshot', 'subtotal', 'total_amount', 'balance'])

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
        elif '割引' in category:
            return 'discount'
        else:
            return 'other'
