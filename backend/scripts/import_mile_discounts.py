#!/usr/bin/env python
"""
ProductテーブルのmileフィールドからDiscountテーブルにマイル割引レコードを作成するスクリプト

使用方法:
    python manage.py shell < scripts/import_mile_discounts.py

本番環境:
    docker exec -i oza_backend python manage.py shell < scripts/import_mile_discounts.py

処理内容:
    - mile > 0 のProductを検索
    - 各Productに対してマイル割引のDiscountレコードを作成
    - discount_code: MILE_{product_code}
    - discount_type: mile
    - calculation_type: fixed (固定金額)
    - value: mileの値
"""
import os
import sys
import django

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from decimal import Decimal
from apps.contracts.models import Product, Discount
from apps.tenants.models import Tenant


def main():
    print("=== マイル割引 インポート開始 ===")

    # テナント取得
    tenant = Tenant.objects.first()
    if not tenant:
        print("エラー: テナントが見つかりません")
        return
    print(f"テナント: {tenant.name} ({tenant.id})")

    # mile > 0 のProductを取得
    products_with_mile = Product.objects.filter(tenant=tenant, mile__gt=0)
    print(f"マイル > 0 のProduct数: {products_with_mile.count()}")

    created_count = 0
    updated_count = 0
    error_count = 0

    for product in products_with_mile:
        try:
            discount_code = f"MILE_{product.product_code}"
            discount_name = f"マイル割引 - {product.product_name}"

            # 100文字以内に収める
            if len(discount_name) > 100:
                discount_name = discount_name[:97] + "..."

            # discount_codeも20文字制限
            if len(discount_code) > 20:
                discount_code = discount_code[:20]

            discount, created = Discount.objects.update_or_create(
                tenant_id=tenant.id,
                discount_code=discount_code,
                defaults={
                    'discount_name': discount_name,
                    'discount_type': 'mile',
                    'calculation_type': 'fixed',
                    'value': product.mile,
                    'is_active': True,
                }
            )

            if created:
                created_count += 1
                if created_count <= 20:
                    print(f"  作成: {discount_code} = {product.mile}マイル ({product.product_name})")
            else:
                updated_count += 1
                if updated_count <= 10:
                    print(f"  更新: {discount_code} = {product.mile}マイル")

        except Exception as e:
            error_count += 1
            if error_count <= 5:
                print(f"  エラー ({product.product_code}): {e}")

    print(f"\n=== 完了 ===")
    print(f"新規作成: {created_count}")
    print(f"更新: {updated_count}")
    print(f"エラー: {error_count}")

    # 確認
    mile_discounts = Discount.objects.filter(tenant=tenant, discount_type='mile')
    print(f"\nマイル割引 Discount数: {mile_discounts.count()}")
    for d in mile_discounts[:10]:
        print(f"  {d.discount_code}: {d.discount_name} = {d.value}")


if __name__ == '__main__':
    main()
