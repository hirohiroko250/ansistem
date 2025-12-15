"""
保護者銀行口座情報インポートスクリプト
OZAシステムのT1_保護者銀行情報CSVから銀行口座情報をGuardianモデルに更新
"""
import os
import sys
import csv
import django

# Django setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.students.models import Guardian
from apps.tenants.models import Tenant


def convert_account_type(value):
    """口座種別を変換"""
    # 1=普通, 2=当座, など
    mapping = {
        '1': 'ordinary',
        '2': 'current',
        '3': 'savings',
        '普通': 'ordinary',
        '当座': 'current',
        '貯蓄': 'savings',
    }
    return mapping.get(str(value), 'ordinary')


def import_guardian_bank_accounts(csv_path, tenant_id=None, dry_run=True):
    """
    CSVから保護者の銀行口座情報をインポート

    Args:
        csv_path: CSVファイルパス
        tenant_id: テナントID（指定しない場合は最初のテナントを使用）
        dry_run: Trueの場合は実際の更新を行わない
    """
    # テナント取得
    if tenant_id:
        tenant = Tenant.objects.get(id=tenant_id)
    else:
        tenant = Tenant.objects.first()

    if not tenant:
        print("エラー: テナントが見つかりません")
        return

    print(f"テナント: {tenant.tenant_name} ({tenant.id})")
    print(f"ドライラン: {dry_run}")
    print("-" * 50)

    updated_count = 0
    not_found_count = 0
    skipped_count = 0
    errors = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            guardian_old_id = row.get('保護者ID', '').strip()
            bank_name = row.get('銀行名', '').strip()
            bank_code = row.get('銀行番号', '').strip()
            branch_name = row.get('支店名', '').strip()
            branch_code = row.get('支店番号', '').strip()
            account_type = row.get('口座種別', '').strip()
            account_number = row.get('口座番号', '').strip()
            account_holder_kana = row.get('口座名義（ｶﾅ）', '').strip()

            # 銀行情報がない場合はスキップ
            if not bank_name or not account_number:
                skipped_count += 1
                continue

            # 保護者を検索（old_idまたはguardian_noで）
            guardian = Guardian.objects.filter(
                tenant_id=tenant.id
            ).filter(
                old_id=guardian_old_id
            ).first()

            if not guardian:
                # guardian_noでも検索
                guardian = Guardian.objects.filter(
                    tenant_id=tenant.id,
                    guardian_no=guardian_old_id
                ).first()

            if not guardian:
                not_found_count += 1
                if not_found_count <= 10:
                    print(f"保護者が見つかりません: {guardian_old_id}")
                continue

            # 銀行口座情報を更新
            try:
                if not dry_run:
                    guardian.bank_name = bank_name
                    guardian.bank_code = bank_code
                    guardian.branch_name = branch_name
                    guardian.branch_code = branch_code
                    guardian.account_type = convert_account_type(account_type)
                    guardian.account_number = account_number
                    guardian.account_holder_kana = account_holder_kana
                    # 口座名義は保護者のカナ名を使用（CSVには口座名義の漢字がないため）
                    if not guardian.account_holder:
                        guardian.account_holder = f"{guardian.last_name} {guardian.first_name}"
                    guardian.save()

                updated_count += 1
                if updated_count <= 10:
                    print(f"更新: {guardian_old_id} -> {guardian.guardian_no} ({guardian.last_name} {guardian.first_name})")
                    print(f"  銀行: {bank_name} ({bank_code}) {branch_name} ({branch_code})")
                    print(f"  口座: {account_type} {account_number} {account_holder_kana}")

            except Exception as e:
                errors.append(f"{guardian_old_id}: {str(e)}")

    print("-" * 50)
    print(f"更新成功: {updated_count}件")
    print(f"保護者未発見: {not_found_count}件")
    print(f"銀行情報なしスキップ: {skipped_count}件")

    if errors:
        print(f"エラー: {len(errors)}件")
        for error in errors[:10]:
            print(f"  {error}")

    if dry_run:
        print("\n※ドライランモードのため実際の更新は行われていません")
        print("※実際に更新するには --execute オプションを付けて実行してください")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='保護者銀行口座情報インポート')
    parser.add_argument('csv_path', help='CSVファイルパス')
    parser.add_argument('--tenant-id', help='テナントID')
    parser.add_argument('--execute', action='store_true', help='実際に更新を実行')

    args = parser.parse_args()

    import_guardian_bank_accounts(
        args.csv_path,
        tenant_id=args.tenant_id,
        dry_run=not args.execute
    )
