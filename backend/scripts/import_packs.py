"""
パック組み合わせデータインポートスクリプト (T51)
使用方法: docker compose run --rm backend python scripts/import_packs.py <xlsx_path>
"""
import sys
import os
import django
import openpyxl

# Django設定
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.contracts.models import Pack, PackCourse, Course
from apps.schools.models import Brand
from apps.tenants.models import Tenant


# サクセス系ブランド
SUCCESS_BRANDS = {
    'AES', 'AGS', 'BMS', 'FES', 'GOK', 'MPS', 'MWS', 'PRS',
    'SCC', 'SEL', 'SFE', 'SFJ', 'SHI', 'SHS', 'SJJ', 'SJU',
    'SKC', 'SKK', 'SOS', 'SUC', 'SHO', 'SEK',
}


def get_brand_from_code(contract_id):
    """契約IDからブランドコードを抽出"""
    # 24AEC_1000007 -> AEC
    if not contract_id or '_' not in contract_id:
        return None
    parts = contract_id.split('_')
    if len(parts) >= 2:
        # 24AEC -> AEC (先頭の数字2文字を除去)
        brand_part = parts[0]
        if len(brand_part) > 2 and brand_part[:2].isdigit():
            return brand_part[2:]
    return None


def is_success_brand(brand_code):
    """サクセス系ブランドかどうか"""
    if not brand_code:
        return False
    return brand_code in SUCCESS_BRANDS


def import_packs(xlsx_path):
    """パックをインポート"""

    # テナント取得
    an_tenant = Tenant.objects.filter(tenant_code='100000').first()
    teraco_tenant = Tenant.objects.filter(tenant_code='101615').first()

    if not an_tenant or not teraco_tenant:
        print("エラー: テナントが見つかりません")
        sys.exit(1)

    print(f"アンイングリッシュグループ: {an_tenant.id}")
    print(f"株式会社TE・RA・CO: {teraco_tenant.id}")

    # ブランドマップ
    brand_map = {}
    for b in Brand.objects.all():
        brand_map[b.brand_code] = b

    # コースマップ
    course_map = {}
    for c in Course.objects.all():
        key = (str(c.tenant_id), c.course_code)
        course_map[key] = c
        course_map[c.course_code] = c

    print(f"ブランドマップ: {len(brand_map)} 件")
    print(f"コースマップ: {len(course_map)} 件")

    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb['T51_パック組み合わせ情報']

    imported_packs = 0
    updated_packs = 0
    imported_pack_courses = 0
    errors = []

    for row_num, row in enumerate(ws.iter_rows(min_row=2), start=2):
        try:
            pack_contract_id = str(row[0].value).strip() if row[0].value else ''
            if not pack_contract_id:
                continue

            # パック用のブランドを取得
            brand_code = get_brand_from_code(pack_contract_id)
            brand = brand_map.get(brand_code)

            # テナント決定
            if is_success_brand(brand_code):
                tenant_id = teraco_tenant.id
            else:
                tenant_id = an_tenant.id

            # 含まれるコースを取得
            course_ids = []
            for i in range(1, 5):  # 基本契約ID_1〜4
                if row[i].value:
                    course_ids.append(str(row[i].value).strip())

            if not course_ids:
                continue

            # パック名を生成（含まれるコースから）
            course_names = []
            for cid in course_ids:
                c = course_map.get((str(tenant_id), cid)) or course_map.get(cid)
                if c:
                    course_names.append(c.course_name[:30])

            pack_name = ' + '.join(course_names) if course_names else pack_contract_id
            if len(pack_name) > 100:
                pack_name = pack_name[:97] + '...'

            # パックを作成または更新
            existing_pack = Pack.objects.filter(
                tenant_id=tenant_id,
                pack_code=pack_contract_id
            ).first()

            if existing_pack:
                pack = existing_pack
                pack.pack_name = pack_name
                pack.brand = brand
                pack.save()
                updated_packs += 1
            else:
                pack = Pack.objects.create(
                    tenant_id=tenant_id,
                    pack_code=pack_contract_id,
                    pack_name=pack_name,
                    brand=brand,
                    discount_type='none',
                    is_active=True,
                )
                imported_packs += 1

            # パック構成（PackCourse）を作成
            for sort_order, course_id in enumerate(course_ids, start=1):
                course = course_map.get((str(tenant_id), course_id)) or course_map.get(course_id)
                if not course:
                    continue

                # 既存チェック
                existing_pc = PackCourse.objects.filter(
                    pack=pack,
                    course=course
                ).first()

                if not existing_pc:
                    PackCourse.objects.create(
                        tenant_id=tenant_id,
                        pack=pack,
                        course=course,
                        sort_order=sort_order,
                        is_active=True,
                    )
                    imported_pack_courses += 1

            if (imported_packs + updated_packs) % 500 == 0:
                print(f"  処理中... パック {imported_packs + updated_packs} 件, パック構成 {imported_pack_courses} 件")

        except Exception as e:
            errors.append(f"行 {row_num}: {pack_contract_id} - {str(e)}")
            continue

    return imported_packs, updated_packs, imported_pack_courses, errors


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python scripts/import_packs.py <xlsx_path>")
        sys.exit(1)

    xlsx_path = sys.argv[1]

    if not os.path.exists(xlsx_path):
        print(f"エラー: ファイルが見つかりません: {xlsx_path}")
        sys.exit(1)

    print(f"インポート開始: {xlsx_path}")
    print("-" * 50)

    imported_packs, updated_packs, imported_pack_courses, errors = import_packs(xlsx_path)

    print("-" * 50)
    print(f"完了!")
    print(f"  新規パック: {imported_packs} 件")
    print(f"  更新パック: {updated_packs} 件")
    print(f"  パック構成: {imported_pack_courses} 件")

    if errors:
        print(f"  エラー: {len(errors)} 件")
        for error in errors[:10]:
            print(f"    - {error}")
        if len(errors) > 10:
            print(f"    ... 他 {len(errors) - 10} 件")
