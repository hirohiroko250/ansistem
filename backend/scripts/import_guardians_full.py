"""
保護者情報フルインポートスクリプト
OZAシステムのT1_保護者銀行情報CSVから保護者情報を全て更新
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
from apps.schools.models import School
from apps.tenants.models import Tenant


def convert_account_type(value):
    """口座種別を変換"""
    mapping = {
        '1': 'ordinary',
        '2': 'current',
        '3': 'savings',
        '普通': 'ordinary',
        '当座': 'current',
        '貯蓄': 'savings',
    }
    return mapping.get(str(value), 'ordinary')


def import_guardians_full(csv_path, tenant_id=None, dry_run=True):
    """
    CSVから保護者情報をフルインポート/更新
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

    # 校舎名→校舎オブジェクトのマッピングを作成
    school_map = {}
    for school in School.objects.filter(tenant_id=tenant.id):
        school_map[school.school_name] = school
        # 「校」を除いた名前でもマッピング
        if school.school_name.endswith('校'):
            school_map[school.school_name[:-1]] = school

    updated_count = 0
    created_count = 0
    not_found_count = 0
    errors = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            guardian_old_id = row.get('保護者ID', '').strip()
            if not guardian_old_id:
                continue

            # 保護者を検索（old_idで）
            guardian = Guardian.objects.filter(
                tenant_id=tenant.id,
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
                if not_found_count <= 5:
                    print(f"保護者が見つかりません: {guardian_old_id}")
                continue

            try:
                # 基本情報
                last_name = row.get('苗字', '').strip()
                first_name = row.get('お名前', '').strip()
                last_name_kana = row.get('姓（読み仮名）', '').strip()
                first_name_kana = row.get('名（読み仮名）', '').strip()
                last_name_roman = row.get('姓（アルファベット）', '').strip()
                first_name_roman = row.get('名（アルファベット）', '').strip()

                # 連絡先
                email = row.get('メールアドレス', '').strip()
                phone = row.get('電話1番号', '').strip()
                phone_mobile = row.get('初回登録_電話番号1', '').strip() or phone

                # 住所
                postal_code = row.get('郵便番号', '').strip()
                prefecture = row.get('都道府県', '').strip()
                city = row.get('市区町村', '').strip()
                address1 = row.get('番地', '').strip()
                address2 = row.get('建物・部屋番号', '').strip()

                # 勤務先
                workplace = row.get('勤務先1', '').strip()
                workplace2 = row.get('勤務先2', '').strip()

                # 最寄り校舎
                nearest_school_name = row.get('基準校舎(お近くの校舎）', '').strip()
                nearest_school = school_map.get(nearest_school_name)

                # 銀行口座
                bank_name = row.get('銀行名', '').strip()
                bank_code = row.get('銀行番号', '').strip()
                branch_name = row.get('支店名', '').strip()
                branch_code = row.get('支店番号', '').strip()
                account_type = row.get('口座種別', '').strip()
                account_number = row.get('口座番号', '').strip()
                account_holder_kana = row.get('口座名義（ｶﾅ）', '').strip()

                if not dry_run:
                    # 基本情報更新
                    if last_name:
                        guardian.last_name = last_name
                    if first_name:
                        guardian.first_name = first_name
                    if last_name_kana:
                        guardian.last_name_kana = last_name_kana
                    if first_name_kana:
                        guardian.first_name_kana = first_name_kana
                    if last_name_roman:
                        guardian.last_name_roman = last_name_roman
                    if first_name_roman:
                        guardian.first_name_roman = first_name_roman

                    # 連絡先更新
                    if email:
                        guardian.email = email
                    if phone:
                        guardian.phone = phone
                    if phone_mobile:
                        guardian.phone_mobile = phone_mobile

                    # 住所更新
                    if postal_code:
                        guardian.postal_code = postal_code
                    if prefecture:
                        guardian.prefecture = prefecture
                    if city:
                        guardian.city = city
                    if address1:
                        guardian.address1 = address1
                    if address2:
                        guardian.address2 = address2

                    # 勤務先更新
                    if workplace:
                        guardian.workplace = workplace
                    if workplace2:
                        guardian.workplace2 = workplace2

                    # 最寄り校舎
                    if nearest_school:
                        guardian.nearest_school = nearest_school

                    # 銀行口座更新
                    if bank_name:
                        guardian.bank_name = bank_name
                    if bank_code:
                        guardian.bank_code = bank_code
                    if branch_name:
                        guardian.branch_name = branch_name
                    if branch_code:
                        guardian.branch_code = branch_code
                    if account_type:
                        guardian.account_type = convert_account_type(account_type)
                    if account_number:
                        guardian.account_number = account_number
                    if account_holder_kana:
                        guardian.account_holder_kana = account_holder_kana
                    if not guardian.account_holder and (last_name or first_name):
                        guardian.account_holder = f"{last_name} {first_name}".strip()

                    guardian.save()

                updated_count += 1
                if updated_count <= 5:
                    print(f"更新: {guardian_old_id} -> {guardian.guardian_no} ({last_name} {first_name})")

            except Exception as e:
                errors.append(f"{guardian_old_id}: {str(e)}")

    print("-" * 50)
    print(f"更新成功: {updated_count}件")
    print(f"保護者未発見: {not_found_count}件")

    if errors:
        print(f"エラー: {len(errors)}件")
        for error in errors[:10]:
            print(f"  {error}")

    if dry_run:
        print("\n※ドライランモードのため実際の更新は行われていません")
        print("※実際に更新するには --execute オプションを付けて実行してください")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='保護者情報フルインポート')
    parser.add_argument('csv_path', help='CSVファイルパス')
    parser.add_argument('--tenant-id', help='テナントID')
    parser.add_argument('--execute', action='store_true', help='実際に更新を実行')

    args = parser.parse_args()

    import_guardians_full(
        args.csv_path,
        tenant_id=args.tenant_id,
        dry_run=not args.execute
    )
