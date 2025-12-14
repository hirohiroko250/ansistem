"""
ユーザー契約情報インポートスクリプト

T4_ユーザー契約情報CSVからContractを作成する。
保護者ID・生徒IDは先にインポート済みのold_idと紐付ける。
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
from django.utils import timezone

from apps.contracts.models import Contract
from apps.students.models import Student, Guardian
from apps.schools.models import School, Brand
from apps.tenants.models import Tenant

# 定数
CSV_PATH = '/tmp/user_contracts.csv'


def get_tenant():
    """テナントを取得"""
    tenant = Tenant.objects.first()
    if not tenant:
        print("テナントが見つかりません。先にテナントを作成してください。")
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


def find_brand_by_name(brand_name, tenant, brand_map):
    """ブランド名で検索"""
    if pd.isna(brand_name) or not brand_name:
        return None

    brand_name = str(brand_name).strip()

    # マップから完全一致
    if brand_name in brand_map:
        return brand_map[brand_name]

    # 部分一致（全ブランドから）
    for name, brand in brand_map.items():
        if brand_name in name or name in brand_name:
            return brand

    return None


def get_contract_status(row):
    """行からステータスを判定"""
    # 全退会日があれば解約
    if parse_date(row.get('全退会日')):
        return Contract.Status.CANCELLED

    # ブランド退会日があれば解約
    if parse_date(row.get('ブランド退会日')):
        return Contract.Status.CANCELLED

    # 休会中（休会開始日あり、復会日なしまたは未来）
    suspend_date = parse_date(row.get('休会開始日'))
    resume_date = parse_date(row.get('復会日'))

    if suspend_date:
        if not resume_date or resume_date > datetime.now().date():
            return Contract.Status.PAUSED

    return Contract.Status.ACTIVE


def import_data(dry_run=True):
    """データをインポート"""
    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name} ({tenant.id})")

    # CSVを読み込み
    print(f"\nCSVファイルを読み込み中: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    print(f"総レコード数: {len(df)}")

    # 保護者と生徒のold_idマッピングを作成
    print("既存データをマッピング中...")

    guardian_map = {}
    for g in Guardian.objects.filter(tenant_id=tenant.id).exclude(old_id__isnull=True).exclude(old_id=''):
        guardian_map[str(g.old_id)] = g
    print(f"  保護者: {len(guardian_map)}")

    student_map = {}
    for s in Student.objects.filter(tenant_id=tenant.id).exclude(old_id__isnull=True).exclude(old_id=''):
        student_map[str(s.old_id)] = s
    print(f"  生徒: {len(student_map)}")

    brand_map = {}
    # ブランドは全テナントから検索（他テナントのブランドを参照している可能性）
    for b in Brand.objects.all():
        brand_map[b.brand_name] = b
    print(f"  ブランド: {len(brand_map)}")

    # 既存の契約をold_idでマッピング
    existing_contracts = {}
    for c in Contract.objects.filter(tenant_id=tenant.id):
        if hasattr(c, 'old_id') and c.old_id:
            existing_contracts[str(c.old_id)] = c
    print(f"  既存契約（old_id付き）: {len(existing_contracts)}")

    # デフォルト校舎を取得（全テナントから）
    default_school = School.objects.filter(is_active=True).first()

    created_contracts = 0
    skipped_no_student = 0
    skipped_existing = 0
    errors = []

    with transaction.atomic():
        for idx, row in df.iterrows():
            contract_old_id = str(row['受講ID']).strip() if not pd.isna(row['受講ID']) else None

            if not contract_old_id:
                continue

            # 既に存在する場合はスキップ
            if contract_old_id in existing_contracts:
                skipped_existing += 1
                continue

            # 生徒を検索
            student_old_id = str(int(row['生徒ID'])) if not pd.isna(row['生徒ID']) else None
            student = student_map.get(student_old_id) if student_old_id else None

            if not student:
                skipped_no_student += 1
                continue

            # 保護者を検索
            guardian_old_id = str(int(row['保護者ID'])) if not pd.isna(row['保護者ID']) else None
            guardian = guardian_map.get(guardian_old_id) if guardian_old_id else None

            # ブランドを検索
            brand_name = str(row['Class用ブランド名']).strip() if not pd.isna(row['Class用ブランド名']) else None
            brand = find_brand_by_name(brand_name, tenant, brand_map) if brand_name else None

            if not brand:
                # ブランドが見つからない場合、デフォルトを使用（アンイングリッシュクラブ）
                brand = Brand.objects.filter(brand_name='アンイングリッシュクラブ').first()

            if not brand:
                # それでも見つからない場合、最初のブランドを使用
                brand = Brand.objects.first()

            if not brand:
                errors.append(f"ブランドが見つからない: {brand_name} (受講ID: {contract_old_id})")
                continue

            # 校舎を設定（生徒の主所属校舎、保護者の最寄り校舎、またはデフォルト）
            school = student.primary_school
            if not school and guardian:
                school = guardian.nearest_school
            if not school:
                school = default_school
            if not school:
                # 最後の手段として全校舎から最初の1件を取得
                school = School.objects.first()
            if not school:
                errors.append(f"校舎が見つからない (受講ID: {contract_old_id})")
                continue

            # 日付を解析
            start_date = parse_date(row.get('開始日'))
            end_date = parse_date(row.get('終了日'))

            if not start_date:
                start_date = datetime.now().date()

            # ステータスを判定
            status = get_contract_status(row)

            # 備考
            notes_parts = []
            if not pd.isna(row.get('備考')) and row['備考']:
                notes_parts.append(str(row['備考']))
            if not pd.isna(row.get('入会理由')) and row['入会理由']:
                notes_parts.append(f"入会理由: {row['入会理由']}")
            if not pd.isna(row.get('契約名')) and row['契約名']:
                notes_parts.append(f"契約名: {row['契約名']}")
            notes = '\n'.join(notes_parts)

            try:
                # 契約番号を生成（受講IDをそのまま使用）
                contract_no = contract_old_id

                contract = Contract(
                    tenant_id=tenant.id,
                    old_id=contract_old_id,
                    contract_no=contract_no,
                    student=student,
                    guardian=guardian or student.guardian,
                    school=school,
                    brand=brand,
                    contract_date=start_date,
                    start_date=start_date,
                    end_date=end_date,
                    status=status,
                    notes=notes,
                )

                if not dry_run:
                    contract.save()

                existing_contracts[contract_old_id] = contract
                created_contracts += 1

            except Exception as e:
                errors.append(f"契約作成エラー (受講ID:{contract_old_id}): {str(e)}")
                import traceback
                traceback.print_exc()

        if dry_run:
            print("\n=== ドライラン結果 ===")
            print(f"作成予定の契約数: {created_contracts}")
            print(f"スキップ（生徒なし）: {skipped_no_student}")
            print(f"スキップ（既存）: {skipped_existing}")
            if errors:
                print(f"\nエラー数: {len(errors)}")
                for err in errors[:10]:
                    print(f"  - {err}")
                if len(errors) > 10:
                    print(f"  ... 他 {len(errors) - 10} 件")

            # ロールバック
            transaction.set_rollback(True)
        else:
            print("\n=== インポート結果 ===")
            print(f"作成した契約数: {created_contracts}")
            print(f"スキップ（生徒なし）: {skipped_no_student}")
            print(f"スキップ（既存）: {skipped_existing}")
            if errors:
                print(f"\nエラー数: {len(errors)}")
                for err in errors[:10]:
                    print(f"  - {err}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='ユーザー契約情報インポート')
    parser.add_argument('--execute', action='store_true', help='実際にインポートを実行')
    args = parser.parse_args()

    if args.execute:
        print("実際のインポートを実行します...")
        import_data(dry_run=False)
    else:
        print("ドライランモード（--execute で実行）")
        import_data(dry_run=True)
