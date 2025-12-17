"""
チケットマスタデータインポートスクリプト (T7)
使用方法: docker compose run --rm backend python scripts/import_tickets.py <xlsx_path>
"""
import sys
import os
import django
import openpyxl

# Django設定
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.contracts.models import Ticket
from apps.schools.models import Brand
from apps.tenants.models import Tenant


# サクセス系ブランド
SUCCESS_BRANDS = {
    'AES', 'AGS', 'BMS', 'FES', 'GOK', 'MPS', 'MWS', 'PRS',
    'SCC', 'SEL', 'SFE', 'SFJ', 'SHI', 'SHS', 'SJJ', 'SJU',
    'SKC', 'SKK', 'SOS', 'SUC', 'SHO', 'SEK',
}


def is_success_brand(brand_code):
    """サクセス系ブランドかどうか"""
    if not brand_code:
        return False
    return brand_code in SUCCESS_BRANDS


def parse_int(value):
    """整数パース"""
    if not value:
        return None
    try:
        return int(float(value))
    except:
        return None


def import_tickets(xlsx_path):
    """チケットをインポート"""

    # テナント取得
    an_tenant = Tenant.objects.filter(tenant_code='100000').first()
    teraco_tenant = Tenant.objects.filter(tenant_code='101615').first()

    if not an_tenant or not teraco_tenant:
        print("エラー: テナントが見つかりません")
        sys.exit(1)

    print(f"アンイングリッシュグループ: {an_tenant.id}")
    print(f"株式会社TE・RA・CO: {teraco_tenant.id}")

    # ブランドマップ
    brand_map = {}
    for b in Brand.objects.all():
        brand_map[b.brand_code] = b

    print(f"ブランドマップ: {len(brand_map)} 件")

    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb['★T7_チケット情報　これを元へ張り付ける事']

    imported = 0
    updated = 0
    errors = []

    for row_num, row in enumerate(ws.iter_rows(min_row=2), start=2):
        try:
            # チケットID
            ticket_code = str(row[0].value).strip() if row[0].value else ''
            if not ticket_code:
                continue

            # チケット種類
            ticket_type_raw = str(row[1].value).strip() if row[1].value else ''
            if '1' in ticket_type_raw:
                ticket_type = '1'  # 授業
            elif '5' in ticket_type_raw:
                ticket_type = '5'  # 講習会
            elif '6' in ticket_type_raw:
                ticket_type = '6'  # 模試
            elif '7' in ticket_type_raw:
                ticket_type = '7'  # テスト対策
            elif '8' in ticket_type_raw:
                ticket_type = '8'  # 自宅受講
            else:
                ticket_type = '0'

            # チケット区別
            ticket_category = str(row[2].value).strip() if row[2].value else '1'
            if ticket_category not in ['1', '2', '3']:
                ticket_category = '0'

            # チケット名
            ticket_name = str(row[6].value).strip() if row[6].value else ''
            if not ticket_name:
                ticket_name = str(row[5].value).strip() if row[5].value else ticket_code

            # ブランド
            brand_code = str(row[8].value).strip() if row[8].value else ''
            brand = brand_map.get(brand_code)

            # テナント決定
            if is_success_brand(brand_code):
                tenant_id = teraco_tenant.id
            else:
                tenant_id = an_tenant.id

            # 基本定員、Max値
            capacity = parse_int(row[9].value) or 10
            max_per_lesson = parse_int(row[10].value) or 1

            # 振替曜日
            transfer_day = parse_int(row[11].value)

            # 年間/週、チケット枚数
            annual_weekly = parse_int(row[12].value) or 42
            total_tickets = parse_int(row[13].value) or 42

            # 振替Group
            transfer_group = str(row[14].value).strip() if row[14].value else ''

            # 消化記号
            consumption_symbol = str(row[17].value).strip() if row[17].value else ''

            # 年マタギ利用
            year_carryover_raw = str(row[18].value).strip() if row[18].value else ''
            year_carryover = year_carryover_raw.upper() == 'OK'

            # カレンダーフラグ
            calendar_flag = parse_int(row[20].value) or 2

            # 既存チェック
            existing = Ticket.objects.filter(
                tenant_id=tenant_id,
                ticket_code=ticket_code
            ).first()

            data = {
                'tenant_id': tenant_id,
                'ticket_code': ticket_code,
                'ticket_name': ticket_name[:200] if ticket_name else ticket_code,
                'ticket_type': ticket_type,
                'ticket_category': ticket_category,
                'transfer_day': transfer_day,
                'transfer_group': transfer_group,
                'consumption_symbol': consumption_symbol,
                'annual_weekly': annual_weekly,
                'max_per_lesson': max_per_lesson,
                'total_tickets': total_tickets,
                'calendar_flag': calendar_flag,
                'year_carryover': year_carryover,
                'brand': brand,
                'is_active': True,
            }

            if existing:
                for key, value in data.items():
                    if key != 'brand' or value is not None:
                        setattr(existing, key, value)
                existing.save()
                updated += 1
            else:
                Ticket.objects.create(**data)
                imported += 1

            if (imported + updated) % 100 == 0:
                print(f"  処理中... {imported + updated} 件")

        except Exception as e:
            errors.append(f"行 {row_num}: {ticket_code} - {str(e)}")
            continue

    return imported, updated, errors


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python scripts/import_tickets.py <xlsx_path>")
        sys.exit(1)

    xlsx_path = sys.argv[1]

    if not os.path.exists(xlsx_path):
        print(f"エラー: ファイルが見つかりません: {xlsx_path}")
        sys.exit(1)

    print(f"インポート開始: {xlsx_path}")
    print("-" * 50)

    imported, updated, errors = import_tickets(xlsx_path)

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
