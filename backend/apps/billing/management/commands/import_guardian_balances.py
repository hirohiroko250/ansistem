"""
過不足金データをGuardianBalanceにインポートするコマンド

CSVファイルから過不足金データを読み込み、GuardianBalanceに反映する。
"""
import csv
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.billing.models import GuardianBalance, OffsetLog
from apps.students.models import Guardian


class Command(BaseCommand):
    help = '過不足金CSVをGuardianBalanceにインポートする'

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
        self.stdout.write('過不足金 → GuardianBalance インポート')
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
            'zero_amount': 0,
            'non_zero': 0,
            'guardian_found': 0,
            'guardian_not_found': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
        }

        # 保護者ごとに集計（同じ保護者が1月と2月で別レコードになっている場合は合算）
        guardian_adjustments = {}

        # CSVを読み込み
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

                # 0円はスキップ
                if adjustment_amount == 0:
                    stats['zero_amount'] += 1
                    continue

                stats['non_zero'] += 1

                # 保護者ごとに集計
                if guardian_old_id not in guardian_adjustments:
                    guardian_adjustments[guardian_old_id] = {
                        'name': f'{last_name}{first_name}',
                        'amount': Decimal('0'),
                        'notes': [],
                    }

                guardian_adjustments[guardian_old_id]['amount'] += adjustment_amount
                if note:
                    guardian_adjustments[guardian_old_id]['notes'].append(f'{billing_date}: {note}')

        self.stdout.write(f'CSV読み込み完了: {stats["total"]}件')
        self.stdout.write(f'  0円: {stats["zero_amount"]}件')
        self.stdout.write(f'  過不足あり: {stats["non_zero"]}件')
        self.stdout.write(f'  ユニーク保護者: {len(guardian_adjustments)}件')
        self.stdout.write('-'*70)

        # 各保護者のGuardianBalanceを更新
        results = []

        for guardian_old_id, data in guardian_adjustments.items():
            # 保護者を検索
            guardian = Guardian.objects.filter(
                tenant_id=tenant_id,
                old_id=guardian_old_id,
                deleted_at__isnull=True
            ).first()

            if not guardian:
                stats['guardian_not_found'] += 1
                results.append({
                    'status': 'not_found',
                    'old_id': guardian_old_id,
                    'name': data['name'],
                    'amount': data['amount'],
                })
                continue

            stats['guardian_found'] += 1

            # GuardianBalanceを取得または作成
            balance_obj, created = GuardianBalance.objects.get_or_create(
                tenant_id=tenant_id,
                guardian=guardian,
                defaults={'balance': Decimal('0')}
            )

            old_balance = balance_obj.balance

            # CSVの過不足金をそのまま使用
            # CSVの過不足金: マイナス=不足金（顧客が払う）、プラス=預り金（顧客に戻す）
            # GuardianBalance: マイナス=不足金（未払い）、プラス=預り金（過払い）
            # 符号はそのまま
            new_balance = data['amount']

            if not dry_run:
                with transaction.atomic():
                    balance_obj.balance = new_balance
                    balance_obj.notes = '\n'.join(data['notes'][:5])  # 最初の5件のみ
                    balance_obj.save()

                    # OffsetLogを記録
                    OffsetLog.objects.create(
                        tenant_id=tenant_id,
                        guardian=guardian,
                        transaction_type=OffsetLog.TransactionType.ADJUSTMENT,
                        amount=new_balance,
                        balance_after=new_balance,
                        reason=f'CSVインポート: {data["notes"][0] if data["notes"] else "過不足金"}',
                    )

            if created:
                stats['created'] += 1
            else:
                stats['updated'] += 1

            results.append({
                'status': 'created' if created else 'updated',
                'old_id': guardian_old_id,
                'name': data['name'],
                'guardian_id': str(guardian.id),
                'old_balance': old_balance,
                'new_balance': new_balance,
                'csv_amount': data['amount'],
            })

        # 結果サマリー
        self.stdout.write('')
        self.stdout.write('='*70)
        self.stdout.write('処理結果サマリー')
        self.stdout.write('='*70)
        self.stdout.write(f"ユニーク保護者（0円以外）: {len(guardian_adjustments)}")
        self.stdout.write(self.style.SUCCESS(f"  保護者発見: {stats['guardian_found']}"))
        self.stdout.write(self.style.WARNING(f"  保護者未発見: {stats['guardian_not_found']}"))
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"  新規作成: {stats['created']}"))
            self.stdout.write(self.style.SUCCESS(f"  更新: {stats['updated']}"))

        # サンプル表示
        updated_results = [r for r in results if r['status'] in ('created', 'updated')]
        if updated_results:
            self.stdout.write('')
            self.stdout.write('-'*70)
            self.stdout.write('更新サンプル（最初の15件）:')
            for r in updated_results[:15]:
                self.stdout.write(
                    f"  {r['old_id']} {r['name']}: CSV {r['csv_amount']:+,.0f}円 → 残高 {r['new_balance']:+,.0f}円"
                )

        # 未発見リスト
        not_found = [r for r in results if r['status'] == 'not_found']
        if not_found:
            self.stdout.write('')
            self.stdout.write('-'*70)
            self.stdout.write(self.style.WARNING(f'保護者未発見（{len(not_found)}件、最初の20件）:'))
            for r in not_found[:20]:
                self.stdout.write(
                    f"  {r['old_id']} {r['name']}: {r['amount']:+,.0f}円"
                )

        # 統計サマリー
        self.stdout.write('')
        self.stdout.write('-'*70)
        total_positive = sum(r['new_balance'] for r in updated_results if r.get('new_balance', 0) > 0)
        total_negative = sum(r['new_balance'] for r in updated_results if r.get('new_balance', 0) < 0)
        self.stdout.write(f'残高集計:')
        self.stdout.write(f'  預り金（プラス）合計: {total_positive:+,.0f}円')
        self.stdout.write(f'  不足金（マイナス）合計: {total_negative:+,.0f}円')

        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('DRY RUNのため、実際の変更は行われていません'))
