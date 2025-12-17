"""
コースチケット紐づけデータインポートスクリプト (T08b)
使用方法: docker compose run --rm backend python scripts/import_course_tickets.py <xlsx_path>
"""
import sys
import os
import django
import openpyxl

# Django設定
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.contracts.models import Course, Ticket, CourseTicket, Pack, PackTicket
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


def import_course_tickets(xlsx_path):
    """コースチケットとパックチケットをインポート"""

    # テナント取得
    an_tenant = Tenant.objects.filter(tenant_code='100000').first()
    teraco_tenant = Tenant.objects.filter(tenant_code='101615').first()

    if not an_tenant or not teraco_tenant:
        print("エラー: テナントが見つかりません")
        sys.exit(1)

    print(f"アンイングリッシュグループ: {an_tenant.id}")
    print(f"株式会社TE・RA・CO: {teraco_tenant.id}")

    # コースマップ（契約ID -> Course）
    course_map = {}
    for c in Course.objects.all():
        key = (str(c.tenant_id), c.course_code)
        course_map[key] = c
        course_map[c.course_code] = c
    print(f"コースマップ: {len(course_map)} 件")

    # パックマップ（パックコード -> Pack）
    pack_map = {}
    for p in Pack.objects.all():
        key = (str(p.tenant_id), p.pack_code)
        pack_map[key] = p
        pack_map[p.pack_code] = p
    print(f"パックマップ: {len(pack_map)} 件")

    # チケットマップ
    ticket_map = {}
    for t in Ticket.objects.all():
        key = (str(t.tenant_id), t.ticket_code)
        ticket_map[key] = t
        ticket_map[t.ticket_code] = t
    print(f"チケットマップ: {len(ticket_map)} 件")

    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb['②T8_契約とチケット情報_CSV用']

    course_ticket_imported = 0
    course_ticket_updated = 0
    pack_ticket_imported = 0
    pack_ticket_updated = 0
    skipped = 0
    errors = []

    for row_num, row in enumerate(ws.iter_rows(min_row=2), start=2):
        try:
            # 契約ID
            contract_id = str(row[2].value).strip() if row[2].value else ''
            if not contract_id:
                continue

            # ブランドコード
            brand_code = str(row[3].value).strip() if row[3].value else ''

            # テナント決定
            if is_success_brand(brand_code):
                tenant_id = teraco_tenant.id
            else:
                tenant_id = an_tenant.id

            # 基本/パック（1=基本、2=?、3=パック）
            pack_type = str(row[7].value).strip() if row[7].value else ''
            is_pack = pack_type == '3'

            if is_pack:
                # パックを探す
                target = pack_map.get((str(tenant_id), contract_id)) or pack_map.get(contract_id)
                if not target:
                    skipped += 1
                    continue
            else:
                # コースを探す
                target = course_map.get((str(tenant_id), contract_id)) or course_map.get(contract_id)
                if not target:
                    skipped += 1
                    continue

            # チケットID_1〜11を処理
            for i in range(11):
                ticket_col = 9 + (i * 4)  # 9, 13, 17, 21, 25, 29, 33, 37, 41, 45, 49
                qty_col = 10 + (i * 4)    # 10, 14, 18, 22, 26, 30, 34, 38, 42, 46, 50

                if ticket_col >= len(row):
                    break

                ticket_code = str(row[ticket_col].value).strip() if row[ticket_col].value else ''
                if not ticket_code:
                    continue

                # チケット検索
                ticket = ticket_map.get((str(tenant_id), ticket_code)) or ticket_map.get(ticket_code)
                if not ticket:
                    continue

                # 数量
                qty = parse_int(row[qty_col].value) if qty_col < len(row) else 1
                if not qty:
                    qty = 1

                if is_pack:
                    # PackTicket
                    existing = PackTicket.objects.filter(
                        pack=target,
                        ticket=ticket
                    ).first()

                    if existing:
                        existing.quantity = qty
                        existing.save()
                        pack_ticket_updated += 1
                    else:
                        PackTicket.objects.create(
                            tenant_id=tenant_id,
                            pack=target,
                            ticket=ticket,
                            quantity=qty,
                            per_week=qty,
                            sort_order=i,
                            is_active=True,
                        )
                        pack_ticket_imported += 1
                else:
                    # CourseTicket
                    existing = CourseTicket.objects.filter(
                        course=target,
                        ticket=ticket
                    ).first()

                    if existing:
                        existing.quantity = qty
                        existing.save()
                        course_ticket_updated += 1
                    else:
                        CourseTicket.objects.create(
                            tenant_id=tenant_id,
                            course=target,
                            ticket=ticket,
                            quantity=qty,
                            per_week=qty,
                            sort_order=i,
                            is_active=True,
                        )
                        course_ticket_imported += 1

            total = course_ticket_imported + course_ticket_updated + pack_ticket_imported + pack_ticket_updated
            if total % 500 == 0 and total > 0:
                print(f"  処理中... コースチケット {course_ticket_imported + course_ticket_updated} 件, パックチケット {pack_ticket_imported + pack_ticket_updated} 件")

        except Exception as e:
            errors.append(f"行 {row_num}: {contract_id} - {str(e)}")
            continue

    return course_ticket_imported, course_ticket_updated, pack_ticket_imported, pack_ticket_updated, skipped, errors


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python scripts/import_course_tickets.py <xlsx_path>")
        sys.exit(1)

    xlsx_path = sys.argv[1]

    if not os.path.exists(xlsx_path):
        print(f"エラー: ファイルが見つかりません: {xlsx_path}")
        sys.exit(1)

    print(f"インポート開始: {xlsx_path}")
    print("-" * 50)

    ct_imported, ct_updated, pt_imported, pt_updated, skipped, errors = import_course_tickets(xlsx_path)

    print("-" * 50)
    print(f"完了!")
    print(f"  コースチケット新規: {ct_imported} 件")
    print(f"  コースチケット更新: {ct_updated} 件")
    print(f"  パックチケット新規: {pt_imported} 件")
    print(f"  パックチケット更新: {pt_updated} 件")
    print(f"  スキップ: {skipped} 件")

    if errors:
        print(f"  エラー: {len(errors)} 件")
        for error in errors[:10]:
            print(f"    - {error}")
        if len(errors) > 10:
            print(f"    ... 他 {len(errors) - 10} 件")
