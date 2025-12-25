"""
既存のConfirmedBillingのitems_snapshotを
新しいStudentItemデータ（授業料/月会費/設備費分離）で展開するマネジメントコマンド

旧items_snapshot: 1行（合計金額）
  ↓
新items_snapshot: 3行（授業料/月会費/設備費）

Usage:
    # ドライラン（変更しない）
    python manage.py expand_items_snapshot --dry-run

    # 特定の年月に適用
    python manage.py expand_items_snapshot --year 2025 --month 1

    # 実行
    python manage.py expand_items_snapshot
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.billing.models import ConfirmedBilling
from apps.contracts.models import StudentItem


class Command(BaseCommand):
    help = '既存のConfirmedBillingのitems_snapshotをStudentItemデータで展開'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='ドライラン（実際には変更しない）'
        )
        parser.add_argument(
            '--year',
            type=int,
            help='対象年（指定しない場合は全て）'
        )
        parser.add_argument(
            '--month',
            type=int,
            help='対象月（指定しない場合は全て）'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='既に展開済みでも強制的に再展開'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        year = options.get('year')
        month = options.get('month')
        force = options.get('force', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ==='))

        # StudentItemをold_idでキャッシュ
        self.stdout.write('StudentItemデータを読み込み中...')
        student_items_map = {}
        for si in StudentItem.objects.select_related(
            'product', 'product__brand', 'course', 'brand', 'contract'
        ).all():
            if si.old_id:
                # old_idからベースIDを抽出 (UC0000000075_2 -> UC0000000075)
                base_id = si.old_id.split('_')[0] if '_' in si.old_id and si.old_id.count('_') > 0 else si.old_id
                # ベースIDの最初の部分がUCで始まるかチェック
                if base_id.startswith('UC'):
                    if base_id not in student_items_map:
                        student_items_map[base_id] = []
                    student_items_map[base_id].append(si)
                else:
                    # 24AEC_1000067 形式の場合はそのままキーにする
                    full_id = si.old_id
                    base_key = '_'.join(full_id.split('_')[:2]) if full_id.count('_') >= 2 else full_id
                    if base_key not in student_items_map:
                        student_items_map[base_key] = []
                    student_items_map[base_key].append(si)

        self.stdout.write(f'StudentItem: {len(student_items_map)}件のベースIDをキャッシュ')

        # 対象のConfirmedBillingを取得
        queryset = ConfirmedBilling.objects.all()

        if year:
            queryset = queryset.filter(year=year)
        if month:
            queryset = queryset.filter(month=month)

        total_count = queryset.count()
        updated_count = 0
        skipped_count = 0
        expanded_count = 0

        self.stdout.write(f'対象件数: {total_count}件')

        for billing in queryset:
            try:
                result = self.expand_snapshot(billing, student_items_map, dry_run, force)
                if result['expanded']:
                    expanded_count += 1
                    updated_count += 1
                elif result['updated']:
                    updated_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'エラー: {billing.billing_no} - {e}')
                )
                import traceback
                traceback.print_exc()

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
対象件数: {total_count}件
更新件数: {updated_count}件
展開件数: {expanded_count}件
スキップ: {skipped_count}件
'''))

    def expand_snapshot(self, billing, student_items_map, dry_run, force) -> dict:
        """items_snapshotをStudentItemデータで展開"""
        items_snapshot = billing.items_snapshot or []
        result = {'updated': False, 'expanded': False}

        if not items_snapshot:
            return result

        # 既に展開済みかチェック（同じold_idが複数ある場合は展開済み）
        old_ids = [item.get('old_id', '') for item in items_snapshot if item.get('old_id')]
        base_old_ids = set()
        for old_id in old_ids:
            if old_id.startswith('UC'):
                base_id = old_id.split('_')[0] if '_' in old_id else old_id
            else:
                base_id = '_'.join(old_id.split('_')[:2]) if old_id.count('_') >= 2 else old_id
            base_old_ids.add(base_id)

        # 同じbase_idで複数アイテムがある = 既に展開済み
        if not force:
            old_id_counts = {}
            for old_id in old_ids:
                if old_id.startswith('UC'):
                    base_id = old_id.split('_')[0] if '_' in old_id else old_id
                else:
                    base_id = '_'.join(old_id.split('_')[:2]) if old_id.count('_') >= 2 else old_id
                old_id_counts[base_id] = old_id_counts.get(base_id, 0) + 1

            if any(count > 1 for count in old_id_counts.values()):
                # 既に展開済み
                return result

        new_items = []

        for item in items_snapshot:
            old_id = item.get('old_id', '')

            if not old_id:
                new_items.append(item)
                continue

            # ベースIDを抽出
            if old_id.startswith('UC'):
                base_id = old_id.split('_')[0] if '_' in old_id else old_id
            else:
                base_id = '_'.join(old_id.split('_')[:2]) if old_id.count('_') >= 2 else old_id

            # StudentItemを検索
            student_items = student_items_map.get(base_id, [])

            if not student_items:
                # StudentItemがなければ元のアイテムをそのまま使用
                new_items.append(item)
                continue

            # StudentItemから複数行を生成
            # 請求月に応じた金額をProductから取得
            billing_month = billing.month

            for si in student_items:
                # 請求月に応じた金額を取得
                if si.product:
                    unit_price = si.product.get_price_for_billing_month(billing_month)
                else:
                    unit_price = si.unit_price

                new_item = {
                    'id': str(si.id),
                    'student_item_id': str(si.id),
                    'old_id': si.old_id,
                    'product_id': str(si.product.id) if si.product else '',
                    'product_code': si.product.product_code if si.product else '',
                    'product_name': si.product.product_name if si.product else '',
                    'product_name_short': si.product.product_name_short if si.product else '',
                    'item_type': si.product.item_type if si.product else 'other',
                    'item_type_display': si.product.get_item_type_display() if si.product and si.product.item_type else 'その他',
                    'brand_name': (si.brand.brand_name if si.brand else
                                   (si.product.brand.brand_name if si.product and si.product.brand else '')),
                    'course_name': si.course.course_name if si.course else '',
                    'contract_no': si.contract.contract_no if si.contract else '',
                    'contract_id': str(si.contract.id) if si.contract else '',
                    'quantity': si.quantity,
                    'unit_price': float(unit_price),
                    'discount_amount': 0,
                    'subtotal': float(unit_price * si.quantity),
                    'billing_month': f'{billing.year}-{billing.month:02d}',
                    'notes': item.get('notes', ''),
                }
                new_items.append(new_item)

            result['expanded'] = True
            self.stdout.write(
                f'  展開: {billing.billing_no} - {base_id} ({len(student_items)}行)'
            )

        if not result['expanded']:
            return result

        result['updated'] = True

        # 合計金額を再計算
        new_subtotal = sum(Decimal(str(item.get('subtotal', 0))) for item in new_items)

        if dry_run:
            self.stdout.write(
                f'  [ドライラン] {billing.billing_no}: {len(items_snapshot)}行 → {len(new_items)}行, 小計: {billing.subtotal} → {new_subtotal}'
            )
        else:
            with transaction.atomic():
                billing.items_snapshot = new_items
                # 小計は変更しない（元の合計金額を維持）
                billing.save(update_fields=['items_snapshot'])
            self.stdout.write(self.style.SUCCESS(f'  更新完了: {billing.billing_no}'))

        return result
