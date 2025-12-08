#!/usr/bin/env python
"""
ブランドCSVからデータを更新
"""
import os
import sys
import django

sys.path.insert(0, '/Users/hirosesuzu/Desktop/アンシステム/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import csv
from apps.schools.models import Brand
from apps.tenants.models import Tenant


CSV_PATH = '/Users/hirosesuzu/Downloads/ブランド 2025年12月03 (1).csv'


def get_tenant():
    return Tenant.objects.get(tenant_code='OZA')


def import_brands():
    print("=" * 60)
    print("ブランドCSVインポート")
    print("=" * 60)

    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name}")

    # 現在のブランド数
    current_count = Brand.objects.filter(tenant_id=tenant.id).count()
    print(f"現在のブランド数: {current_count}")

    # CSVを読み込み
    created = 0
    updated = 0
    errors = 0

    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                brand_code = row.get('ブランドコード', '').strip()
                if not brand_code:
                    continue

                # is_active: CSVの「有効」列は連番なので、空でなければ有効とする
                is_active_val = row.get('有効', '').strip()
                is_active = bool(is_active_val)  # 値があれば有効

                # sort_order の変換
                sort_order = int(row.get('並び順', '0').strip() or '0')

                brand, is_created = Brand.objects.update_or_create(
                    tenant_id=tenant.id,
                    brand_code=brand_code,
                    defaults={
                        'brand_name': row.get('ブランド名', '').strip(),
                        'brand_name_short': row.get('ブランド略称', '').strip(),
                        'brand_type': row.get('ブランドタイプ', '').strip(),
                        'description': row.get('説明', '').strip(),
                        'logo_url': row.get('ロゴURL', '').strip(),
                        'color_primary': row.get('テーマカラー', '').strip(),
                        'sort_order': sort_order,
                        'is_active': is_active,
                    }
                )

                if is_created:
                    created += 1
                else:
                    updated += 1

            except Exception as e:
                errors += 1
                print(f"エラー ({row.get('ブランドコード', 'unknown')}): {e}")

    print(f"\n=== 結果 ===")
    print(f"作成: {created}")
    print(f"更新: {updated}")
    print(f"エラー: {errors}")

    # 確認
    final_count = Brand.objects.filter(tenant_id=tenant.id).count()
    print(f"\n=== 確認 ===")
    print(f"ブランド総数: {final_count}")

    # サンプル表示
    print(f"\n=== サンプル（最初の10件）===")
    for brand in Brand.objects.filter(tenant_id=tenant.id).order_by('sort_order')[:10]:
        status = "有効" if brand.is_active else "無効"
        print(f"  {brand.sort_order:2d}. [{brand.brand_code}] {brand.brand_name} ({brand.brand_type}) - {status}")


if __name__ == '__main__':
    import_brands()
