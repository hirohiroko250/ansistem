"""
T4（ユーザー契約情報）CSVからStudentItemを作成・更新するスクリプト

既存のStudentItemをold_id（受講ID）で照合し、
- student紐付けを修正
- contract紐付けを作成
- 価格情報を更新（ProductのMonthlyPriceから取得）
"""
import os
import sys
import django

# Djangoのセットアップ
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.contracts.models import Contract, StudentItem, Product
from apps.students.models import Student, Guardian
from apps.schools.models import School, Brand
from apps.tenants.models import Tenant


def get_tenant():
    """テナントを取得"""
    tenant = Tenant.objects.first()
    if not tenant:
        print("テナントが見つかりません")
        sys.exit(1)
    return tenant


def parse_date(date_str):
    """日付を解析"""
    if pd.isna(date_str) or not date_str:
        return None
    try:
        if isinstance(date_str, str):
            return datetime.strptime(date_str.strip(), '%Y/%m/%d').date()
        return date_str
    except:
        return None


def find_brand_by_name(brand_name, brand_map):
    """ブランド名で検索"""
    if pd.isna(brand_name) or not brand_name:
        return None
    brand_name = str(brand_name).strip()
    # 完全一致
    if brand_name in brand_map:
        return brand_map[brand_name]
    # 部分一致
    for name, brand in brand_map.items():
        if brand_name in name or name in brand_name:
            return brand
    return None


def find_school_by_name(school_name, school_map):
    """校舎名で検索"""
    if pd.isna(school_name) or not school_name:
        return None
    school_name = str(school_name).strip()
    if school_name in school_map:
        return school_map[school_name]
    # 部分一致
    for name, school in school_map.items():
        if school_name in name or name in school_name:
            return school
    return None


def get_product_price(product, billing_month, grade_name=None):
    """商品の月額価格を取得"""
    if not product:
        return Decimal('0')

    # まずbase_priceを使用
    price = product.base_price or Decimal('0')

    # MonthlyPriceがあれば使用
    try:
        from apps.pricing.models import MonthlyPrice
        monthly_prices = MonthlyPrice.objects.filter(
            product=product,
            year_month=billing_month
        )
        if monthly_prices.exists():
            mp = monthly_prices.first()
            price = mp.price or price
    except:
        pass

    return price


