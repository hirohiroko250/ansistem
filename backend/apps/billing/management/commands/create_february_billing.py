"""
1月請求データをコピーして2月請求を作成し、T5追加請求を反映するコマンド

ロジック:
- 12月新規契約 → 12月分 + 1月分 + 2月分を請求
- 1月新規契約 → 1月分 + 2月分を請求
- 既存契約 → 2月分のみ（1月と同じ）

Usage:
    # ドライラン
    python manage.py create_february_billing --t5 /path/to/t5.csv --dry-run

    # 実行
    python manage.py create_february_billing --t5 /path/to/t5.csv
"""
import pandas as pd
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.billing.models import ConfirmedBilling
from apps.students.models import Student, Guardian


class Command(BaseCommand):
    help = '1月請求をコピーして2月請求を作成し、T5追加請求を反映'

    def add_arguments(self, parser):
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
            '--clear-existing',
            action='store_true',
            help='既存の2月データを削除してから作成'
        )

    def handle(self, *args, **options):
        t5_path = options.get('t5')
        dry_run = options['dry_run']
        clear_existing = options.get('clear_existing', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ==='))

        # 既存の2月データを削除
        if clear_existing and not dry_run:
            deleted = ConfirmedBilling.objects.filter(year=2025, month=2).delete()[0]
            self.stdout.write(f'既存の2月データを{deleted}件削除しました')

        # 保護者・生徒のold_idマッピング
        guardian_map = {}
        for g in Guardian.objects.only('id', 'old_id').all():
            if g.old_id:
                guardian_map[str(g.old_id)] = g

        student_map = {}
        for s in Student.objects.only('id', 'old_id', 'guardian_id').all():
            if s.old_id:
                try:
                    student_map[int(s.old_id)] = s
                except ValueError:
                    pass

        # T5追加請求を読み込み
        t5_items = {}  # (guardian_old_id, student_old_id) -> list of items
        if t5_path:
            self.stdout.write(f'T5ファイル読み込み: {t5_path}')
            df_t5 = pd.read_csv(t5_path, encoding='utf-8-sig')

            for _, row in df_t5.iterrows():
                # 有無フラグが1のもののみ
                if row.get('有無') != 1:
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

                # 開始日から請求月数を判定
                start_date = str(row.get('開始日', ''))
                months_to_charge = 1  # デフォルト1ヶ月分

                if '2025/12' in start_date or '2025-12' in start_date:
                    # 12月新規 → 3ヶ月分（12月+1月+2月）
                    months_to_charge = 3
                elif '2026/01' in start_date or '2026-01' in start_date or '2025/01' in start_date or '2025-01' in start_date:
                    # 1月新規 → 2ヶ月分（1月+2月）
                    months_to_charge = 2

                category = str(row.get('対象カテゴリー', '') or '')
                display_name = str(row.get('顧客表記用請求名（契約、請求IDの請求は、そのすぐ下に表記）', '') or '')
                brand_name = str(row.get('対象　同ブランド', '') or '')
                billing_id = str(row.get('請求ID', ''))

                # 金額を月数で乗算
                total_amount = amount * months_to_charge

                item = {
                    'billing_id': billing_id,
                    'product_name': display_name,
                    'item_type_display': category,
                    'item_type': self._get_item_type(category),
                    'brand_name': brand_name,
                    'unit_price': float(amount),
                    'quantity': months_to_charge,
                    'subtotal': float(total_amount),
                    'months_charged': months_to_charge,
                    'start_date': start_date,
                    'notes': f'{months_to_charge}ヶ月分' if months_to_charge > 1 else '',
                }

                key = (guardian_id, student_id)
                if key not in t5_items:
                    t5_items[key] = []
                t5_items[key].append(item)

            self.stdout.write(f'T5追加請求: {len(t5_items)}件の生徒/保護者, 合計{sum(len(v) for v in t5_items.values())}アイテム')

        # 1月請求データを取得
        jan_billings = ConfirmedBilling.objects.filter(
            year=2025, month=1, deleted_at__isnull=True
        )
        total_jan = jan_billings.count()
        self.stdout.write(f'1月請求データ: {total_jan}件')

        created_count = 0
        t5_added_count = 0
        skipped_count = 0

        for jan_billing in jan_billings:
            # 既存チェック
            existing = ConfirmedBilling.objects.filter(
                student=jan_billing.student,
                year=2025,
                month=2
            ).first()

            if existing and not clear_existing:
                skipped_count += 1
                continue

            # 保護者・生徒のold_id取得
            guardian = jan_billing.guardian
            student = jan_billing.student
            guardian_old_id = str(guardian.old_id) if guardian and guardian.old_id else None
            student_old_id = None
            if student and student.old_id:
                try:
                    student_old_id = int(student.old_id)
                except ValueError:
                    pass

            # 2月用のitems_snapshotを作成（1月と同じ）
            items_snapshot = list(jan_billing.items_snapshot or [])
            discounts_snapshot = list(jan_billing.discounts_snapshot or [])

            # T5追加請求を追加
            t5_added_for_student = 0
            if guardian_old_id:
                key = (guardian_old_id, student_old_id)
                if key in t5_items:
                    for item in t5_items[key]:
                        items_snapshot.append(item)
                        t5_added_for_student += 1
                        t5_added_count += 1

            # 合計金額を計算
            subtotal = sum(Decimal(str(i.get('subtotal', 0) or i.get('unit_price', 0) or 0))
                           for i in items_snapshot)
            discount_total = sum(Decimal(str(d.get('amount', 0)))
                                 for d in discounts_snapshot)
            total_amount = subtotal - discount_total

            # 請求番号生成
            billing_no = f'CB202502-{created_count + 1:04d}'

            if dry_run:
                student_name = student.full_name if student else '不明'
                self.stdout.write(
                    f'  [ドライラン] {billing_no}: {student_name} '
                    f'(基本: {len(jan_billing.items_snapshot or [])}件, T5追加: {t5_added_for_student}件, '
                    f'小計: {subtotal}, 割引: {discount_total}, 請求額: {total_amount})'
                )
            else:
                with transaction.atomic():
                    ConfirmedBilling.objects.create(
                        tenant_id=jan_billing.tenant_id,
                        tenant_ref=jan_billing.tenant_ref,
                        billing_no=billing_no,
                        student=student,
                        guardian=guardian,
                        year=2025,
                        month=2,
                        subtotal=subtotal,
                        discount_total=discount_total,
                        tax_amount=Decimal('0'),
                        total_amount=total_amount,
                        paid_amount=Decimal('0'),
                        balance=total_amount,
                        items_snapshot=items_snapshot,
                        discounts_snapshot=discounts_snapshot,
                        status='confirmed',
                        payment_method=jan_billing.payment_method,
                        confirmed_at=timezone.now(),
                        notes='',
                    )

            created_count += 1

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
1月請求: {total_jan}件
2月請求作成: {created_count}件
T5追加: {t5_added_count}件
スキップ: {skipped_count}件
'''))

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
        elif '管理費' in category:
            return 'management_fee'
        elif '講習' in category:
            return 'seminar'
        else:
            return 'other'
