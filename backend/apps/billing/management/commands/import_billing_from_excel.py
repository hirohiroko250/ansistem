"""
請求合計結果Excelからitems_snapshotを更新するマネジメントコマンド

Usage:
    # ドライラン
    python manage.py import_billing_from_excel --excel /path/to/file.xlsx --dry-run

    # 実行
    python manage.py import_billing_from_excel --excel /path/to/file.xlsx --year 2025 --month 1
"""
import pandas as pd
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.billing.models import ConfirmedBilling
from apps.students.models import Student


class Command(BaseCommand):
    help = '請求合計結果Excelからitems_snapshotを更新'

    def add_arguments(self, parser):
        parser.add_argument(
            '--excel',
            type=str,
            required=True,
            help='請求合計結果Excelファイルのパス'
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
        parser.add_argument(
            '--update-subtotal',
            action='store_true',
            help='subtotalも更新する'
        )

    def handle(self, *args, **options):
        excel_path = options['excel']
        dry_run = options['dry_run']
        year = options['year']
        month = options['month']
        update_subtotal = options.get('update_subtotal', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ==='))

        # Excelを読み込む
        self.stdout.write(f'Excelファイルを読み込み中: {excel_path}')
        df = pd.read_excel(excel_path, sheet_name=0)
        self.stdout.write(f'読み込み件数: {len(df)}行')

        # 生徒IDでグループ化
        billing_data = {}
        for _, row in df.iterrows():
            student_id = row.get('生徒ID')
            if pd.isna(student_id):
                continue
            student_id = int(student_id)

            if student_id not in billing_data:
                billing_data[student_id] = {
                    'guardian_id': row.get('保護者ID'),
                    'student_name': row.get('生徒名'),
                    'items': [],
                    'total': Decimal('0'),
                }

            # 削除フラグがあるものはスキップ
            if row.get('削除フラッグ') == 1:
                continue

            amount = row.get('月額料金', 0)
            if pd.isna(amount):
                amount = 0
            amount = Decimal(str(amount))

            item = {
                'contract_id': str(row.get('契約ID', '')),
                'product_code': str(row.get('請求ID', '')),
                'brand_name': str(row.get('ブランド名', '')),
                'course_name': str(row.get('契約名', '')),
                'item_type_display': str(row.get('請求カテゴリ名', '')),
                'product_name': str(row.get('顧客表示用(契約T3の「ブランド別請求カテゴリ」', '')),
                'unit_price': float(amount),
                'quantity': 1,
                'subtotal': float(amount),
            }

            # item_typeを設定
            category = str(row.get('請求カテゴリ名', ''))
            if '授業料' in category:
                item['item_type'] = 'tuition'
            elif '月会費' in category:
                item['item_type'] = 'monthly_fee'
            elif '設備費' in category:
                item['item_type'] = 'facility'
            elif '教材' in category:
                item['item_type'] = 'textbook'
            elif '入会' in category:
                item['item_type'] = 'enrollment'
            elif '講習' in category:
                item['item_type'] = 'seminar'
            else:
                item['item_type'] = 'other'

            billing_data[student_id]['items'].append(item)
            billing_data[student_id]['total'] += amount

        self.stdout.write(f'生徒数: {len(billing_data)}件')

        # 生徒のold_idマッピングを作成
        student_map = {}
        for student in Student.objects.all():
            if student.old_id:
                try:
                    old_id_int = int(student.old_id)
                    student_map[old_id_int] = student
                except ValueError:
                    pass

        # ConfirmedBillingを更新
        queryset = ConfirmedBilling.objects.filter(year=year, month=month)
        total_count = queryset.count()
        updated_count = 0
        skipped_count = 0
        not_found_count = 0

        self.stdout.write(f'対象ConfirmedBilling: {total_count}件')

        for billing in queryset:
            # 生徒のold_idから請求データを検索
            student = billing.student
            if not student or not student.old_id:
                skipped_count += 1
                continue

            try:
                student_old_id = int(student.old_id)
            except ValueError:
                skipped_count += 1
                continue

            if student_old_id not in billing_data:
                not_found_count += 1
                continue

            data = billing_data[student_old_id]
            items = data['items']
            new_total = data['total']

            if not items:
                skipped_count += 1
                continue

            if dry_run:
                self.stdout.write(
                    f'  [ドライラン] {billing.billing_no}: {len(billing.items_snapshot or [])}行 → {len(items)}行, '
                    f'subtotal: {billing.subtotal} → {new_total}'
                )
            else:
                with transaction.atomic():
                    billing.items_snapshot = items
                    fields_to_update = ['items_snapshot']

                    if update_subtotal:
                        billing.subtotal = new_total
                        billing.total_amount = new_total - billing.discount_total
                        billing.balance = billing.total_amount - billing.paid_amount
                        fields_to_update.extend(['subtotal', 'total_amount', 'balance'])

                    billing.save(update_fields=fields_to_update)

                self.stdout.write(self.style.SUCCESS(f'  更新: {billing.billing_no}'))

            updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
対象件数: {total_count}件
更新件数: {updated_count}件
スキップ: {skipped_count}件
未発見: {not_found_count}件
'''))
