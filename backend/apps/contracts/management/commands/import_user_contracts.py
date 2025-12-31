"""
ユーザー契約情報CSVからContract + StudentItemを作成するマネジメントコマンド

Usage:
    # ドライラン
    python manage.py import_user_contracts --csv /path/to/file.csv --dry-run

    # 実行
    python manage.py import_user_contracts --csv /path/to/file.csv
"""
import csv
import pandas as pd
from datetime import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.contracts.models import Contract, StudentItem
from apps.students.models import Student, Guardian
from apps.schools.models import Brand, School
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = 'ユーザー契約情報CSVからContract + StudentItemを作成'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            required=True,
            help='ユーザー契約情報CSVファイルのパス'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='ドライラン（実際には変更しない）'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='既存データを削除してから作成'
        )
        parser.add_argument(
            '--skip-output',
            type=str,
            default='skipped_contracts.csv',
            help='スキップしたデータの出力先CSVファイル'
        )

    def handle(self, *args, **options):
        csv_path = options['csv']
        dry_run = options['dry_run']
        clear_existing = options.get('clear_existing', False)
        skip_output = options.get('skip_output', 'skipped_contracts.csv')

        if dry_run:
            self.stdout.write(self.style.WARNING('=== ドライランモード ==='))

        # テナント取得
        tenant = Tenant.objects.first()
        if not tenant:
            self.stdout.write(self.style.ERROR('テナントが見つかりません'))
            return

        # デフォルト校舎取得
        default_school = School.objects.first()
        if not default_school:
            self.stdout.write(self.style.ERROR('校舎が見つかりません'))
            return

        # デフォルトブランド取得
        default_brand = Brand.objects.filter(brand_code='DEFAULT').first() or Brand.objects.first()
        if not default_brand:
            self.stdout.write(self.style.ERROR('ブランドが見つかりません'))
            return

        # 既存データ削除
        if clear_existing and not dry_run:
            contract_count = Contract.objects.all().delete()[0]
            item_count = StudentItem.objects.all().delete()[0]
            self.stdout.write(f'既存データ削除: Contract {contract_count}件, StudentItem {item_count}件')

        # マッピング作成
        self.stdout.write('マッピングデータ作成中...')

        # 生徒マッピング (old_id -> Student) - primary_schoolも含める
        student_map = {}
        for s in Student.objects.only('id', 'old_id', 'guardian_id', 'primary_school_id').all():
            if s.old_id:
                try:
                    student_map[int(s.old_id)] = s
                except ValueError:
                    pass
        self.stdout.write(f'  生徒: {len(student_map)}件')

        # 保護者マッピング (old_id -> Guardian)
        guardian_map = {}
        for g in Guardian.objects.only('id', 'old_id').all():
            if g.old_id:
                guardian_map[str(g.old_id)] = g
        self.stdout.write(f'  保護者: {len(guardian_map)}件')

        # ブランドマッピング (code -> Brand)
        brand_map = {}
        for b in Brand.objects.all():
            brand_map[b.brand_code] = b
            # 24SOR -> SOR のマッピングも追加
            brand_map[f'24{b.brand_code}'] = b
        self.stdout.write(f'  ブランド: {len(brand_map)}件')

        # 校舎マッピング (school_code -> School)
        school_map = {}
        for s in School.objects.all():
            school_map[s.school_code] = s
        self.stdout.write(f'  校舎: {len(school_map)}件')

        # CSV読み込み
        self.stdout.write(f'CSV読み込み: {csv_path}')
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        self.stdout.write(f'  行数: {len(df)}件')

        # 既存の契約番号を取得
        existing_contracts = set(Contract.objects.values_list('contract_no', flat=True))
        self.stdout.write(f'  既存契約: {len(existing_contracts)}件')

        # 各行が1つの契約（生徒ID + 契約ID で一意）
        created_contracts = 0
        created_items = 0
        skipped_no_student = 0
        skipped_no_guardian = 0
        skipped_ended = 0
        skipped_existing = 0
        skipped_rows = []  # スキップした行を保存

        for _, first_row in df.iterrows():
            contract_id = first_row.get('契約ID')
            if pd.isna(contract_id):
                skipped_no_student += 1
                skipped_rows.append({**first_row.to_dict(), 'skip_reason': '契約IDなし'})
                continue

            # 生徒ID確認
            student_id = first_row.get('生徒ID')
            if pd.isna(student_id):
                skipped_no_student += 1
                skipped_rows.append({**first_row.to_dict(), 'skip_reason': '生徒IDなし'})
                continue

            try:
                student_id = int(student_id)
            except ValueError:
                skipped_no_student += 1
                skipped_rows.append({**first_row.to_dict(), 'skip_reason': '生徒ID不正'})
                continue

            student = student_map.get(student_id)
            if not student:
                skipped_no_student += 1
                skipped_rows.append({**first_row.to_dict(), 'skip_reason': '生徒未発見'})
                continue

            # 保護者
            guardian_id = first_row.get('保護者ID')
            guardian = None
            if not pd.isna(guardian_id):
                guardian = guardian_map.get(str(int(guardian_id)))
            if not guardian:
                # 生徒から取得
                if student.guardian_id:
                    guardian = Guardian.objects.filter(id=student.guardian_id).first()
            if not guardian:
                skipped_no_guardian += 1
                skipped_rows.append({**first_row.to_dict(), 'skip_reason': '保護者未発見'})
                continue

            # 生徒と保護者の紐付けを更新
            if student.guardian_id != guardian.id:
                if not dry_run:
                    student.guardian = guardian
                    student.save(update_fields=['guardian'])

            # 終了日チェック（過去の契約はスキップ）
            end_date_str = str(first_row.get('終了日', ''))
            brand_end_str = str(first_row.get('ブランド退会日', ''))
            all_end_str = str(first_row.get('全退会日', ''))

            # 終了している契約はスキップ
            if all_end_str and all_end_str != 'nan' and all_end_str != '':
                try:
                    all_end = pd.to_datetime(all_end_str)
                    if all_end < datetime.now():
                        skipped_ended += 1
                        skipped_rows.append({**first_row.to_dict(), 'skip_reason': '終了済み'})
                        continue
                except (ValueError, TypeError):
                    pass

            # ブランド抽出（契約ID: 24SOR_1000006 -> SOR）
            brand_code = None
            brand = None
            if contract_id and '_' in str(contract_id):
                prefix = str(contract_id).split('_')[0]
                # 24SOR -> SOR
                if prefix.startswith('24') and len(prefix) > 2:
                    brand_code = prefix[2:]
                else:
                    brand_code = prefix
                brand = brand_map.get(brand_code) or brand_map.get(prefix)

            # ブランドが見つからない場合はデフォルトを使用
            if not brand:
                brand = default_brand

            # 開始日
            start_date = None
            start_date_str = str(first_row.get('開始日', ''))
            if start_date_str and start_date_str != 'nan':
                try:
                    start_date = pd.to_datetime(start_date_str).date()
                except (ValueError, TypeError):
                    pass

            # 終了日
            end_date = None
            if end_date_str and end_date_str != 'nan' and end_date_str != '3000/3/31':
                try:
                    end_date = pd.to_datetime(end_date_str).date()
                except (ValueError, TypeError):
                    pass

            # 契約名
            contract_name = str(first_row.get('契約名', ''))
            notes = str(first_row.get('備考', '')) if not pd.isna(first_row.get('備考')) else ''

            # 一意の契約番号 (契約ID_生徒ID)
            unique_contract_no = f'{contract_id}_{student_id}'

            # 既存チェック（作成済みも含む）
            if unique_contract_no in existing_contracts:
                skipped_existing += 1
                continue

            # 校舎を取得（生徒のprimary_school、なければデフォルト）
            school = None
            if student.primary_school_id:
                school = School.objects.filter(id=student.primary_school_id).first()
            if not school:
                school = default_school

            if dry_run:
                self.stdout.write(
                    f'  [ドライラン] Contract: {unique_contract_no} - {student.full_name} - {contract_name}'
                )
                # ドライランでも重複を防ぐためにセットに追加
                existing_contracts.add(unique_contract_no)
            else:
                with transaction.atomic():
                    # Contract作成
                    contract = Contract.objects.create(
                        tenant_id=tenant.id,
                        tenant_ref=tenant,
                        contract_no=unique_contract_no,
                        old_id=unique_contract_no,
                        student=student,
                        guardian=guardian,
                        school=school,
                        brand=brand,
                        status='active',
                        contract_date=start_date or datetime.now().date(),
                        start_date=start_date,
                        end_date=end_date,
                        notes=notes,
                    )

                    # StudentItem作成（基本の月額請求用）
                    StudentItem.objects.create(
                        tenant_id=tenant.id,
                        tenant_ref=tenant,
                        old_id=unique_contract_no,
                        student=student,
                        contract=contract,
                        brand=brand,
                        start_date=start_date,
                        billing_month=f'2025-01',  # 1月請求
                        quantity=1,
                        unit_price=Decimal('0'),  # 金額はAC_5から取得済み
                        discount_amount=Decimal('0'),
                        final_price=Decimal('0'),
                        notes=contract_name,
                    )

                    created_items += 1
                    # 作成済みセットに追加
                    existing_contracts.add(unique_contract_no)

            created_contracts += 1

        # スキップしたデータをCSVに出力
        if skipped_rows and not dry_run:
            with open(skip_output, 'w', newline='', encoding='utf-8-sig') as f:
                if skipped_rows:
                    writer = csv.DictWriter(f, fieldnames=skipped_rows[0].keys())
                    writer.writeheader()
                    writer.writerows(skipped_rows)
            self.stdout.write(f'スキップデータを {skip_output} に出力しました')

        self.stdout.write(self.style.SUCCESS(f'''
=== 完了 ===
Contract作成: {created_contracts}件
StudentItem作成: {created_items}件
スキップ（既存）: {skipped_existing}件
スキップ（生徒なし）: {skipped_no_student}件
スキップ（保護者なし）: {skipped_no_guardian}件
スキップ（終了済み）: {skipped_ended}件
'''))
