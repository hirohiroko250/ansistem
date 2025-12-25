"""
社員一覧をインポートするコマンド
"""
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import connection
from apps.tenants.models import Tenant
from apps.students.models import Guardian
import uuid


class Command(BaseCommand):
    help = '社員一覧をExcelファイルからインポートする'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Excelファイルのパス'
        )
        parser.add_argument(
            '--tenant-code',
            type=str,
            default='an',
            help='テナントコード（デフォルト: an）'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        tenant_code = options['tenant_code']

        # テナント取得
        try:
            tenant = Tenant.objects.get(tenant_code=tenant_code)
        except Tenant.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'テナント {tenant_code} が見つかりません'))
            return

        # Excelファイル読み込み
        self.stdout.write(f'ファイル読み込み中: {file_path}')
        df = pd.read_excel(file_path)
        self.stdout.write(f'総行数: {len(df)}')

        # 既存のguardian_idを取得（guardian_noは文字列型）
        guardian_ids = df['保護者ID'].dropna().astype(int).astype(str).tolist()
        existing_guardians = {
            g.guardian_no: g.id
            for g in Guardian.objects.filter(guardian_no__in=guardian_ids)
        }
        self.stdout.write(f'マッチした保護者: {len(existing_guardians)}件')

        imported_count = 0
        skipped_count = 0
        errors = []

        with connection.cursor() as cursor:
            # 既存の社員を削除（再インポート用）
            cursor.execute("DELETE FROM t19_employees WHERE tenant_id = %s", [str(tenant.id)])
            self.stdout.write('既存の社員データをクリアしました')

            for idx, row in df.iterrows():
                try:
                    guardian_id_num = row.get('保護者ID')
                    if pd.isna(guardian_id_num):
                        skipped_count += 1
                        continue

                    guardian_id_str = str(int(guardian_id_num))
                    guardian_uuid = existing_guardians.get(guardian_id_str)

                    last_name = str(row.get('姓', '')) if pd.notna(row.get('姓')) else ''
                    first_name = str(row.get('名', '')) if pd.notna(row.get('名')) else ''
                    email = str(row.get('メールアドレス', '')) if pd.notna(row.get('メールアドレス')) else ''
                    phone = str(row.get('電話番号', '')) if pd.notna(row.get('電話番号')) else ''
                    department = str(row.get('部署', '')) if pd.notna(row.get('部署')) else ''

                    # 社員割引情報
                    discount_flag = int(row.get('社員割引フラッグ', 0)) if pd.notna(row.get('社員割引フラッグ')) else 0
                    discount_amount = float(row.get('社員割引額', 0)) if pd.notna(row.get('社員割引額')) else 0
                    discount_unit = str(row.get('社員割引額単位', '')) if pd.notna(row.get('社員割引額単位')) else ''

                    # 社員番号生成（保護者IDベース）
                    employee_number = f"EMP{guardian_id_str}"

                    employee_id = str(uuid.uuid4())

                    cursor.execute("""
                        INSERT INTO t19_employees (
                            id, tenant_id, employee_no, guardian_id,
                            last_name, first_name, email, phone,
                            department, is_active,
                            discount_flag, discount_amount, discount_unit,
                            created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s,
                            %s, %s, %s,
                            NOW(), NOW()
                        )
                    """, [
                        employee_id, str(tenant.id), employee_number, str(guardian_uuid) if guardian_uuid else None,
                        last_name, first_name, email, phone,
                        department, True,
                        discount_flag == 1, discount_amount, discount_unit
                    ])

                    imported_count += 1

                except Exception as e:
                    errors.append(f"行 {idx + 1}: {str(e)}")

        self.stdout.write(self.style.SUCCESS(f'インポート完了: {imported_count}件'))
        self.stdout.write(f'スキップ: {skipped_count}件')

        if errors:
            self.stdout.write(self.style.WARNING(f'エラー: {len(errors)}件'))
            for error in errors[:10]:
                self.stdout.write(f'  - {error}')
