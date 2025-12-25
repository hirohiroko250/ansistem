"""
請求合計結果ExcelからConfirmedBillingを新規作成するマネジメントコマンド

Usage:
    # ドライラン
    python manage.py create_confirmed_billing --excel /path/to/file.xlsx --year 2025 --month 1 --dry-run

    # 実行
    python manage.py create_confirmed_billing --excel /path/to/file.xlsx --year 2025 --month 1
"""
import pandas as pd
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.billing.models import ConfirmedBilling
from apps.students.models import Student, Guardian
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = '請求合計結果ExcelからConfirmedBillingを新規作成'

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
            '--clear-existing',
            action='store_true',
            help='既存データを削除してから作成'
        )

    def handle(self, *args, **options):
        excel_path = options['excel']
        dry_run = options['dry_run']
        year = options['year']
        month = options['month']
        clear_existing = options.get('clear_existing', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ==='))

        # テナント取得
        tenant = Tenant.objects.first()
        if not tenant:
            self.stdout.write(self.style.ERROR('テナントが見つかりません'))
            return

        # 既存データの削除
        if clear_existing and not dry_run:
            deleted_count = ConfirmedBilling.objects.filter(
                year=year, month=month
            ).delete()[0]
            self.stdout.write(f'既存データを{deleted_count}件削除しました')

        # Excelを読み込む
        self.stdout.write(f'Excelファイルを読み込み中: {excel_path}')
        df = pd.read_excel(excel_path, sheet_name=0)
        self.stdout.write(f'読み込み件数: {len(df)}行')

        # 生徒IDでグループ化
        billing_data = {}
        for _, row in df.iterrows():
            student_id = row.get('生徒ID')
            guardian_id = row.get('保護者ID')

            if pd.isna(student_id):
                continue
            student_id = int(student_id)

            if student_id not in billing_data:
                billing_data[student_id] = {
                    'guardian_old_id': str(int(guardian_id)) if not pd.isna(guardian_id) else None,
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
            amount = Decimal(str(int(amount)))

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

        # 生徒と保護者のold_idマッピングを作成
        student_map = {}
        for student in Student.objects.only('id', 'old_id', 'guardian_id', 'first_name', 'last_name').all():
            if student.old_id:
                try:
                    old_id_int = int(student.old_id)
                    student_map[old_id_int] = student
                except ValueError:
                    pass

        guardian_map = {}
        for guardian in Guardian.objects.only('id', 'old_id').all():
            if guardian.old_id:
                guardian_map[str(guardian.old_id)] = guardian

        # ConfirmedBillingを作成
        created_count = 0
        skipped_count = 0
        not_found_students = []
        not_found_guardians = []

        for old_student_id, data in billing_data.items():
            student = student_map.get(old_student_id)
            if not student:
                not_found_students.append(old_student_id)
                skipped_count += 1
                continue

            # 保護者を取得（生徒のguardian_idから検索、なければold_idで検索）
            guardian = None
            if student.guardian_id:
                guardian = Guardian.objects.filter(id=student.guardian_id).only('id').first()
            if not guardian and data['guardian_old_id']:
                guardian = guardian_map.get(data['guardian_old_id'])

            if not guardian:
                not_found_guardians.append(data['guardian_old_id'])
                skipped_count += 1
                continue

            items = data['items']
            total = data['total']

            # 既存チェック
            existing = ConfirmedBilling.objects.filter(
                student=student,
                year=year,
                month=month
            ).first()

            if existing and not clear_existing:
                self.stdout.write(f'  スキップ（既存）: {student.full_name}')
                skipped_count += 1
                continue

            # 請求番号生成
            billing_no = f'CB{year}{month:02d}-{created_count + 1:04d}'

            if dry_run:
                self.stdout.write(
                    f'  [ドライラン] {billing_no}: {student.full_name} '
                    f'({len(items)}件, 合計: {total}円)'
                )
            else:
                with transaction.atomic():
                    billing = ConfirmedBilling.objects.create(
                        tenant_id=tenant.id,
                        tenant_ref=tenant,
                        billing_no=billing_no,
                        student=student,
                        guardian=guardian,
                        year=year,
                        month=month,
                        subtotal=total,
                        discount_total=Decimal('0'),
                        tax_amount=Decimal('0'),
                        total_amount=total,
                        paid_amount=Decimal('0'),
                        balance=total,
                        items_snapshot=items,
                        discounts_snapshot=[],
                        status='confirmed',
                        payment_method='direct_debit',
                        confirmed_at=timezone.now(),
                        notes='',
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  作成: {billing_no} - {student.full_name} '
                            f'({len(items)}件, 合計: {total}円)'
                        )
                    )

            created_count += 1

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
作成件数: {created_count}件
スキップ: {skipped_count}件
生徒未発見: {len(not_found_students)}件
保護者未発見: {len(not_found_guardians)}件
'''))

        if not_found_students and len(not_found_students) <= 20:
            self.stdout.write(f'未発見の生徒ID: {not_found_students[:20]}')
        if not_found_guardians and len(not_found_guardians) <= 20:
            self.stdout.write(f'未発見の保護者ID: {not_found_guardians[:20]}')
