"""
社員テーブルから社員割引をStudentDiscountに同期するコマンド
"""
from django.core.management.base import BaseCommand
from django.db import connection
from apps.tenants.models import Tenant
from apps.students.models import Guardian, Student
from apps.contracts.models import StudentDiscount
import uuid


class Command(BaseCommand):
    help = '社員テーブルの割引情報をStudentDiscountに同期する'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant-code',
            type=str,
            default='100000',
            help='テナントコード（デフォルト: 100000）'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には作成せず、対象を表示のみ'
        )

    def handle(self, *args, **options):
        tenant_code = options['tenant_code']
        dry_run = options['dry_run']

        # テナント取得
        try:
            tenant = Tenant.objects.get(tenant_code=tenant_code)
        except Tenant.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'テナント {tenant_code} が見つかりません'))
            return

        # 社員一覧を取得（割引フラグがtrueのもの）
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    e.id, e.employee_no, e.guardian_id, e.last_name, e.first_name,
                    e.discount_flag, e.discount_amount, e.discount_unit
                FROM t19_employees e
                WHERE e.tenant_id = %s AND e.discount_flag = true AND e.is_active = true
            """, [str(tenant.id)])
            employees = cursor.fetchall()

        self.stdout.write(f'社員割引対象者: {len(employees)}名')

        created_count = 0
        skipped_count = 0
        errors = []

        for emp in employees:
            emp_id, emp_no, guardian_id, last_name, first_name, discount_flag, discount_amount, discount_unit = emp

            if not guardian_id:
                skipped_count += 1
                continue

            # 保護者の子供を取得
            try:
                guardian = Guardian.objects.get(id=guardian_id)
                students = Student.objects.filter(
                    guardian_relations__guardian=guardian,
                    status='enrolled'  # 在籍中の生徒のみ
                )

                if not students.exists():
                    self.stdout.write(f'  {last_name} {first_name}: 子供なし')
                    skipped_count += 1
                    continue

                for student in students:
                    # 既存の社割をチェック
                    existing = StudentDiscount.objects.filter(
                        student=student,
                        discount_name__contains='社割',
                        is_active=True
                    ).exists()

                    if existing:
                        self.stdout.write(f'  {student.last_name} {student.first_name}: 既に社割あり')
                        skipped_count += 1
                        continue

                    if dry_run:
                        self.stdout.write(f'  [DRY RUN] {student.last_name} {student.first_name} に社割を作成予定')
                        created_count += 1
                    else:
                        # StudentDiscountを作成
                        # discount_amount が -50 なら 50% 割引
                        unit = 'percent' if discount_unit == '%' or not discount_unit else 'yen'
                        amount = discount_amount  # 既にマイナス値

                        StudentDiscount.objects.create(
                            tenant_ref=tenant,
                            student=student,
                            guardian=guardian,
                            discount_name='社割',
                            amount=amount,
                            discount_unit=unit,
                            is_recurring=True,
                            is_auto=True,
                            end_condition='monthly',
                            is_active=True,
                            notes=f'社員: {last_name} {first_name} ({emp_no})'
                        )
                        self.stdout.write(f'  {student.last_name} {student.first_name}: 社割作成 ({amount}{unit})')
                        created_count += 1

            except Guardian.DoesNotExist:
                errors.append(f'{emp_no}: 保護者ID {guardian_id} が見つかりません')
            except Exception as e:
                errors.append(f'{emp_no}: {str(e)}')

        if dry_run:
            self.stdout.write(self.style.WARNING(f'[DRY RUN] 作成予定: {created_count}件'))
        else:
            self.stdout.write(self.style.SUCCESS(f'作成完了: {created_count}件'))

        self.stdout.write(f'スキップ: {skipped_count}件')

        if errors:
            self.stdout.write(self.style.WARNING(f'エラー: {len(errors)}件'))
            for error in errors[:10]:
                self.stdout.write(f'  - {error}')
