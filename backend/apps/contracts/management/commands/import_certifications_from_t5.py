"""
T5追加請求CSVから検定マスタと検定申込を作成するマネジメントコマンド

Usage:
    # ドライラン
    python manage.py import_certifications_from_t5 --csv /path/to/t5.csv --dry-run

    # 実行
    python manage.py import_certifications_from_t5 --csv /path/to/t5.csv
"""
import re
import pandas as pd
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.contracts.models import Certification, CertificationEnrollment
from apps.students.models import Student
from apps.schools.models import Brand
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = 'T5追加請求CSVから検定マスタと検定申込を作成'

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
        default_brand = Brand.objects.filter(brand_code='SOR').first() or Brand.objects.first()

        # CSV読み込み
        self.stdout.write(f'CSV読み込み: {csv_path}')
        df = pd.read_csv(csv_path, encoding='utf-8-sig')

        # 検定関連を抽出
        cert_keywords = ['検定', '英検', '漢検', '数検', '珠算', '暗算']
        cert_rows = df[df['顧客表記用請求名（契約、請求IDの請求は、そのすぐ下に表記）'].fillna('').str.contains('|'.join(cert_keywords))]
        self.stdout.write(f'検定関連行数: {len(cert_rows)}件')

        # 検定マスタを作成
        cert_master = {}  # (検定名, 金額) -> Certification
        created_certs = 0
        created_enrollments = 0
        skipped_no_student = 0

        for _, row in cert_rows.iterrows():
            student_id = row.get('生徒ID')
            amount = row.get('金額', 0)
            display_name = str(row.get('顧客表記用請求名（契約、請求IDの請求は、そのすぐ下に表記）', '') or '')
            brand_name = str(row.get('対象　同ブランド', '') or '')

            if pd.isna(amount) or amount == 0:
                continue

            amount = Decimal(str(int(amount)))

            # 検定種別を判定
            cert_type = 'other'
            if '英検' in display_name:
                cert_type = 'eiken'
            elif '漢検' in display_name:
                cert_type = 'kanken'
            elif '数検' in display_name:
                cert_type = 'suken'
            elif '珠算' in display_name or '暗算' in display_name:
                cert_type = 'other'  # そろばん検定

            # 級・レベルを抽出
            level = ''
            level_match = re.search(r'(\d+)級', display_name)
            if level_match:
                level = f'{level_match.group(1)}級'
            elif '準' in display_name:
                prep_match = re.search(r'準(\d+)級', display_name)
                if prep_match:
                    level = f'準{prep_match.group(1)}級'

            # 年度を抽出
            year = 2025
            year_match = re.search(r'(\d{4})年', display_name)
            if year_match:
                year = int(year_match.group(1))
            else:
                # 202507検定 形式
                ym_match = re.search(r'\((\d{6})検定\)', display_name)
                if ym_match:
                    year = int(ym_match.group(1)[:4])

            # 検定コード生成
            cert_code = f'{cert_type}_{year}_{display_name[:30].replace(" ", "_")}'
            cert_key = (cert_code, float(amount))

            # 検定マスタ作成
            if cert_key not in cert_master:
                if dry_run:
                    self.stdout.write(f'  [ドライラン] 検定マスタ: {display_name[:50]} ({amount}円)')
                    cert_master[cert_key] = None
                else:
                    # 既存チェック
                    existing = Certification.objects.filter(
                        tenant_id=tenant.id,
                        certification_code=cert_code[:50]
                    ).first()
                    if existing:
                        cert_master[cert_key] = existing
                    else:
                        with transaction.atomic():
                            cert = Certification.objects.create(
                                tenant_id=tenant.id,
                                tenant_ref=tenant,
                                certification_code=cert_code[:50],
                                certification_name=display_name[:200],
                                certification_type=cert_type,
                                level=level,
                                brand=default_brand,
                                year=year,
                                exam_fee=amount,
                                is_active=True,
                            )
                            cert_master[cert_key] = cert
                        created_certs += 1

            # 検定申込作成
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

            cert = cert_master.get(cert_key)
            if dry_run:
                self.stdout.write(f'    → 申込: {student.full_name}')
            elif cert:
                CertificationEnrollment.objects.create(
                    tenant_id=tenant.id,
                    tenant_ref=tenant,
                    student=student,
                    certification=cert,
                    status='confirmed',
                    exam_fee=amount,
                    discount_amount=Decimal('0'),
                    final_price=amount,
                )
            created_enrollments += 1

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
検定マスタ作成: {created_certs}件
検定申込作成: {created_enrollments}件
スキップ（生徒なし）: {skipped_no_student}件
'''))
