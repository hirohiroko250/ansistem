"""
契約にコースと月額を紐付けるコマンド
T4データから受講ID→契約IDのマッピングを取得し、
契約IDでCourseを検索して紐付ける
"""
import pandas as pd
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.contracts.models import Contract, Course, CourseItem, Product


class Command(BaseCommand):
    help = '契約にコースと月額を紐付ける'

    def add_arguments(self, parser):
        parser.add_argument(
            '--t4-xlsx',
            type=str,
            required=True,
            help='T4 XLSXファイルパス'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には保存しない'
        )

    def handle(self, *args, **options):
        xlsx_path = options['t4_xlsx']
        dry_run = options['dry_run']

        self.stdout.write(f'ファイル: {xlsx_path}')
        self.stdout.write(f'Dry Run: {dry_run}')

        # T4データ読み込み
        df = pd.read_excel(xlsx_path)
        df = df.fillna('')

        self.stdout.write(f'T4データ行数: {len(df)}')

        # 受講ID → 契約ID のマッピング作成
        enrollment_to_course = {}
        for _, row in df.iterrows():
            enrollment_id = str(row.get('受講ID', '')).strip()
            contract_id = str(row.get('契約ID', '')).strip()
            if enrollment_id and contract_id:
                enrollment_to_course[enrollment_id] = contract_id

        self.stdout.write(f'受講ID→契約IDマッピング数: {len(enrollment_to_course)}')

        # コースをcourse_codeでキャッシュ
        course_cache = {}
        for course in Course.objects.all():
            if course.course_code:
                course_cache[course.course_code] = course
        self.stdout.write(f'コースキャッシュ数: {len(course_cache)}')

        # コースなし契約を処理
        contracts_without_course = Contract.objects.filter(course__isnull=True)
        total = contracts_without_course.count()
        self.stdout.write(f'コースなし契約数: {total}')

        updated = 0
        skipped = 0
        not_found_courses = set()

        for contract in contracts_without_course.iterator():
            old_id = contract.old_id
            if not old_id:
                skipped += 1
                continue

            # 受講ID（old_id）から契約IDを取得
            course_code = enrollment_to_course.get(old_id)
            if not course_code:
                skipped += 1
                continue

            # 契約ID（course_code）でコースを検索
            course = course_cache.get(course_code)
            if not course:
                not_found_courses.add(course_code)
                skipped += 1
                continue

            # コースを設定
            contract.course = course

            # 月額を計算（授業料 + 月会費 + 設備費）
            monthly_total = self.calculate_monthly_total(course)
            contract.monthly_total = monthly_total

            if not dry_run:
                contract.save(update_fields=['course', 'monthly_total'])

            updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'完了: 更新{updated}件, スキップ{skipped}件'
        ))

        if not_found_courses:
            self.stdout.write(self.style.WARNING(
                f'見つからなかったコース: {len(not_found_courses)}件'
            ))
            for code in list(not_found_courses)[:10]:
                self.stdout.write(f'  - {code}')

    def calculate_monthly_total(self, course):
        """コースから月額合計を計算（授業料 + 月会費 + 設備費）"""
        monthly_types = [
            Product.ItemType.TUITION,
            Product.ItemType.MONTHLY_FEE,
            Product.ItemType.FACILITY,
        ]

        total = Decimal('0')
        for ci in course.course_items.filter(is_active=True).select_related('product'):
            if ci.product and ci.product.item_type in monthly_types:
                price = ci.get_price()
                if price:
                    total += Decimal(str(price))

        return total
