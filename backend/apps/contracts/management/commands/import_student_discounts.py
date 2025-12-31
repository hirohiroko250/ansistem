"""
StudentDiscountにT6割引情報をインポート
"""
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.contracts.models import StudentDiscount, Course, Pack, Product
from apps.students.models import Student, Guardian
from apps.schools.models import Brand
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = 'T6割引情報をStudentDiscountにインポート'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            required=True,
            help='T6割引情報CSVファイルパス'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には保存せず、何が作成されるかを表示'
        )
        parser.add_argument(
            '--include-all',
            action='store_true',
            help='マッチしないレコードも含めてインポート'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='インポート前に既存データを削除'
        )

    def handle(self, *args, **options):
        csv_path = options['csv']
        dry_run = options['dry_run']
        include_all = options['include_all']
        clear = options['clear']

        # デフォルトテナントを取得
        self.default_tenant = Tenant.objects.first()
        if not self.default_tenant:
            self.stdout.write(self.style.ERROR("テナントが見つかりません"))
            return

        # 既存データを削除
        if clear and not dry_run:
            deleted_count = StudentDiscount.objects.count()
            StudentDiscount.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"既存の{deleted_count}件を削除しました"))

        # キャッシュを作成
        self.students_by_old_id = {
            s.old_id: s for s in Student.objects.all() if s.old_id
        }
        self.guardians_by_old_id = {
            g.old_id: g for g in Guardian.objects.all() if g.old_id
        }
        self.courses_by_code = {
            c.course_code: c for c in Course.objects.all() if c.course_code
        }
        self.brands_by_name = {
            b.brand_name: b for b in Brand.objects.all()
        }

        self.stdout.write(f"キャッシュ作成完了:")
        self.stdout.write(f"  生徒: {len(self.students_by_old_id)}件")
        self.stdout.write(f"  保護者: {len(self.guardians_by_old_id)}件")
        self.stdout.write(f"  コース: {len(self.courses_by_code)}件")
        self.stdout.write(f"  ブランド: {len(self.brands_by_name)}件")

        # インポート実行
        created = self.import_discounts(csv_path, dry_run, include_all)

        # サマリー
        self.stdout.write("\n=== サマリー ===")
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"[DRY RUN] {created}件のStudentDiscountを作成予定"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"{created}件のStudentDiscountを作成しました"
            ))

    def import_discounts(self, csv_path, dry_run, include_all):
        """T6割引情報をインポート"""
        self.stdout.write(f"\n=== T6割引情報インポート ===")
        self.stdout.write(f"ファイル: {csv_path}")

        created_count = 0
        skipped_count = 0
        error_count = 0
        no_student_count = 0
        inactive_count = 0

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f"行数: {len(rows)}")

        for row in rows:
            try:
                # 有無チェック
                umu = row.get('有無', '').strip()
                if umu != '1':
                    inactive_count += 1
                    if not include_all:
                        skipped_count += 1
                        continue

                # 生徒を検索
                student_old_id = row.get('生徒ID', '').strip()
                student = self.students_by_old_id.get(student_old_id) if student_old_id else None

                # 保護者を検索
                guardian_old_id = row.get('保護者ID', '').strip()
                guardian = self.guardians_by_old_id.get(guardian_old_id) if guardian_old_id else None

                if not student and not guardian:
                    no_student_count += 1
                    if not include_all:
                        skipped_count += 1
                        continue

                # ブランドを取得
                brand_name = row.get('対象　同ブランド', '').strip()
                brand = self.brands_by_name.get(brand_name)

                # 契約IDからコースを検索
                contract_id = row.get('対象　契約ID', '').strip()
                # course = self.courses_by_code.get(contract_id)  # 今は使わない

                # 割引名
                discount_name = row.get('顧客表記用割引名（契約、請求IDの割引は、そのすぐ下に表記）', '').strip()

                # 金額をパース
                amount_str = row.get('金額', '0').strip()
                try:
                    amount = Decimal(amount_str)
                except (InvalidOperation, ValueError):
                    amount = Decimal('0')

                # 割引単位
                unit_str = row.get('割引単位', '円').strip()
                discount_unit = 'percent' if unit_str == '%' else 'yen'

                # 開始日をパース
                start_date_str = row.get('開始日', '').strip()
                start_date = None
                if start_date_str:
                    try:
                        start_date = datetime.strptime(start_date_str, '%Y/%m/%d').date()
                    except ValueError:
                        pass

                # 終了日をパース
                end_date_str = row.get('終了日', '').strip()
                end_date = None
                if end_date_str:
                    try:
                        end_date = datetime.strptime(end_date_str, '%Y/%m/%d').date()
                    except ValueError:
                        pass

                # 繰り返し・自動割引
                is_recurring = row.get('繰り返し', '').strip() == '1'
                is_auto = row.get('自動割引', '').strip() == '1'

                # 終了条件
                end_condition_str = row.get('終了条件', '').strip()
                end_condition_map = {
                    '１回だけ': 'once',
                    '毎月': 'monthly',
                    '終了日まで': 'until_end_date',
                }
                end_condition = end_condition_map.get(end_condition_str, 'once')

                # 備考
                notes_parts = []
                if row.get('社長のIF文用備考', '').strip():
                    notes_parts.append(row.get('社長のIF文用備考', '').strip())
                if not student and student_old_id:
                    notes_parts.append(f"[旧生徒ID: {student_old_id}]")
                if not guardian and guardian_old_id:
                    notes_parts.append(f"[旧保護者ID: {guardian_old_id}]")
                if umu != '1':
                    notes_parts.append(f"[有無: {umu}]")
                notes = ' '.join(notes_parts)

                # テナントIDを決定
                if student:
                    tenant_id = student.tenant_id
                elif guardian:
                    tenant_id = guardian.tenant_id
                else:
                    tenant_id = self.default_tenant.id

                # StudentDiscountを作成
                if not dry_run:
                    StudentDiscount.objects.create(
                        tenant_id=tenant_id,
                        old_id=row.get('割引ID', ''),
                        student=student,
                        guardian=guardian,
                        brand=brand,
                        discount_name=discount_name,
                        amount=amount,
                        discount_unit=discount_unit,
                        start_date=start_date,
                        end_date=end_date,
                        is_recurring=is_recurring,
                        is_auto=is_auto,
                        end_condition=end_condition,
                        is_active=(umu == '1'),
                        notes=notes,
                    )
                created_count += 1

            except Exception as e:
                error_count += 1
                if error_count <= 10:
                    self.stdout.write(self.style.ERROR(f"エラー: {e} - {row.get('割引ID', '')}"))

        self.stdout.write(f"作成: {created_count}件, スキップ: {skipped_count}件, エラー: {error_count}件")
        self.stdout.write(f"  (生徒/保護者なし: {no_student_count}件, 有無!=1: {inactive_count}件)")
        return created_count
