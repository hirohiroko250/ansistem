#!/usr/bin/env python
"""
校舎CSVからデータをインポート
"""
import os
import sys
sys.path.insert(0, '/Users/hirosesuzu/Desktop/アンシステム/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

import csv
from decimal import Decimal
from datetime import datetime
from apps.schools.models import School, Brand
from apps.tenants.models import Tenant


CSV_PATH = '/Users/hirosesuzu/Desktop/アンシステム/Claude-Code-Communication/instructions/おざ/T10_校舎情報dayo.xlsx - T10_校舎情報_CSV書き出し用DATAもと.csv'


def get_tenant():
    return Tenant.objects.get(tenant_code='OZA')


def parse_date(date_str):
    """日付文字列をパース"""
    if not date_str or date_str.strip() == '':
        return None
    try:
        # YYYY/M/D 形式
        return datetime.strptime(date_str.strip(), '%Y/%m/%d').date()
    except:
        try:
            # YYYY-MM-DD 形式
            return datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
        except:
            return None


def parse_decimal(val):
    """緯度経度をDecimalに変換"""
    if not val or val.strip() == '':
        return None
    try:
        return Decimal(val.strip())
    except:
        return None


def import_schools():
    print("=" * 60)
    print("校舎CSVインポート")
    print("=" * 60)

    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name}")

    # 現在の校舎数
    current_count = School.objects.filter(tenant_id=tenant.id).count()
    print(f"現在の校舎数: {current_count}")

    # デフォルトブランド取得（校舎にはブランドが必須）
    # CSVにブランド情報がないので、最初のブランドを使用
    default_brand = Brand.objects.filter(tenant_id=tenant.id).first()
    if not default_brand:
        print("エラー: ブランドが見つかりません")
        return
    print(f"デフォルトブランド: {default_brand.brand_name}")

    created = 0
    updated = 0
    errors = 0

    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                school_code = row.get('校舎ID', '').strip()
                if not school_code:
                    continue

                # 開校日・閉校日
                opening_date = parse_date(row.get('校舎開校日', ''))
                closing_date = parse_date(row.get('校舎閉校日', ''))

                # 緯度経度
                latitude = parse_decimal(row.get('緯度', ''))
                longitude = parse_decimal(row.get('経度', ''))

                # 部屋数（capacity として使用）
                try:
                    capacity = int(row.get('部屋数', '0').strip() or '0')
                except:
                    capacity = None

                # 住所を結合
                address1 = row.get('住所_1', '').strip()
                address2 = row.get('住所_2', '').strip()
                if row.get('住所_3', '').strip():
                    address2 += ' ' + row.get('住所_3', '').strip()

                # 設定JSON
                settings = {
                    'roma_name': row.get('校舎ローマ字名', '').strip(),
                    'area_name': row.get('地区名', '').strip(),
                    'area_no': row.get('地区No', '').strip(),
                    'map_link': row.get('Map Link', '').strip(),
                    'map_pin': row.get('MAP Pin', '').strip(),
                    'building_ownership': row.get('建物所有権', '').strip(),
                    'building_owner_info': row.get('建物オーナー情報', '').strip(),
                    'management_company': row.get('管理会社', '').strip(),
                    'teacher_parking': row.get('教師用駐車場', '').strip(),
                    'customer_parking': row.get('顧客用駐車場', '').strip(),
                    'memo': row.get('メモ', '').strip(),
                    'directions': row.get('行き方', '').strip(),
                    'internet_id': row.get('インターネットID', '').strip(),
                    'wireless': row.get('ワイヤレス', '').strip(),
                    'website': row.get('ウェブサイト', '').strip(),
                }
                # 空の値を除去
                settings = {k: v for k, v in settings.items() if v}

                school, is_created = School.objects.update_or_create(
                    tenant_id=tenant.id,
                    school_code=school_code,
                    defaults={
                        'brand': default_brand,
                        'school_name': row.get('校舎名', '').strip(),
                        'school_name_short': row.get('短縮名', '').strip(),
                        'postal_code': row.get('校舎郵便番号', '').strip(),
                        'prefecture': row.get('県', '').strip(),
                        'city': address1,
                        'address1': address1,
                        'address2': address2,
                        'phone': row.get('電話', '').strip(),
                        'fax': row.get('FAX', '').strip(),
                        'email': row.get('メール', '').strip(),
                        'latitude': latitude,
                        'longitude': longitude,
                        'capacity': capacity,
                        'opening_date': opening_date,
                        'closing_date': closing_date,
                        'settings': settings,
                        'is_active': True,
                    }
                )

                if is_created:
                    created += 1
                else:
                    updated += 1

            except Exception as e:
                errors += 1
                print(f"エラー ({row.get('校舎ID', 'unknown')}): {e}")

    print(f"\n=== 結果 ===")
    print(f"作成: {created}")
    print(f"更新: {updated}")
    print(f"エラー: {errors}")

    # 確認
    final_count = School.objects.filter(tenant_id=tenant.id).count()
    print(f"\n=== 確認 ===")
    print(f"校舎総数: {final_count}")

    # サンプル表示
    print(f"\n=== サンプル（最初の10件）===")
    for school in School.objects.filter(tenant_id=tenant.id).order_by('school_code')[:10]:
        print(f"  [{school.school_code}] {school.school_name} ({school.prefecture} {school.city})")


if __name__ == '__main__':
    import_schools()
