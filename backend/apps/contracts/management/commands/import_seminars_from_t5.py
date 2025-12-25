"""
T5追加請求CSVから講習会マスタと講習会申込を作成するマネジメントコマンド

Usage:
    # ドライラン
    python manage.py import_seminars_from_t5 --csv /path/to/t5.csv --dry-run

    # 実行
    python manage.py import_seminars_from_t5 --csv /path/to/t5.csv
"""
import re
import pandas as pd
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.contracts.models import Seminar, SeminarEnrollment
from apps.students.models import Student
from apps.schools.models import Brand
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = 'T5追加請求CSVから講習会マスタと講習会申込を作成'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            required=True,
            help='T5追加請求CSVファイルのパス'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='ドライラン（実際には変更しない）'
        )

    def handle(self, *args, **options):
        csv_path = options['csv']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ==='))

        # テナント取得
        tenant = Tenant.objects.first()
        if not tenant:
            self.stdout.write(self.style.ERROR('テナントが見つかりません'))
            return

        # マッピング作成
        self.stdout.write('マッピングデータ作成中...')

        # 生徒マッピング
        student_map = {}
        for s in Student.objects.only('id', 'old_id').all():
            if s.old_id:
                try:
                    student_map[int(s.old_id)] = s
                except ValueError:
                    pass
        self.stdout.write(f'  生徒: {len(student_map)}件')

        # ブランドマッピング
        brand_map = {}
        for b in Brand.objects.all():
            brand_map[b.brand_code] = b
        default_brand = Brand.objects.filter(brand_code='DEFAULT').first() or Brand.objects.first()

        # CSV読み込み
        self.stdout.write(f'CSV読み込み: {csv_path}')
        df = pd.read_csv(csv_path, encoding='utf-8-sig')

        # 講習会関連を抽出（カテゴリまたは名前で判定）
        seminar_categories = ['夏期講習会', '講習会', '必須講習会', '冬期講習会', '春期講習会']
        seminar_keywords = ['講習', '夏期', '冬期', '春期']

        seminar_rows = df[
            (df['対象カテゴリー'].isin(seminar_categories)) |
            (df['顧客表記用請求名（契約、請求IDの請求は、そのすぐ下に表記）'].fillna('').str.contains('|'.join(seminar_keywords)))
        ]
        self.stdout.write(f'講習会関連行数: {len(seminar_rows)}件')

        # 講習会マスタを作成
        seminar_master = {}  # (講習会名, 金額) -> Seminar
        created_seminars = 0
        created_enrollments = 0
        skipped_no_student = 0

        for _, row in seminar_rows.iterrows():
            student_id = row.get('生徒ID')
            amount = row.get('金額', 0)
            display_name = str(row.get('顧客表記用請求名（契約、請求IDの請求は、そのすぐ下に表記）', '') or '')
            category = str(row.get('対象カテゴリー', '') or '')
            brand_name = str(row.get('対象　同ブランド', '') or '')

            if pd.isna(amount) or amount == 0:
                continue

            amount = Decimal(str(int(amount)))

            # 講習会種別を判定
            seminar_type = 'other'
            if '夏期' in display_name or '夏期' in category:
                seminar_type = 'summer'
            elif '冬期' in display_name or '冬期' in category:
                seminar_type = 'winter'
            elif '春期' in display_name or '春期' in category:
                seminar_type = 'spring'

            # 年度を抽出
            year = 2025
            year_match = re.search(r'(\d{4})年', display_name)
            if year_match:
                year = int(year_match.group(1))

            # 講習会コード生成
            seminar_code = f'{seminar_type}_{year}_{display_name[:30].replace(" ", "_")}'
            seminar_key = (seminar_code, float(amount))

            # 講習会マスタ作成
            if seminar_key not in seminar_master:
                if dry_run:
                    self.stdout.write(f'  [ドライラン] 講習会マスタ: {display_name[:50]} ({amount}円)')
                    seminar_master[seminar_key] = None
                else:
                    # 既存チェック
                    existing = Seminar.objects.filter(
                        tenant_id=tenant.id,
                        seminar_code=seminar_code[:50]
                    ).first()
                    if existing:
                        seminar_master[seminar_key] = existing
                    else:
                        with transaction.atomic():
                            seminar = Seminar.objects.create(
                                tenant_id=tenant.id,
                                tenant_ref=tenant,
                                seminar_code=seminar_code[:50],
                                seminar_name=display_name[:200],
                                seminar_type=seminar_type,
                                brand=default_brand,
                                year=year,
                                base_price=amount,
                                is_active=True,
                            )
                            seminar_master[seminar_key] = seminar
                        created_seminars += 1

            # 講習会申込作成
            if pd.isna(student_id):
                skipped_no_student += 1
                continue

            try:
                student_id_int = int(student_id)
            except ValueError:
                skipped_no_student += 1
                continue

            student = student_map.get(student_id_int)
            if not student:
                skipped_no_student += 1
                continue

            seminar = seminar_master.get(seminar_key)
            if dry_run:
                self.stdout.write(f'    → 申込: {student.full_name}')
            elif seminar:
                SeminarEnrollment.objects.create(
                    tenant_id=tenant.id,
                    tenant_ref=tenant,
                    student=student,
                    seminar=seminar,
                    status='confirmed',
                    unit_price=amount,
                    discount_amount=Decimal('0'),
                    final_price=amount,
                )
            created_enrollments += 1

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
講習会マスタ作成: {created_seminars}件
講習会申込作成: {created_enrollments}件
スキップ（生徒なし）: {skipped_no_student}件
'''))
