"""
保護者データインポートスクリプト
使用方法: docker compose run --rm backend python scripts/import_guardians.py <csv_path>
"""
import csv
import sys
import os
import django
import uuid
from datetime import datetime

# Django設定
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.students.models import Guardian
from apps.tenants.models import Tenant


def clean_phone(phone):
    """電話番号をクリーンアップ"""
    if not phone:
        return ''
    return phone.replace('　', '').replace(' ', '').strip()


def clean_postal_code(postal):
    """郵便番号をクリーンアップ"""
    if not postal:
        return ''
    # ハイフンを除去し、数字のみに
    postal = postal.replace('-', '').replace('ー', '').replace('−', '')
    # 全角数字を半角に
    postal = postal.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    return postal[:8] if postal else ''


def convert_account_type(account_type):
    """口座種別を変換"""
    if not account_type:
        return 'ordinary'
    if '当座' in account_type:
        return 'current'
    if '貯蓄' in account_type:
        return 'savings'
    return 'ordinary'


def import_guardians(csv_path):
    """CSVから保護者データをインポート"""

    # アンイングリッシュグループテナント取得
    tenant = Tenant.objects.filter(tenant_code='100000').first()
    if not tenant:
        print("エラー: アンイングリッシュグループテナントが見つかりません")
        sys.exit(1)
    tenant_id = tenant.id
    print(f"テナント: {tenant.tenant_name} ({tenant_id})")

    imported = 0
    updated = 0
    errors = []

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):
            try:
                guardian_id = row.get('保護者ID', '').strip()
                if not guardian_id:
                    continue

                # 既存チェック（old_idで）
                existing = Guardian.objects.filter(old_id=guardian_id).first()

                # データ準備
                data = {
                    'tenant_id': tenant_id,
                    'guardian_no': guardian_id,
                    'old_id': guardian_id,
                    'last_name': row.get('苗字', '').replace('◆', '').strip() or '未設定',
                    'first_name': row.get('お名前', '').strip() or '未設定',
                    'last_name_kana': row.get('姓（読み仮名）', '').strip() or '',
                    'first_name_kana': row.get('名（読み仮名）', '').strip() or '',
                    'last_name_roman': row.get('姓（アルファベﾂト）', '').strip() or '',
                    'first_name_roman': row.get('名（アルファベﾂト）', '').strip() or '',
                    'email': row.get('メールアドレス', '').strip() or '',
                    'phone': clean_phone(row.get('電話1番号', '')),
                    'phone_mobile': clean_phone(row.get('電話2番号', '')),
                    'postal_code': clean_postal_code(row.get('郵便番号', '')),
                    'prefecture': row.get('都道府県', '').strip() or '',
                    'city': row.get('市区町村', '').strip() or '',
                    'address1': row.get('番地', '').strip() or '',
                    'address2': row.get('建物・部屋番号', '').strip() or '',
                    'workplace': row.get('勤務先1', '').strip() or '',
                    'workplace2': row.get('勤務先2', '').strip() or '',
                    'workplace_phone': '',
                    'workplace_phone2': '',
                    'line_id': '',
                    'interested_brands': [],
                    'referral_source': '',
                    'expectations': '',
                    'notes': '',
                    # 銀行情報
                    'account_holder': row.get('口座名義', '').strip() or '',
                    'account_holder_kana': row.get('口座名義', '').strip() or '',  # カナがないので同じ値
                    'bank_name': row.get('銀行名', '').strip() or '',
                    'bank_code': row.get('銀行番号', '').strip() or '',
                    'branch_name': row.get('支店名', '').strip() or '',
                    'branch_code': row.get('支店番号', '').strip() or '',
                    'account_type': convert_account_type(row.get('口座種別', '')),
                    'account_number': row.get('口座番号', '').strip() or '',
                    'payment_registered': bool(row.get('口座名義', '').strip()),
                }

                if existing:
                    # 更新
                    for key, value in data.items():
                        setattr(existing, key, value)
                    existing.save()
                    updated += 1
                else:
                    # 新規作成
                    Guardian.objects.create(**data)
                    imported += 1

                if (imported + updated) % 100 == 0:
                    print(f"  処理中... {imported + updated} 件")

            except Exception as e:
                errors.append(f"行 {row_num}: {guardian_id} - {str(e)}")
                continue

    return imported, updated, errors


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python scripts/import_guardians.py <csv_path>")
        sys.exit(1)

    csv_path = sys.argv[1]

    if not os.path.exists(csv_path):
        print(f"エラー: ファイルが見つかりません: {csv_path}")
        sys.exit(1)

    print(f"インポート開始: {csv_path}")
    print("-" * 50)

    imported, updated, errors = import_guardians(csv_path)

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
