#!/usr/bin/env python
"""
商品コードのプレフィックスからCourseを自動生成し、CourseItemで紐づける

ルール:
- プレフィックス（最後の_以前）が同じ商品をグループ化
- _1 の商品（授業料）からコース名を取得
- _1〜_6 を通常のCourseItemとして登録（毎月/初回）
- _50〜_60 は入会時用なので別途管理（今回はスキップ or 別フラグ）
"""
import os
import sys
import django

sys.path.insert(0, '/Users/hirosesuzu/Desktop/アンシステム/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from collections import defaultdict
from apps.contracts.models import Product, Course, CourseItem
from apps.schools.models import Brand
from apps.tenants.models import Tenant


def get_tenant():
    return Tenant.objects.get(tenant_code='OZA')


def generate_courses():
    print("=" * 60)
    print("Course自動生成")
    print("=" * 60)

    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name}")

    # プレフィックスでグループ化
    prefix_groups = defaultdict(list)
    for product in Product.objects.filter(tenant_id=tenant.id):
        code = product.product_code
        if '_' in code:
            prefix = code.rsplit('_', 1)[0]
            suffix = code.rsplit('_', 1)[1]
            prefix_groups[prefix].append((suffix, product))

    print(f"\n全プレフィックス数: {len(prefix_groups)}")

    # Course生成
    course_created = 0
    course_item_created = 0
    errors = 0

    for prefix, items in prefix_groups.items():
        try:
            # _1 の商品からコース情報を取得
            main_product = None
            for suffix, product in items:
                if suffix == '1':
                    main_product = product
                    break

            if not main_product:
                # _1がない場合はスキップ
                continue

            # コース名を生成（【授業料】を除去）
            course_name = main_product.product_name
            if '【授業料】' in course_name:
                course_name = course_name.replace('【授業料】', ' ')
            course_name = course_name.strip()

            # ブランドコードを取得
            brand = main_product.brand

            # Course作成
            course, created = Course.objects.update_or_create(
                tenant_id=tenant.id,
                course_code=prefix,
                defaults={
                    'course_name': course_name,
                    'brand': brand,
                    'is_active': True,
                }
            )

            if created:
                course_created += 1

            # CourseItem作成（_1〜_9のみ、_50以上は入会時用なのでスキップ）
            for suffix, product in items:
                try:
                    suffix_num = int(suffix)
                except ValueError:
                    continue

                # _1〜_9 のみ通常のコース構成として登録
                if 1 <= suffix_num <= 9:
                    course_item, ci_created = CourseItem.objects.update_or_create(
                        course=course,
                        product=product,
                        defaults={
                            'tenant_id': tenant.id,
                            'quantity': 1,
                            'sort_order': suffix_num,
                            'is_active': True,
                        }
                    )
                    if ci_created:
                        course_item_created += 1

        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"エラー ({prefix}): {e}")

    print(f"\n=== 結果 ===")
    print(f"Course作成: {course_created}")
    print(f"CourseItem作成: {course_item_created}")
    print(f"エラー: {errors}")

    # 確認
    print(f"\n=== 確認 ===")
    print(f"Course総数: {Course.objects.filter(tenant_id=tenant.id).count()}")
    print(f"CourseItem総数: {CourseItem.objects.filter(tenant_id=tenant.id).count()}")

    # サンプル表示
    print(f"\n=== サンプル（最初の3コース）===")
    for course in Course.objects.filter(tenant_id=tenant.id)[:3]:
        print(f"\n【{course.course_code}】{course.course_name}")
        print(f"  ブランド: {course.brand.brand_name if course.brand else 'なし'}")
        for item in course.course_items.all().order_by('sort_order'):
            print(f"  └ {item.sort_order}: {item.product.product_name} ({item.product.item_type}) ¥{item.product.base_price}")


if __name__ == '__main__':
    generate_courses()
