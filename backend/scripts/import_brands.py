"""
ブランドデータインポートスクリプト
使用方法: docker compose run --rm backend python scripts/import_brands.py <xlsx_path>
"""
import sys
import os
import django
import openpyxl

# Django設定
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.schools.models import Brand
from apps.tenants.models import Tenant


def import_brands(xlsx_path):
    """Excelからブランドデータをインポート"""

    # アンイングリッシュグループテナント取得
    tenant = Tenant.objects.filter(tenant_code='100000').first()
    if not tenant:
        print("エラー: アンイングリッシュグループテナントが見つかりません")
        sys.exit(1)
    tenant_id = tenant.id
    print(f"テナント: {tenant.tenant_name} ({tenant_id})")

    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb['T12_ブランド情報_CSV書き出し用DATAもと']

    imported = 0
    updated = 0
    errors = []

    for row_num, row in enumerate(ws.iter_rows(min_row=2), start=2):
        try:
            # データ取得
            oza_id = row[0].value
            display_flag = row[1].value
            brand_code = str(row[2].value).strip() if row[2].value else ''
            brand_name = str(row[3].value).strip() if row[3].value else ''
            brand_name_short = str(row[4].value).strip() if row[4].value else ''
            subject = str(row[5].value).strip() if row[5].value else ''
            class_brand_id = str(row[6].value).strip() if row[6].value else ''
            class_brand_name = str(row[7].value).strip() if row[7].value else ''

            if not brand_code or not brand_name:
                continue

            # 既存チェック（brand_codeで）
            existing = Brand.objects.filter(
                tenant_id=tenant_id,
                brand_code=brand_code
            ).first()

            # データ準備
            data = {
                'tenant_id': tenant_id,
                'brand_code': brand_code,
                'brand_name': brand_name,
                'brand_name_short': brand_name_short,
                'brand_type': subject,
                'description': f'ClassブランドID: {class_brand_id}' if class_brand_id else '',
                'sort_order': int(display_flag) if display_flag else 0,
                'is_active': True,
            }

            if existing:
                # 更新
                for key, value in data.items():
                    setattr(existing, key, value)
                existing.save()
                updated += 1
            else:
                # 新規作成
                Brand.objects.create(**data)
                imported += 1

            if (imported + updated) % 10 == 0:
                print(f"  処理中... {imported + updated} 件")

        except Exception as e:
            errors.append(f"行 {row_num}: {brand_code} - {str(e)}")
            continue

    return imported, updated, errors


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python scripts/import_brands.py <xlsx_path>")
        sys.exit(1)

    xlsx_path = sys.argv[1]

    if not os.path.exists(xlsx_path):
        print(f"エラー: ファイルが見つかりません: {xlsx_path}")
        sys.exit(1)

    print(f"インポート開始: {xlsx_path}")
    print("-" * 50)

    imported, updated, errors = import_brands(xlsx_path)

    print("-" * 50)
    print(f"完了!")
    print(f"  新規作成: {imported} 件")
    print(f"  更新: {updated} 件")

    if errors:
        print(f"  エラー: {len(errors)} 件")
        for error in errors[:10]:
            print(f"    - {error}")
        if len(errors) > 10:
            print(f"    ... 他 {len(errors) - 10} 件")
