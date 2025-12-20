"""
T5（追加請求）CSVからStudentItemを作成するスクリプト

追加請求データ（検定料、教材費、設備費など）をインポート
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
from decimal import Decimal
from django.db import transaction

from apps.contracts.models import Contract, StudentItem, Product
from apps.students.models import Student, Guardian
from apps.schools.models import Brand
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


def import_t5_csv(csv_path, dry_run=True):
    """T5 CSVからStudentItemを作成"""
    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name} ({tenant.id})")
    print(f"CSVファイル: {csv_path}")
    print(f"モード: {'ドライラン' if dry_run else '実行'}")

    # CSVを読み込み
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    print(f"総レコード数: {len(df)}")

    # マッピングを作成
    print("\nマッピングを作成中...")

    # 保護者マップ
    guardian_map = {}
    for g in Guardian.objects.filter(tenant_id=tenant.id).exclude(old_id__isnull=True).exclude(old_id=''):
        guardian_map[str(g.old_id)] = g
    print(f"  保護者: {len(guardian_map)}件")

    # 生徒マップ
    student_map = {}
    for s in Student.objects.filter(tenant_id=tenant.id).exclude(old_id__isnull=True).exclude(old_id=''):
        student_map[str(s.old_id)] = s
    print(f"  生徒: {len(student_map)}件")

    # ブランドマップ
    brand_map = {}
    for b in Brand.objects.all():
        brand_map[b.brand_name] = b
    print(f"  ブランド: {len(brand_map)}件")

    # 契約マップ (old_id -> Contract)
    contract_map = {}
    for c in Contract.objects.filter(tenant_id=tenant.id).exclude(old_id__isnull=True).exclude(old_id=''):
        contract_map[str(c.old_id)] = c
    print(f"  契約: {len(contract_map)}件")

    # 既存のStudentItemマップ
    existing_items = set()
    for si in StudentItem.objects.filter(tenant_id=tenant.id).exclude(old_id=''):
        existing_items.add(si.old_id)
    print(f"  既存StudentItem: {len(existing_items)}件")

    # 統計
    stats = {
        'processed': 0,
        'created': 0,
        'skipped_exists': 0,
        'skipped_no_student': 0,
        'skipped_invalid': 0,
        'errors': []
    }

    print("\n処理を開始...")

    with transaction.atomic():
        for idx, row in df.iterrows():
            stats['processed'] += 1

            if stats['processed'] % 1000 == 0:
                print(f"  処理中: {stats['processed']}/{len(df)}")

            try:
                # 請求ID
                billing_id = str(row.get('請求ID', '')).strip()
                if not billing_id:
                    stats['skipped_invalid'] += 1
                    continue

                # 既に存在する場合はスキップ
                if billing_id in existing_items:
                    stats['skipped_exists'] += 1
                    continue

                # 有無チェック（1=有効）
                if row.get('有無') != 1:
                    stats['skipped_invalid'] += 1
                    continue

                # 生徒を検索
                student_old_id = str(int(row['生徒ID'])) if not pd.isna(row['生徒ID']) else None
                student = student_map.get(student_old_id) if student_old_id else None

                if not student:
                    stats['skipped_no_student'] += 1
                    continue

                # 金額
                amount = row.get('金額', 0)
                if pd.isna(amount):
                    amount = 0
                amount = Decimal(str(int(amount)))

                # 日付
                start_date = parse_date(row.get('開始日'))
                end_date = parse_date(row.get('終了日'))

                if not start_date:
                    start_date = datetime.now().date()

                # 請求月を計算
                billing_month = start_date.strftime('%Y-%m')

                # ブランドを検索
                brand_name = str(row.get('対象　同ブランド', '')).strip() if not pd.isna(row.get('対象　同ブランド')) else None
                brand = find_brand_by_name(brand_name, brand_map)

                # 契約を検索（対象契約IDまたは対象請求ID）
                contract_old_id = str(row.get('対象　契約ID', '')).strip() if not pd.isna(row.get('対象　契約ID')) else None
                contract = contract_map.get(contract_old_id) if contract_old_id else None

                # 備考・商品名
                billing_name = str(row.get('顧客表記用請求名（契約、請求IDの請求は、そのすぐ下に表記）', '')).strip() \
                    if not pd.isna(row.get('顧客表記用請求名（契約、請求IDの請求は、そのすぐ下に表記）')) else ''
                category = str(row.get('対象カテゴリー', '')).strip() \
                    if not pd.isna(row.get('対象カテゴリー')) else ''

                notes = billing_name or category

                # StudentItemを作成
                student_item = StudentItem(
                    tenant_id=tenant.id,
                    old_id=billing_id,
                    student=student,
                    contract=contract,
                    brand=brand,
                    billing_month=billing_month,
                    quantity=1,
                    unit_price=amount,
                    discount_amount=Decimal('0'),
                    final_price=amount,
                    start_date=start_date,
                    notes=notes,
                )

                if not dry_run:
                    student_item.save()

                existing_items.add(billing_id)
                stats['created'] += 1

            except Exception as e:
                stats['errors'].append(f"Row {idx}: {str(e)}")
                if len(stats['errors']) < 5:
                    import traceback
                    traceback.print_exc()

        if dry_run:
            print("\n=== ドライラン結果 ===")
            transaction.set_rollback(True)
        else:
            print("\n=== 実行結果 ===")

    print(f"処理行数: {stats['processed']}")
    print(f"作成: {stats['created']}")
    print(f"スキップ（既存）: {stats['skipped_exists']}")
    print(f"スキップ（生徒なし）: {stats['skipped_no_student']}")
    print(f"スキップ（無効）: {stats['skipped_invalid']}")
    print(f"エラー: {len(stats['errors'])}")

    if stats['errors']:
        print("\n最初の10件のエラー:")
        for err in stats['errors'][:10]:
            print(f"  - {err}")

    return stats


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='T5 CSVからStudentItemをインポート')
    parser.add_argument('csv_path', nargs='?',
                        default='/tmp/T5_additional.csv',
                        help='CSVファイルパス')
    parser.add_argument('--execute', action='store_true', help='実際にインポートを実行')
    args = parser.parse_args()

    if args.execute:
        print("実際のインポートを実行します...")
        import_t5_csv(args.csv_path, dry_run=False)
    else:
        print("ドライランモード（--execute で実行）")
        import_t5_csv(args.csv_path, dry_run=True)
