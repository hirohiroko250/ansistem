"""
2026年2月請求データ検証スクリプト
T20（過不足金一覧）と比較して正確性を確認
"""
import csv
from decimal import Decimal
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db.models import Sum
from apps.contracts.models import StudentItem, StudentDiscount
from apps.students.models import Student, Guardian


class Command(BaseCommand):
    help = '2026年2月請求データをT20と比較検証'

    BILLING_MONTH = '2026-02'
    DATA_DIR = '/Users/hirosesuzu/Library/CloudStorage/GoogleDrive-katsu44sky@gmail.com/マイドライブ/OZAシステム/月謝DATA/2月DATA'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detail',
            action='store_true',
            help='詳細な差分を表示'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='表示する差分の上限'
        )

    def handle(self, *args, **options):
        show_detail = options['detail']
        limit = options['limit']

        self.stdout.write("=== 2026年2月請求データ検証 ===\n")

        # 1. T20データを読み込み（2026/02/01の請求のみ）
        t20_data = self._load_t20_data()

        # 2. DBのデータを集計
        db_data = self._load_db_data()

        # 3. 比較
        self._compare_data(t20_data, db_data, show_detail, limit)

    def _load_t20_data(self):
        """T20（過不足金一覧）を読み込み"""
        csv_path = f"{self.DATA_DIR}/T20_過不足金一覧_202601141851_UTF8.csv"
        self.stdout.write(f"T20読み込み中: {csv_path}")

        guardian_totals = {}  # guardian_old_id -> total

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                billing_date = row.get('請求日', '').strip()
                if billing_date != '2026/02/01':
                    continue

                guardian_old_id = row.get('保護者ID', '').strip()
                if not guardian_old_id:
                    continue

                # 過不足金（これが請求総額？）
                # T20は過不足金一覧なので、請求金額の直接的なソースではない可能性あり
                # 実際の請求金額はT4+T5から計算すべきかもしれない
                balance_str = row.get('過不足金', '0').strip()
                try:
                    balance = Decimal(balance_str)
                except:
                    balance = Decimal('0')

                guardian_totals[guardian_old_id] = balance

        self.stdout.write(f"  2026/02/01の保護者数: {len(guardian_totals)}件")
        return guardian_totals

    def _load_db_data(self):
        """DBから2026-02のデータを集計"""
        self.stdout.write(f"\nDB読み込み中...")

        # 保護者ごとの集計
        guardian_totals = defaultdict(Decimal)

        # StudentItemから集計
        items = StudentItem.objects.filter(
            billing_month=self.BILLING_MONTH
        ).select_related('student__guardians')

        item_count = 0
        for item in items:
            student = item.student
            if not student:
                continue

            # 保護者のold_idを取得
            guardian = student.guardians.first()
            if guardian and guardian.old_id:
                guardian_totals[guardian.old_id] += item.final_price or Decimal('0')
                item_count += 1

        # StudentDiscountから集計（2026/02が範囲内のもの）
        from datetime import date
        feb_date = date(2026, 2, 1)

        discounts = StudentDiscount.objects.filter(
            is_active=True,
        ).filter(
            start_date__lte=feb_date
        ).filter(
            end_date__gte=feb_date
        ).select_related('student', 'guardian')

        discount_count = 0
        for discount in discounts:
            guardian = discount.guardian
            if not guardian and discount.student:
                guardian = discount.student.guardians.first()

            if guardian and guardian.old_id:
                # 割引額（マイナス値）を加算
                guardian_totals[guardian.old_id] += discount.amount or Decimal('0')
                discount_count += 1

        self.stdout.write(f"  StudentItem: {item_count}件")
        self.stdout.write(f"  StudentDiscount: {discount_count}件")
        self.stdout.write(f"  保護者数: {len(guardian_totals)}件")

        return dict(guardian_totals)

    def _compare_data(self, t20_data, db_data, show_detail, limit):
        """データを比較"""
        self.stdout.write("\n=== 比較結果 ===")

        # 集計
        t20_guardians = set(t20_data.keys())
        db_guardians = set(db_data.keys())

        common = t20_guardians & db_guardians
        only_t20 = t20_guardians - db_guardians
        only_db = db_guardians - t20_guardians

        self.stdout.write(f"\n保護者数:")
        self.stdout.write(f"  T20のみ: {len(only_t20)}件")
        self.stdout.write(f"  DBのみ: {len(only_db)}件")
        self.stdout.write(f"  両方: {len(common)}件")

        # 金額比較（共通の保護者）
        match_count = 0
        diff_count = 0
        diffs = []

        for guardian_id in common:
            t20_amount = t20_data[guardian_id]
            db_amount = db_data[guardian_id]

            if t20_amount == db_amount:
                match_count += 1
            else:
                diff_count += 1
                diff = db_amount - t20_amount
                diffs.append({
                    'guardian_id': guardian_id,
                    't20': t20_amount,
                    'db': db_amount,
                    'diff': diff,
                })

        self.stdout.write(f"\n金額比較（共通{len(common)}件）:")
        self.stdout.write(f"  一致: {match_count}件")
        self.stdout.write(f"  不一致: {diff_count}件")

        if diffs and show_detail:
            self.stdout.write(f"\n=== 不一致の詳細（上位{limit}件）===")
            diffs.sort(key=lambda x: abs(x['diff']), reverse=True)
            for d in diffs[:limit]:
                self.stdout.write(
                    f"  保護者{d['guardian_id']}: T20={d['t20']:,}円, DB={d['db']:,}円, 差={d['diff']:,}円"
                )

        # T20総額とDB総額の比較
        t20_total = sum(t20_data.values())
        db_total = sum(db_data.values())

        self.stdout.write(f"\n総額比較:")
        self.stdout.write(f"  T20総額: {t20_total:,}円")
        self.stdout.write(f"  DB総額: {db_total:,}円")
        self.stdout.write(f"  差額: {db_total - t20_total:,}円")

        # 注意事項
        self.stdout.write("\n注意: T20は過不足金一覧のため、請求金額ではなく")
        self.stdout.write("      残高（未払い/過払い）を表している可能性があります。")
        self.stdout.write("      正確な比較には請求明細の別途確認が必要です。")
