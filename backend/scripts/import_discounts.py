"""
割引データ（T6）インポートスクリプト
使用方法: docker compose run --rm backend python scripts/import_discounts.py <csv_path>
"""
import sys
import os
import django
import csv
from decimal import Decimal
from datetime import datetime

# Django設定
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.contracts.models import StudentDiscount
from apps.students.models import Student, Guardian
from apps.tenants.models import Tenant


def parse_date(value):
    """日付パース"""
    if not value or value == '':
        return None
    try:
        return datetime.strptime(value, '%Y/%m/%d').date()
    except:
        try:
            return datetime.strptime(value[:10], '%Y-%m-%d').date()
        except:
            return None


def parse_decimal(value):
    """Decimalパース"""
    if not value or value == '':
        return Decimal('0')
    try:
        return Decimal(str(value).replace(',', ''))
    except:
        return Decimal('0')


def import_discounts(csv_path):
    """割引データをインポート"""

    # テナント取得
    tenant = Tenant.objects.filter(tenant_code='100000').first()
    if not tenant:
        print("エラー: テナントが見つかりません")
        sys.exit(1)
    tenant_id = tenant.id
    print(f"テナント: {tenant.tenant_name} ({tenant_id})")

    # 保護者マップ（old_id → Guardian）
    guardian_map = {}
    for g in Guardian.objects.all():
        if g.old_id:
            guardian_map[str(g.old_id)] = g
    print(f"保護者マップ: {len(guardian_map)} 件")

    # 生徒マップ（old_id → Student）
    student_map = {}
    for s in Student.objects.all():
        if s.old_id:
            student_map[str(s.old_id)] = s
    print(f"生徒マップ: {len(student_map)} 件")

    imported = 0
    updated = 0
    skipped = 0
    errors = []

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):
            try:
                # 割引ID
                discount_id = row.get('割引ID', '').strip()
                if not discount_id:
                    skipped += 1
                    continue

                # 有無チェック（0なら無効）
                is_active = row.get('有無', '1').strip()
                if is_active == '0':
                    skipped += 1
                    continue

                # 対象タイプ（1=保護者, 2=生徒）
                target_type = row.get('対象', '').strip()

                # 保護者・生徒を取得
                guardian_old_id = row.get('保護者ID', '').strip()
                student_old_id = row.get('生徒ID', '').strip()

                guardian = guardian_map.get(guardian_old_id) if guardian_old_id else None
                student = student_map.get(student_old_id) if student_old_id else None

                # 保護者も生徒もなければスキップ
                if not guardian and not student:
                    skipped += 1
                    continue

                # 割引名
                discount_name = row.get('顧客表記用割引名（契約、請求IDの割引は、そのすぐ下に表記）', '').strip()
                if not discount_name:
                    discount_name = '割引'

                # 金額
                amount = parse_decimal(row.get('金額', '0'))

                # 割引単位
                discount_unit_raw = row.get('割引単位', '円').strip()
                if discount_unit_raw == '%':
                    discount_unit = StudentDiscount.DiscountUnit.PERCENT
                else:
                    discount_unit = StudentDiscount.DiscountUnit.YEN

                # 開始日・終了日
                start_date = parse_date(row.get('開始日', ''))
                end_date = parse_date(row.get('終了日', ''))

                # 繰り返し（1=なし, 2=あり）
                is_recurring_raw = row.get('繰り返し', '1').strip()
                is_recurring = is_recurring_raw == '2'

                # 自動割引
                is_auto_raw = row.get('自動割引', '0').strip()
                is_auto = is_auto_raw == '1'

                # 終了条件
                end_condition_raw = row.get('終了条件', '１回だけ').strip()
                if end_condition_raw == '毎月':
                    end_condition = StudentDiscount.EndCondition.MONTHLY
                elif end_condition_raw == '終了日まで':
                    end_condition = StudentDiscount.EndCondition.UNTIL_END_DATE
                else:
                    end_condition = StudentDiscount.EndCondition.ONCE

                # 既存チェック
                existing = StudentDiscount.objects.filter(
                    tenant_id=tenant_id,
                    old_id=discount_id
                ).first()

                data = {
                    'tenant_id': tenant_id,
                    'old_id': discount_id,
                    'guardian': guardian,
                    'student': student,
                    'discount_name': discount_name,
                    'amount': amount,
                    'discount_unit': discount_unit,
                    'start_date': start_date,
                    'end_date': end_date,
                    'is_recurring': is_recurring,
                    'is_auto': is_auto,
                    'end_condition': end_condition,
                }

                if existing:
                    for key, value in data.items():
                        setattr(existing, key, value)
                    existing.save()
                    updated += 1
                else:
                    StudentDiscount.objects.create(**data)
                    imported += 1

                if (imported + updated) % 500 == 0:
                    print(f"  処理中... {imported + updated} 件")

            except Exception as e:
                errors.append(f"行 {row_num}: {discount_id} - {str(e)}")
                continue

    return imported, updated, skipped, errors


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python scripts/import_discounts.py <csv_path>")
        sys.exit(1)

    csv_path = sys.argv[1]

    if not os.path.exists(csv_path):
        print(f"エラー: ファイルが見つかりません: {csv_path}")
        sys.exit(1)

    print(f"インポート開始: {csv_path}")
    print("-" * 50)

    imported, updated, skipped, errors = import_discounts(csv_path)

    print("-" * 50)
    print(f"完了!")
    print(f"  新規作成: {imported} 件")
    print(f"  更新: {updated} 件")
    print(f"  スキップ: {skipped} 件")

    if errors:
        print(f"  エラー: {len(errors)} 件")
        for error in errors[:20]:
            print(f"    - {error}")
        if len(errors) > 20:
            print(f"    ... 他 {len(errors) - 20} 件")
