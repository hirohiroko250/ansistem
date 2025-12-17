"""
コース作成スクリプト（T3から契約IDをコースとして作成）
使用方法: docker compose run --rm backend python scripts/import_courses.py <csv_path>
"""
import sys
import os
import django
import csv
from collections import defaultdict

# Django設定
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.contracts.models import Course, CourseItem, Product
from apps.schools.models import Brand
from apps.tenants.models import Tenant


# サクセス系ブランド（TE・RA・COテナント）
SUCCESS_BRANDS = {
    'AES', 'AGS', 'BMS', 'FES', 'GOK', 'MPS', 'MWS', 'PRS',
    'SCC', 'SEL', 'SFE', 'SFJ', 'SHI', 'SHS', 'SJJ', 'SJU',
    'SKC', 'SKK', 'SOS', 'SUC', 'SHO', 'SEK',
}


def is_success_brand(brand_code, brand_name):
    """サクセス系ブランドかどうか判定"""
    if brand_code in SUCCESS_BRANDS:
        return True
    if brand_name and 'サクセス' in brand_name:
        return True
    return False


def import_courses(csv_path):
    """コースを作成し商品を紐付け"""

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
        key = (str(b.tenant_id), b.brand_code)
        brand_map[key] = b

    # 商品マップ（請求IDで検索用）
    product_map = {}
    for p in Product.objects.all():
        key = (str(p.tenant_id), p.product_code)
        product_map[key] = p
        product_map[p.product_code] = p

    print(f"ブランドマップ: {len(brand_map)} 件")
    print(f"商品マップ: {len(product_map)} 件")

    # CSVを読み込んで契約IDごとにグルーピング
    contracts = defaultdict(list)

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            contract_id = row['契約ID']
            contracts[contract_id].append(row)

    print(f"契約ID（コース）数: {len(contracts)}")

    imported_courses = 0
    imported_items = 0
    updated_courses = 0
    errors = []

    for contract_id, rows in contracts.items():
        try:
            # 最初の行からコース情報を取得
            first_row = rows[0]

            brand_code = first_row.get('契約ブランド記号', '').strip()
            brand_name = first_row.get('契約ブランド名', '').strip()
            contract_name = first_row.get('契約名', '').strip()
            target_grade = first_row.get('対象学年', '').strip()

            # テナント決定
            if is_success_brand(brand_code, brand_name):
                tenant_id = teraco_tenant.id
            else:
                tenant_id = an_tenant.id

            # ブランド取得
            brand = brand_map.get(brand_code)

            # コース名を決定（100文字以内に制限）
            course_name = f"{brand_name} {contract_name}" if brand_name else contract_name
            if len(course_name) > 100:
                course_name = course_name[:97] + "..."

            # 既存コースチェック
            existing_course = Course.objects.filter(
                tenant_id=tenant_id,
                course_code=contract_id
            ).first()

            if existing_course:
                course = existing_course
                updated_courses += 1
            else:
                course = Course.objects.create(
                    tenant_id=tenant_id,
                    course_code=contract_id,
                    course_name=course_name,
                    brand=brand,
                    description=f"対象学年: {target_grade}" if target_grade else '',
                    is_active=True,
                )
                imported_courses += 1

            # 商品を紐付け
            for row in rows:
                billing_id = row.get('請求ID', '').strip()
                billing_no = row.get('請求番号', '0')

                if not billing_id:
                    continue

                # 商品を探す
                product = product_map.get((str(tenant_id), billing_id)) or product_map.get(billing_id)

                if not product:
                    continue

                # 既存チェック
                existing_item = CourseItem.objects.filter(
                    course=course,
                    product=product
                ).first()

                if not existing_item:
                    try:
                        sort_order = int(billing_no) if billing_no else 0
                    except:
                        sort_order = 0

                    CourseItem.objects.create(
                        tenant_id=tenant_id,
                        course=course,
                        product=product,
                        sort_order=sort_order,
                        is_active=True,
                    )
                    imported_items += 1

            if (imported_courses + updated_courses) % 500 == 0:
                print(f"  処理中... コース {imported_courses + updated_courses} 件, 商品紐付け {imported_items} 件")

        except Exception as e:
            errors.append(f"{contract_id}: {str(e)}")
            continue

    return imported_courses, updated_courses, imported_items, errors


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python scripts/import_courses.py <csv_path>")
        sys.exit(1)

    csv_path = sys.argv[1]

    if not os.path.exists(csv_path):
        print(f"エラー: ファイルが見つかりません: {csv_path}")
        sys.exit(1)

    print(f"インポート開始: {csv_path}")
    print("-" * 50)

    imported_courses, updated_courses, imported_items, errors = import_courses(csv_path)

    print("-" * 50)
    print(f"完了!")
    print(f"  新規コース: {imported_courses} 件")
    print(f"  更新コース: {updated_courses} 件")
    print(f"  商品紐付け: {imported_items} 件")

    if errors:
        print(f"  エラー: {len(errors)} 件")
        for error in errors[:10]:
            print(f"    - {error}")
        if len(errors) > 10:
            print(f"    ... 他 {len(errors) - 10} 件")
