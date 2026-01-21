"""
T4からContractをインポート
確定ボタンでの自動請求計算を可能にする
"""
import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.contracts.models import Contract, Course
from apps.students.models import Student, Guardian
from apps.schools.models import Brand, School
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = 'T4ユーザー契約情報からContractをインポート'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            default='/Users/hirosesuzu/Library/CloudStorage/GoogleDrive-katsu44sky@gmail.com/マイドライブ/OZAシステム/月謝DATA/2月DATA/T4_ユーザー契約情報_202601141851_UTF8.csv',
            help='T4 CSVファイルパス'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には保存せず、何が作成されるかを表示'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='インポート前に既存のContractを削除'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='インポート件数の上限（テスト用）'
        )

    def handle(self, *args, **options):
        csv_path = options['csv']
        dry_run = options['dry_run']
        clear = options['clear']
        limit = options['limit']

        self.stdout.write("=" * 60)
        self.stdout.write("T4からContractインポート")
        self.stdout.write("=" * 60 + "\n")

        # テナント取得
        self.tenant = Tenant.objects.first()
        if not self.tenant:
            self.stdout.write(self.style.ERROR("テナントが見つかりません"))
            return

        # キャッシュ作成
        self._build_caches()

        # 既存データ削除
        if clear and not dry_run:
            deleted = Contract.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"既存Contract削除: {deleted[0]}件"))

        # CSVを読み込み
        self.stdout.write(f"\nCSV読み込み中: {csv_path}")
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f"CSV行数: {len(rows)}")

        if limit > 0:
            rows = rows[:limit]
            self.stdout.write(f"制限適用: {limit}件")

        # インポート実行
        contracts_to_create = []
        stats = {
            'total': 0,
            'created': 0,
            'created_active': 0,
            'created_cancelled': 0,
            'skipped_no_student': 0,
            'skipped_no_course': 0,
            'skipped_duplicate': 0,
            'skipped_ended': 0,
        }

        # 重複チェック用
        existing_keys = set()
        if not clear:
            for c in Contract.objects.values('student_id', 'course_id'):
                existing_keys.add((str(c['student_id']), str(c['course_id'])))

        for i, row in enumerate(rows):
            stats['total'] += 1

            result = self._process_row(row, existing_keys, stats)
            if result:
                contracts_to_create.append(result)
                # 重複防止用にキーを追加
                existing_keys.add((str(result.student_id), str(result.course_id)))

            if (i + 1) % 1000 == 0:
                self.stdout.write(f"  処理中... {i + 1}/{len(rows)}")

        # 保存
        self.stdout.write(f"\n作成予定: {len(contracts_to_create)}件")

        if not dry_run and contracts_to_create:
            self.stdout.write("データベースに保存中...")
            with transaction.atomic():
                Contract.objects.bulk_create(contracts_to_create, batch_size=500)
            self.stdout.write(self.style.SUCCESS("保存完了"))

        # 統計表示
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("統計")
        self.stdout.write("=" * 60)
        self.stdout.write(f"処理件数: {stats['total']}")
        self.stdout.write(f"作成: {len(contracts_to_create)}")
        self.stdout.write(f"  有効(active): {stats['created_active']}")
        self.stdout.write(f"  退会(cancelled): {stats['created_cancelled']}")
        self.stdout.write(f"スキップ（生徒なし）: {stats['skipped_no_student']}")
        self.stdout.write(f"スキップ（コースなし）: {stats['skipped_no_course']}")
        self.stdout.write(f"スキップ（重複）: {stats['skipped_duplicate']}")
        self.stdout.write(f"スキップ（終了済み）: {stats['skipped_ended']}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] 実際には保存されていません"))

    def _build_caches(self):
        """キャッシュを作成"""
        self.stdout.write("キャッシュ作成中...")

        # 生徒（student_noでマッチ）
        self.students_by_no = {}
        for s in Student.objects.select_related('tenant').all():
            if s.student_no:
                self.students_by_no[s.student_no] = s

        # コース（course_codeでマッチ）
        self.courses_by_code = {}
        for c in Course.objects.all():
            if c.course_code:
                self.courses_by_code[c.course_code] = c

        # ブランド
        self.brands_by_name = {}
        self.brands_by_short = {}
        for b in Brand.objects.all():
            if b.brand_name:
                self.brands_by_name[b.brand_name] = b
            if b.brand_name_short:
                self.brands_by_short[b.brand_name_short] = b

        # 保護者（guardian経由で生徒を検索する場合用）
        self.guardians_by_no = {}
        for g in Guardian.objects.all():
            if hasattr(g, 'guardian_no') and g.guardian_no:
                self.guardians_by_no[g.guardian_no] = g

        # 校舎
        self.schools_by_name = {}
        for s in School.objects.all():
            if s.school_name:
                self.schools_by_name[s.school_name] = s

        self.stdout.write(f"  生徒: {len(self.students_by_no)}件")
        self.stdout.write(f"  コース: {len(self.courses_by_code)}件")
        self.stdout.write(f"  ブランド: {len(self.brands_by_name)}件")

    def _parse_date(self, date_str):
        """日付をパース"""
        if not date_str or not date_str.strip():
            return None
        try:
            return datetime.strptime(date_str.strip(), '%Y/%m/%d').date()
        except ValueError:
            return None

    def _process_row(self, row, existing_keys, stats):
        """1行を処理してContractを作成"""
        course_id_csv = row.get('受講ID', '').strip()
        student_id_csv = row.get('生徒ID', '').strip()
        guardian_id_csv = row.get('保護者ID', '').strip()
        contract_code = row.get('契約ID', '').strip()
        contract_name = row.get('契約名', '').strip()
        brand_name = row.get('Class用ブランド名', '').strip()
        start_date_str = row.get('開始日', '').strip()
        end_date_str = row.get('終了日', '').strip()
        brand_withdrawal_str = row.get('ブランド退会日', '').strip()
        full_withdrawal_str = row.get('全退会日', '').strip()

        # 日付パース
        start_date = self._parse_date(start_date_str)
        end_date = self._parse_date(end_date_str)
        brand_withdrawal_date = self._parse_date(brand_withdrawal_str)
        full_withdrawal_date = self._parse_date(full_withdrawal_str)

        # 終了済みチェック（2026年2月1日より前に終了）
        billing_month = datetime(2026, 2, 1).date()
        if end_date and end_date < billing_month:
            stats['skipped_ended'] += 1
            return None

        # 生徒を検索
        student = self.students_by_no.get(student_id_csv)
        if not student:
            stats['skipped_no_student'] += 1
            return None

        # コースを検索
        course = self.courses_by_code.get(contract_code)
        if not course:
            stats['skipped_no_course'] += 1
            return None

        # 重複チェック
        key = (str(student.id), str(course.id))
        if key in existing_keys:
            stats['skipped_duplicate'] += 1
            return None

        # ブランドを検索
        brand = self.brands_by_name.get(brand_name)
        if not brand:
            brand = self.brands_by_short.get(brand_name)

        # 保護者を検索
        guardian = None
        if guardian_id_csv:
            # student_guardiansテーブル経由で検索
            guardians = student.guardians.all()
            if guardians:
                guardian = guardians.first()

        # 校舎を検索（コースから取得を試みる）
        school = None
        if hasattr(course, 'school') and course.school:
            school = course.school

        # ステータス判定（ブランド退会日ベース）
        # ブランド退会日が請求月より前ならCANCELLED
        status = Contract.Status.ACTIVE
        if brand_withdrawal_date and brand_withdrawal_date < billing_month:
            status = Contract.Status.CANCELLED
        elif full_withdrawal_date and full_withdrawal_date < billing_month:
            status = Contract.Status.CANCELLED

        # Contract作成
        contract = Contract(
            tenant_id=self.tenant.id,
            contract_no=course_id_csv,  # 受講IDを契約番号として使用
            old_id=course_id_csv,
            student=student,
            guardian=guardian,
            school=school,
            brand=brand,
            course=course,
            contract_date=start_date or datetime.now().date(),
            start_date=start_date or datetime.now().date(),
            end_date=end_date or brand_withdrawal_date or full_withdrawal_date,
            status=status,
            notes=f'{contract_code}: {contract_name}',
        )

        stats['created'] += 1
        if status == Contract.Status.ACTIVE:
            stats['created_active'] += 1
        else:
            stats['created_cancelled'] += 1
        return contract
