"""
校舎データインポートスクリプト
Excel ファイルから校舎データをインポートします
"""
import os
import sys
import django

# Djangoセットアップ
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

import pandas as pd
from apps.schools.models import Brand, School
from apps.tenants.models import Tenant


def import_schools(excel_path: str, tenant_code: str = None):
    """
    Excelファイルから校舎データをインポート

    Args:
        excel_path: Excelファイルのパス
        tenant_code: テナントコード（指定しない場合は最初のテナントを使用）
    """
    # テナント取得
    if tenant_code:
        tenant = Tenant.objects.get(tenant_code=tenant_code)
    else:
        tenant = Tenant.objects.first()
        if not tenant:
            print("テナントが存在しません。先にテナントを作成してください。")
            return

    print(f"テナント: {tenant.tenant_name} ({tenant.tenant_code})")

    # デフォルトブランド作成（なければ）
    brand, created = Brand.objects.get_or_create(
        tenant_id=tenant.id,
        brand_code='DEFAULT',
        defaults={
            'brand_name': 'デフォルトブランド',
            'brand_name_short': 'DEFAULT',
            'is_active': True,
        }
    )
    if created:
        print(f"ブランド作成: {brand.brand_name}")
    else:
        print(f"既存ブランド使用: {brand.brand_name}")

    # Excelファイル読み込み
    df = pd.read_excel(excel_path, sheet_name='T10_校舎情報_CSV書き出し用DATAもと')
    print(f"読み込み行数: {len(df)}")

    imported = 0
    skipped = 0
    errors = []

    for idx, row in df.iterrows():
        school_code = row.get('校舎ID')
        school_name = row.get('校舎名')

        if pd.isna(school_code) or pd.isna(school_name):
            skipped += 1
            continue

        school_code = str(school_code).strip()
        school_name = str(school_name).strip()

        # 既存チェック
        if School.objects.filter(tenant_id=tenant.id, school_code=school_code).exists():
            print(f"  スキップ（既存）: {school_code} - {school_name}")
            skipped += 1
            continue

        try:
            # 都道府県を取得
            prefecture = row.get('県', '')
            if pd.isna(prefecture) or prefecture == '#ERROR!':
                prefecture = '愛知県'  # デフォルト

            # 住所を取得
            address1 = row.get('住所_1', '')
            if pd.isna(address1) or address1 == '#ERROR!':
                address1 = ''

            address2 = row.get('住所_2', '')
            if pd.isna(address2) or address2 == '#ERROR!':
                address2 = ''

            # 住所から市区町村を抽出
            city = ''
            if address1:
                # 「市」「区」「町」「村」で分割して最初の部分を市区町村とする
                for sep in ['市', '区', '町', '村']:
                    if sep in str(address1):
                        parts = str(address1).split(sep)
                        city = parts[0] + sep
                        break

            # 郵便番号
            postal_code = row.get('校舎郵便番号', '')
            if pd.isna(postal_code) or postal_code == '#ERROR!':
                postal_code = ''
            else:
                postal_code = str(postal_code).replace('-', '')

            # 電話番号
            phone = row.get('電話', '')
            if pd.isna(phone):
                phone = ''

            # FAX
            fax = row.get('FAX', '')
            if pd.isna(fax):
                fax = ''

            # 緯度経度
            latitude = row.get('緯度')
            if pd.isna(latitude) or latitude == '#ERROR!':
                latitude = None
            else:
                try:
                    latitude = float(latitude)
                except:
                    latitude = None

            longitude = row.get('経度')
            if pd.isna(longitude) or longitude == '#ERROR!':
                longitude = None
            else:
                try:
                    longitude = float(longitude)
                except:
                    longitude = None

            # 部屋数
            capacity = row.get('部屋数')
            if pd.isna(capacity):
                capacity = None
            else:
                try:
                    capacity = int(capacity)
                except:
                    capacity = None

            # 校舎作成
            school = School.objects.create(
                tenant_id=tenant.id,
                brand=brand,
                school_code=school_code,
                school_name=school_name,
                school_name_short=str(row.get('短縮名', '')).strip() if not pd.isna(row.get('短縮名')) else '',
                postal_code=postal_code,
                prefecture=prefecture,
                city=city,
                address1=str(address1) if address1 else '',
                address2=str(address2) if address2 else '',
                phone=str(phone),
                fax=str(fax),
                latitude=latitude,
                longitude=longitude,
                capacity=capacity,
                is_active=True,
            )
            print(f"  作成: {school_code} - {school_name} ({prefecture} {city})")
            imported += 1

        except Exception as e:
            errors.append(f"{school_code}: {str(e)}")
            print(f"  エラー: {school_code} - {str(e)}")

    print("\n" + "=" * 50)
    print(f"インポート完了: {imported}件")
    print(f"スキップ: {skipped}件")
    if errors:
        print(f"エラー: {len(errors)}件")
        for e in errors:
            print(f"  - {e}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='校舎データインポート')
    parser.add_argument('excel_path', help='Excelファイルのパス')
    parser.add_argument('--tenant', '-t', help='テナントコード', default=None)
    args = parser.parse_args()

    import_schools(args.excel_path, args.tenant)