def import_t4_csv(csv_path, dry_run=True):
    """T4 CSVからStudentItemを作成・更新"""
    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name} ({tenant.id})")
    print(f"CSVファイル: {csv_path}")
    print(f"モード: {'ドライラン' if dry_run else '実行'}")

    # CSVを読み込み
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    print(f"総レコード数: {len(df)}")

    # マッピングを作成
    print("\nマッピングを作成中...")

    # 保護者マップ（old_id -> Guardian）
    guardian_map = {}
    for g in Guardian.objects.filter(tenant_id=tenant.id).exclude(old_id__isnull=True).exclude(old_id=''):
        guardian_map[str(g.old_id)] = g
    print(f"  保護者: {len(guardian_map)}件")

    # 生徒マップ（old_id -> Student）
    student_map = {}
    for s in Student.objects.filter(tenant_id=tenant.id).exclude(old_id__isnull=True).exclude(old_id=''):
        student_map[str(s.old_id)] = s
    print(f"  生徒: {len(student_map)}件")

    # ブランドマップ
    brand_map = {}
    for b in Brand.objects.all():
        brand_map[b.brand_name] = b
    print(f"  ブランド: {len(brand_map)}件")

    # 校舎マップ
    school_map = {}
    for s in School.objects.all():
        school_map[s.school_name] = s
    print(f"  校舎: {len(school_map)}件")

    # 商品マップ（product_name -> Product）
    product_map = {}
    for p in Product.objects.all():
        product_map[p.product_name] = p
        if p.product_code:
            product_map[p.product_code] = p
    print(f"  商品: {len(product_map)}件")

    # 既存のStudentItemマップ（old_id -> StudentItem）
    existing_items = {}
    for si in StudentItem.objects.filter(tenant_id=tenant.id).exclude(old_id=''):
        if si.old_id not in existing_items:
            existing_items[si.old_id] = []
        existing_items[si.old_id].append(si)
    print(f"  既存StudentItem: {len(existing_items)}件（ユニークold_id）")

    # 既存の契約マップ
    contract_map = {}
    for c in Contract.objects.filter(tenant_id=tenant.id).exclude(old_id__isnull=True).exclude(old_id=''):
        contract_map[str(c.old_id)] = c
    print(f"  契約: {len(contract_map)}件")

    # 統計
    stats = {
        'processed': 0,
        'student_items_created': 0,
        'student_items_updated': 0,
        'contracts_created': 0,
        'skipped_no_student': 0,
        'errors': []
    }

    print("\n処理を開始...")

    with transaction.atomic():
        for idx, row in df.iterrows():
            stats['processed'] += 1

            if stats['processed'] % 1000 == 0:
                print(f"  処理中: {stats['processed']}/{len(df)}")

            try:
                # 受講ID（StudentItemのold_idに対応）
                enrollment_id = str(row.get('受講ID', '')).strip()
                if not enrollment_id:
                    continue

                # 生徒を検索
                student_old_id = str(int(row['生徒ID'])) if not pd.isna(row['生徒ID']) else None
                student = student_map.get(student_old_id) if student_old_id else None

                if not student:
                    stats['skipped_no_student'] += 1
                    continue

                # 保護者を検索
                guardian_old_id = str(int(row['保護者ID'])) if not pd.isna(row['保護者ID']) else None
                guardian = guardian_map.get(guardian_old_id) if guardian_old_id else None

                # ブランドを検索
                brand_name = str(row.get('Class用ブランド名', '')).strip() if not pd.isna(row.get('Class用ブランド名')) else None
                brand = find_brand_by_name(brand_name, brand_map)

                # 日付を解析
                start_date = parse_date(row.get('開始日'))
                end_date = parse_date(row.get('終了日'))

                if not start_date:
                    start_date = datetime.now().date()

                # 契約名
                contract_name = str(row.get('契約名', '')).strip() if not pd.isna(row.get('契約名')) else ''

                # 商品を検索
                product = product_map.get(contract_name)
                if not product and contract_name:
                    # 部分一致で検索
                    for pname, p in product_map.items():
                        if contract_name[:20] in pname or pname in contract_name:
                            product = p
                            break

                # 契約を取得または作成
                contract = contract_map.get(enrollment_id)
                if not contract:
                    # 校舎を取得
                    school = None
                    # 社員X列から校舎名を探す（例：千種本部校）
                    for col in ['社員4', '社員5', '社員6', '社員7', '社員8', '社員9', '社員10']:
                        val = str(row.get(col, '')).strip() if not pd.isna(row.get(col)) else ''
                        if val and val.endswith('校'):
                            school = find_school_by_name(val, school_map)
                            if school:
                                break

                    if not school:
                        school = School.objects.filter(is_active=True).first()

                    if not brand:
                        brand = Brand.objects.first()

                    contract = Contract(
                        tenant_id=tenant.id,
                        old_id=enrollment_id,
                        contract_no=enrollment_id,
                        student=student,
                        guardian=guardian or student.guardian,
                        school=school,
                        brand=brand,
                        contract_date=start_date,
                        start_date=start_date,
                        end_date=end_date,
                        status=Contract.Status.ACTIVE if not end_date or end_date > datetime.now().date() else Contract.Status.CANCELLED,
                        notes=contract_name,
                    )

                    if not dry_run:
                        contract.save()

                    contract_map[enrollment_id] = contract
                    stats['contracts_created'] += 1

                # 請求月を計算（開始日から終了日までの各月）
                billing_months = []
                if start_date and end_date:
                    current_date = start_date
                    while current_date <= end_date and current_date <= datetime(2026, 12, 31).date():
                        billing_month = current_date.strftime('%Y-%m')
                        billing_months.append(billing_month)
                        current_date += relativedelta(months=1)
                elif start_date:
                    # 終了日がない場合は開始日の月のみ
                    billing_months.append(start_date.strftime('%Y-%m'))

                # 各請求月についてStudentItemを作成/更新
                for billing_month in billing_months:
                    # 既存のStudentItemを探す
                    existing_list = existing_items.get(enrollment_id, [])
                    existing_si = None
                    for si in existing_list:
                        if si.billing_month == billing_month:
                            existing_si = si
                            break

                    # 価格を取得
                    grade_name = str(row.get('契約学年', '')).strip() if not pd.isna(row.get('契約学年')) else None
                    price = get_product_price(product, billing_month, grade_name)

                    if existing_si:
                        # 既存のStudentItemを更新
                        updated = False
                        if not existing_si.student and student:
                            existing_si.student = student
                            updated = True
                        if not existing_si.contract and contract:
                            existing_si.contract = contract
                            updated = True
                        if existing_si.final_price == 0 and price > 0:
                            existing_si.unit_price = price
                            existing_si.final_price = price
                            updated = True
                        if not existing_si.brand and brand:
                            existing_si.brand = brand
                            updated = True
                        if not existing_si.product and product:
                            existing_si.product = product
                            updated = True

                        if updated:
                            if not dry_run:
                                existing_si.save()
                            stats['student_items_updated'] += 1
                    else:
                        # 新規作成
                        student_item = StudentItem(
                            tenant_id=tenant.id,
                            old_id=enrollment_id,
                            student=student,
                            contract=contract,
                            product=product,
                            brand=brand,
                            billing_month=billing_month,
                            quantity=1,
                            unit_price=price,
                            discount_amount=Decimal('0'),
                            final_price=price,
                            start_date=start_date,
                            notes=contract_name,
                        )

                        if not dry_run:
                            student_item.save()

                        stats['student_items_created'] += 1

                        # キャッシュに追加
                        if enrollment_id not in existing_items:
                            existing_items[enrollment_id] = []
                        existing_items[enrollment_id].append(student_item)

            except Exception as e:
                stats['errors'].append(f"Row {idx}: {str(e)}")
                import traceback
                if len(stats['errors']) < 5:
                    traceback.print_exc()

        if dry_run:
            print("\n=== ドライラン結果 ===")
            transaction.set_rollback(True)
        else:
            print("\n=== 実行結果 ===")

    print(f"処理行数: {stats['processed']}")
    print(f"契約作成: {stats['contracts_created']}")
    print(f"StudentItem作成: {stats['student_items_created']}")
    print(f"StudentItem更新: {stats['student_items_updated']}")
    print(f"スキップ（生徒なし）: {stats['skipped_no_student']}")
    print(f"エラー: {len(stats['errors'])}")

    if stats['errors']:
        print("\n最初の10件のエラー:")
        for err in stats['errors'][:10]:
            print(f"  - {err}")

    return stats


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='T4 CSVからStudentItemをインポート')
    parser.add_argument('csv_path', nargs='?',
                        default='/Users/hirosesuzu/Library/CloudStorage/GoogleDrive-katsu44sky@gmail.com/マイドライブ/OZAシステム/J_OZAからのテーブル/T4_ユーザー契約情報_202511272047_UTF8.csv',
                        help='CSVファイルパス')
    parser.add_argument('--execute', action='store_true', help='実際にインポートを実行')
    args = parser.parse_args()

    if args.execute:
        print("実際のインポートを実行します...")
        import_t4_csv(args.csv_path, dry_run=False)
    else:
        print("ドライランモード（--execute で実行）")
        import_t4_csv(args.csv_path, dry_run=True)
