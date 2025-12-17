"""
教室（ルーム）データインポートスクリプト
使用方法: python scripts/import_classrooms.py <xlsx_path>
"""
import sys
import os
import django
import openpyxl
import re

# Django設定
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.schools.models import School, Classroom
from apps.tenants.models import Tenant


def extract_floor(description):
    """説明から階数を抽出"""
    if not description:
        return ''
    match = re.search(r'([0-9０-９]+)\s*[FＦ階]', description)
    if match:
        floor = match.group(1)
        # 全角を半角に
        floor = floor.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
        return f'{floor}F'
    return ''


def import_classrooms(xlsx_path):
    """Excelから教室データをインポート"""

    # アンイングリッシュグループテナント取得
    tenant = Tenant.objects.filter(tenant_code='100000').first()
    if not tenant:
        print("エラー: アンイングリッシュグループテナントが見つかりません")
        sys.exit(1)
    tenant_id = tenant.id
    print(f"テナント: {tenant.tenant_name} ({tenant_id})")

    # 校舎マッピング作成
    school_map = {}
    for s in School.objects.filter(tenant_id=tenant_id):
        school_map[s.school_code] = s
    print(f"校舎マッピング: {len(school_map)} 件")

    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb['③T11_ルーム情報']

    imported = 0
    updated = 0
    skipped = 0
    errors = []

    for row_num, row in enumerate(ws.iter_rows(min_row=2), start=2):
        try:
            school_code = str(row[1].value).strip() if row[1].value else ''
            school_name = str(row[2].value).strip() if row[2].value else ''
            room_name = str(row[3].value).strip() if row[3].value else ''
            capacity = row[4].value
            description = str(row[5].value).strip() if row[5].value else ''

            if not school_code or not room_name:
                continue

            # 校舎取得
            school = school_map.get(school_code)
            if not school:
                skipped += 1
                continue

            # 教室コード生成（校舎コード + ルーム名）
            classroom_code = f"{school_code}_{room_name}"

            # 既存チェック
            existing = Classroom.objects.filter(
                school=school,
                classroom_code=classroom_code
            ).first()

            # 階数抽出
            floor = extract_floor(description)

            # 席数
            try:
                capacity_int = int(capacity) if capacity else 1
            except (ValueError, TypeError):
                capacity_int = 1

            data = {
                'tenant_id': tenant_id,
                'school': school,
                'classroom_code': classroom_code,
                'classroom_name': room_name,
                'capacity': capacity_int,
                'floor': floor,
                'room_type': '',
                'is_active': True,
            }

            if existing:
                for key, value in data.items():
                    if key != 'school':  # ForeignKeyは更新しない
                        setattr(existing, key, value)
                existing.save()
                updated += 1
            else:
                Classroom.objects.create(**data)
                imported += 1

            if (imported + updated) % 50 == 0:
                print(f"  処理中... {imported + updated} 件")

        except Exception as e:
            errors.append(f"行 {row_num}: {school_code}/{room_name} - {str(e)}")
            continue

    return imported, updated, skipped, errors


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python scripts/import_classrooms.py <xlsx_path>")
        sys.exit(1)

    xlsx_path = sys.argv[1]

    if not os.path.exists(xlsx_path):
        print(f"エラー: ファイルが見つかりません: {xlsx_path}")
        sys.exit(1)

    print(f"インポート開始: {xlsx_path}")
    print("-" * 50)

    imported, updated, skipped, errors = import_classrooms(xlsx_path)

    print("-" * 50)
    print(f"完了!")
    print(f"  新規作成: {imported} 件")
    print(f"  更新: {updated} 件")
    print(f"  スキップ: {skipped} 件")

    if errors:
        print(f"  エラー: {len(errors)} 件")
        for error in errors[:10]:
            print(f"    - {error}")
