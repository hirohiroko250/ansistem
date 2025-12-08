#!/usr/bin/env python
"""
T51_パック組み合わせ情報.xlsx からPack/PackCourseを生成

構造:
- パック契約ID → Pack
- 基本契約ID_1〜4 → PackCourse（Courseへの参照）
"""
import os
import sys
import django

sys.path.insert(0, '/Users/hirosesuzu/Desktop/アンシステム/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import pandas as pd
from apps.contracts.models import Course, Pack, PackCourse, Product
from apps.schools.models import Brand
from apps.tenants.models import Tenant


EXCEL_PATH = '/Users/hirosesuzu/Desktop/アンシステム/Claude-Code-Communication/instructions/おざ/T51_パック組み合わせ情報.xlsx'


def get_tenant():
    return Tenant.objects.get(tenant_code='OZA')


def get_brand_from_code(code, tenant):
    """コードからブランドを推測（プレフィックスから）"""
    if not code:
        return None

    # コードの最初の部分からブランドコードを抽出
    # 例: 24AEC_1000007 → AEC
    parts = code.split('_')
    if len(parts) >= 2:
        prefix = parts[0]
        # 年度を除去（24AEC → AEC）
        if len(prefix) > 2 and prefix[:2].isdigit():
            brand_code = prefix[2:]
            brand = Brand.objects.filter(tenant_id=tenant.id, brand_code=brand_code).first()
            if brand:
                return brand
    return None


def generate_pack_name(pack_code, course_codes, tenant):
    """パック名を生成（含まれるコース名から）"""
    course_names = []
    for code in course_codes:
        if code:
            course = Course.objects.filter(tenant_id=tenant.id, course_code=code).first()
            if course:
                # コース名を短くする
                name = course.course_name
                # 長すぎる場合は最初の部分だけ
                if len(name) > 30:
                    name = name[:30] + "..."
                course_names.append(name)

    if course_names:
        return " + ".join(course_names[:2])  # 最初の2つだけ
    return pack_code


def import_packs():
    print("=" * 60)
    print("Pack/PackCourse インポート")
    print("=" * 60)

    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name}")

    # 既存データ削除
    print("\n既存データ削除中...")
    PackCourse.objects.filter(tenant_id=tenant.id).delete()
    Pack.objects.filter(tenant_id=tenant.id).delete()
    print("削除完了")

    # Excel読み込み
    print(f"\nExcel読み込み中: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH)
    print(f"全{len(df)}行")

    # 統計
    pack_created = 0
    pack_course_created = 0
    errors = 0
    missing_courses = set()

    for idx, row in df.iterrows():
        try:
            pack_code = str(row['パック契約ID']).strip()
            if not pack_code or pack_code == 'nan':
                continue

            # 含まれるコースコードを取得
            course_codes = []
            for col in ['基本契約ID_1', '基本契約ID_2', '基本契約ID_3', '基本契約ID_4']:
                code = row.get(col)
                if pd.notna(code):
                    course_codes.append(str(code).strip())

            if not course_codes:
                continue

            # ブランドを最初のコースから取得
            brand = get_brand_from_code(course_codes[0], tenant)

            # パック名を生成
            pack_name = generate_pack_name(pack_code, course_codes, tenant)

            # Pack作成
            pack, created = Pack.objects.update_or_create(
                tenant_id=tenant.id,
                pack_code=pack_code,
                defaults={
                    'pack_name': pack_name,
                    'brand': brand,
                    'is_active': True,
                }
            )

            if created:
                pack_created += 1

            # PackCourse作成
            for sort_order, code in enumerate(course_codes, start=1):
                course = Course.objects.filter(tenant_id=tenant.id, course_code=code).first()
                if course:
                    pack_course, pc_created = PackCourse.objects.update_or_create(
                        pack=pack,
                        course=course,
                        defaults={
                            'tenant_id': tenant.id,
                            'sort_order': sort_order,
                            'is_active': True,
                        }
                    )
                    if pc_created:
                        pack_course_created += 1
                else:
                    missing_courses.add(code)

        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"エラー (行{idx}): {e}")

    print(f"\n=== 結果 ===")
    print(f"Pack作成: {pack_created}")
    print(f"PackCourse作成: {pack_course_created}")
    print(f"エラー: {errors}")

    if missing_courses:
        print(f"\n存在しないCourse: {len(missing_courses)}件")
        if len(missing_courses) <= 20:
            for code in sorted(missing_courses):
                print(f"  - {code}")

    # 確認
    print(f"\n=== 確認 ===")
    print(f"Pack総数: {Pack.objects.filter(tenant_id=tenant.id).count()}")
    print(f"PackCourse総数: {PackCourse.objects.filter(tenant_id=tenant.id).count()}")

    # サンプル表示
    print(f"\n=== サンプル（最初の3パック）===")
    for pack in Pack.objects.filter(tenant_id=tenant.id)[:3]:
        print(f"\n【{pack.pack_code}】{pack.pack_name}")
        print(f"  ブランド: {pack.brand.brand_name if pack.brand else 'なし'}")
        for pc in pack.pack_courses.all().order_by('sort_order'):
            print(f"  └ {pc.sort_order}: {pc.course.course_name}")


if __name__ == '__main__':
    import_packs()
