"""
過不足金データのインポートコマンド

CSVファイルから過不足金データを読み込み、請求確定データに反映する。
"""
import csv
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.billing.models import ConfirmedBilling
from apps.students.models import Guardian


class Command(BaseCommand):
    help = '過不足金CSVをインポートして請求確定データに反映する'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='インポートするCSVファイルのパス',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には変更せず、処理対象の確認のみ行う',
        )
        parser.add_argument(
            '--tenant-id',
            type=str,
            help='テナントID（指定しない場合は最初のテナントを使用）',
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']
        tenant_id = options.get('tenant_id')

        self.stdout.write('='*70)
        self.stdout.write('過不足金インポート')
        self.stdout.write('='*70)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN モード: 実際の変更は行いません'))

        # テナントIDの取得
        if not tenant_id:
            from apps.tenants.models import Tenant
            tenant = Tenant.objects.filter(is_active=True).first()
            if tenant:
                tenant_id = str(tenant.id)
            else:
                self.stdout.write(self.style.ERROR('アクティブなテナントが見つかりません'))
                return

        self.stdout.write(f'テナントID: {tenant_id}')
        self.stdout.write(f'CSVファイル: {csv_file}')
        self.stdout.write('-'*70)

        # 統計
        stats = {
            'total': 0,
            'january': 0,
            'february': 0,
            'matched': 0,
            'not_found_guardian': 0,
            'not_found_billing': 0,
            'updated': 0,
            'errors': 0,
        }

        results = {
            'january': [],
            'february': [],
            'not_found': [],
        }

        # CSVを読み込み（BOM付きUTF-8に対応）
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for row in reader:
                stats['total'] += 1

                guardian_old_id = row['保護者ID'].strip()
                last_name = row['姓'].strip()
                first_name = row['名'].strip()
                adjustment_str = row['過不足金'].strip()
                billing_date = row['請求日'].strip()
                note = row['保護者様明細表示用'].strip()
                remarks = row['備考'].strip()

                # 金額をパース
                try:
                    adjustment_amount = Decimal(adjustment_str)
                except (InvalidOperation, ValueError):
                    self.stdout.write(self.style.ERROR(
                        f'金額パースエラー: {guardian_old_id} {last_name}{first_name} - {adjustment_str}'
                    ))
                    stats['errors'] += 1
                    continue

                # 請求月を判定
                if billing_date == '2026/1/1':
                    year, month = 2026, 1
                    stats['january'] += 1
                elif billing_date == '2026/2/1':
                    year, month = 2026, 2
                    stats['february'] += 1
                else:
                    self.stdout.write(self.style.WARNING(
                        f'不明な請求日: {guardian_old_id} {last_name}{first_name} - {billing_date}'
                    ))
                    stats['errors'] += 1
                    continue

                # 保護者を検索
                guardian = Guardian.objects.filter(
                    tenant_id=tenant_id,
                    old_id=guardian_old_id,
                    deleted_at__isnull=True
                ).first()

                if not guardian:
                    stats['not_found_guardian'] += 1
                    results['not_found'].append({
                        'type': 'guardian',
                        'old_id': guardian_old_id,
                        'name': f'{last_name}{first_name}',
                        'amount': adjustment_amount,
                        'month': month,
                    })
                    continue

                # 請求確定データを検索（保護者でグループ化されているので、該当月の最初のレコードを取得）
                billing = ConfirmedBilling.objects.filter(
                    tenant_id=tenant_id,
                    guardian=guardian,
                    year=year,
                    month=month
                ).first()

                if not billing:
                    stats['not_found_billing'] += 1
                    results['not_found'].append({
                        'type': 'billing',
                        'old_id': guardian_old_id,
                        'name': f'{last_name}{first_name}',
                        'guardian_id': str(guardian.id),
                        'amount': adjustment_amount,
                        'month': month,
                    })
                    continue

                stats['matched'] += 1

                # 更新処理
                if not dry_run:
                    with transaction.atomic():
                        # 過不足金を設定
                        billing.adjustment_amount = adjustment_amount
                        billing.adjustment_note = note if note else remarks

                        # 合計金額を再計算（過不足金を含める）
                        # total_amount = subtotal - discount_total + tax_amount + adjustment_amount
                        new_total = (
                            billing.subtotal -
                            billing.discount_total +
                            billing.tax_amount +
                            adjustment_amount +
                            billing.carry_over_amount
                        )
                        billing.total_amount = new_total
                        billing.balance = new_total - billing.paid_amount

                        billing.save()
                        stats['updated'] += 1

                # 結果を記録
                result_entry = {
                    'old_id': guardian_old_id,
                    'name': f'{last_name}{first_name}',
                    'guardian_id': str(guardian.id),
                    'billing_id': str(billing.id),
                    'student_name': billing.student.full_name if billing.student else '-',
                    'adjustment': adjustment_amount,
                    'old_total': billing.total_amount,
                    'note': note[:30] if note else (remarks[:30] if remarks else '-'),
                }

                if month == 1:
                    results['january'].append(result_entry)
                else:
                    results['february'].append(result_entry)

        # 結果サマリー
        self.stdout.write('')
        self.stdout.write('='*70)
        self.stdout.write('処理結果サマリー')
        self.stdout.write('='*70)
        self.stdout.write(f"総レコード数: {stats['total']}")
        self.stdout.write(f"  1月分: {stats['january']}")
        self.stdout.write(f"  2月分: {stats['february']}")
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f"マッチ成功: {stats['matched']}"))
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"更新完了: {stats['updated']}"))
        self.stdout.write(self.style.WARNING(f"保護者未発見: {stats['not_found_guardian']}"))
        self.stdout.write(self.style.WARNING(f"請求データ未発見: {stats['not_found_billing']}"))
        self.stdout.write(self.style.ERROR(f"エラー: {stats['errors']}"))

        # サンプル表示
        if results['january']:
            self.stdout.write('')
            self.stdout.write('-'*70)
            self.stdout.write('1月分サンプル（最初の10件）:')
            for r in results['january'][:10]:
                self.stdout.write(
                    f"  {r['old_id']} {r['name']} - {r['student_name']}: "
                    f"{r['adjustment']:+,}円 | {r['note']}"
                )

        if results['february']:
            self.stdout.write('')
            self.stdout.write('-'*70)
            self.stdout.write('2月分サンプル（最初の10件）:')
            for r in results['february'][:10]:
                self.stdout.write(
                    f"  {r['old_id']} {r['name']} - {r['student_name']}: "
                    f"{r['adjustment']:+,}円 | {r['note']}"
                )

        # 未発見リスト
        if results['not_found']:
            self.stdout.write('')
            self.stdout.write('-'*70)
            self.stdout.write(self.style.WARNING('未発見リスト（最初の20件）:'))
            for r in results['not_found'][:20]:
                self.stdout.write(
                    f"  [{r['type']}] {r['old_id']} {r['name']} - "
                    f"{r['month']}月 {r['amount']:+,}円"
                )

        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('DRY RUNのため、実際の変更は行われていません'))
