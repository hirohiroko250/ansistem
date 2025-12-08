#!/usr/bin/env python
"""
T4（ユーザー契約情報）CSVインポートスクリプト

契約詳細データをインポート
"""
import os
import sys
import csv
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# Django setup
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import transaction
from apps.students.models import Student, Guardian
from apps.contracts.models import Contract, ContractDetail, Product
from apps.schools.models import Grade, School, Brand

# テナントID（デフォルト）
DEFAULT_TENANT_ID = uuid.UUID('00000000-0000-0000-0000-000000000001')


def parse_date(date_str):
    """日付文字列をパース"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y/%m/%d').date()
    except ValueError:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return None


def get_or_create_brand(brand_name, tenant_id):
    """ブランドを取得または作成"""
    if not brand_name:
        return None

    # ブランド名からコードを作成
    brand_code = brand_name.replace(' ', '_').replace('【', '').replace('】', '')[:20]

    brand, created = Brand.objects.get_or_create(
        tenant_id=tenant_id,
        brand_name=brand_name,
        defaults={
            'brand_code': brand_code,
            'is_active': True
        }
    )
    if created:
        print(f"  Created brand: {brand_name}")
    return brand


def get_or_create_school(school_name, tenant_id, brand=None):
    """校舎を取得または作成"""
    if not school_name or school_name == '-':
        return None

    # 校舎名からコードを作成
    school_code = school_name.replace(' ', '_')[:20]

    school, created = School.objects.get_or_create(
        tenant_id=tenant_id,
        school_name=school_name,
        defaults={
            'school_code': school_code,
            'brand': brand,
            'is_active': True
        }
    )
    if created:
        print(f"  Created school: {school_name}")
    return school


def get_or_create_grade(grade_name, tenant_id):
    """学年を取得または作成"""
    if not grade_name:
        return None

    grade, created = Grade.objects.get_or_create(
        tenant_id=tenant_id,
        grade_name=grade_name,
        defaults={
            'grade_code': grade_name.replace(' ', '_'),
            'is_active': True
        }
    )
    if created:
        print(f"  Created grade: {grade_name}")
    return grade


def get_or_create_student(student_id, student_name, tenant_id):
    """生徒を取得または作成"""
    if not student_id:
        return None

    # student_name から姓名を分割
    names = student_name.split() if student_name else ['', '']
    last_name = names[0] if len(names) > 0 else ''
    first_name = names[1] if len(names) > 1 else ''

    student, created = Student.objects.get_or_create(
        tenant_id=tenant_id,
        student_no=student_id,
        defaults={
            'last_name': last_name,
            'first_name': first_name,
            'status': 'active'
        }
    )
    if created:
        print(f"  Created student: {student_id}")
    return student


def get_or_create_guardian(guardian_id, guardian_name, tenant_id):
    """保護者を取得または作成"""
    if not guardian_id:
        return None

    guardian, created = Guardian.objects.get_or_create(
        tenant_id=tenant_id,
        guardian_no=guardian_id,
        defaults={
            'last_name': guardian_name or '',
            'first_name': ''
        }
    )
    if created:
        print(f"  Created guardian: {guardian_id}")
    return guardian


def get_or_create_product(contract_name, brand, tenant_id):
    """商品を取得または作成"""
    if not contract_name:
        return None

    # 契約名から商品コードを作成
    product_code = contract_name[:20].replace(' ', '_').replace(',', '')

    product, created = Product.objects.get_or_create(
        tenant_id=tenant_id,
        product_name=contract_name,
        defaults={
            'product_code': product_code,
            'brand': brand,
            'base_price': Decimal('0'),
            'is_active': True
        }
    )
    if created:
        print(f"  Created product: {contract_name[:50]}...")
    return product


def import_t4_csv(csv_path, tenant_id=DEFAULT_TENANT_ID):
    """T4 CSVをインポート"""

    print(f"Importing T4 data from: {csv_path}")
    print(f"Tenant ID: {tenant_id}")

    stats = {
        'total_rows': 0,
        'contracts_created': 0,
        'contracts_updated': 0,
        'skipped': 0,
        'errors': []
    }

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Total rows to process: {len(rows)}")

    with transaction.atomic():
        for row in rows:
            stats['total_rows'] += 1

            if stats['total_rows'] % 500 == 0:
                print(f"  Processing row {stats['total_rows']}...")

            try:
                # 受講ID（ユニークキー）
                enrollment_id = row.get('受講ID', '')
                if not enrollment_id:
                    stats['skipped'] += 1
                    continue

                # 保護者・生徒
                guardian_id = row.get('保護者ID', '')
                student_id = row.get('生徒ID', '')
                guardian_name = row.get('保護者名1', '')
                student_name1 = row.get('生徒名1', '')
                student_name2 = row.get('生徒名2', '')
                student_full_name = f"{student_name1} {student_name2}".strip()

                # ブランドと校舎
                brand_name = row.get('Class用ブランド名', '')
                brand = get_or_create_brand(brand_name, tenant_id)

                # 契約情報
                contract_id = row.get('契約ID', '')
                contract_name = row.get('契約名', '')

                # 日付
                start_date = parse_date(row.get('開始日', ''))
                end_date = parse_date(row.get('終了日', ''))

                # 学年
                contract_grade = row.get('契約学年', '')

                # 生徒と保護者を取得または作成
                student = get_or_create_student(student_id, student_full_name, tenant_id)
                guardian = get_or_create_guardian(guardian_id, guardian_name, tenant_id)

                if not student:
                    stats['skipped'] += 1
                    continue

                # ダミー校舎（ブランドがあれば）
                school = None
                if brand:
                    school = get_or_create_school(f"{brand.brand_name}本校", tenant_id, brand)

                # 契約を作成または更新
                contract, created = Contract.objects.update_or_create(
                    tenant_id=tenant_id,
                    contract_no=enrollment_id,
                    defaults={
                        'student': student,
                        'guardian': guardian,
                        'school': school,
                        'brand': brand,
                        'contract_date': start_date or datetime.now().date(),
                        'start_date': start_date or datetime.now().date(),
                        'end_date': end_date,
                        'status': 'active' if not end_date or end_date > datetime.now().date() else 'expired',
                        'notes': row.get('備考', '')
                    }
                )

                if created:
                    stats['contracts_created'] += 1
                else:
                    stats['contracts_updated'] += 1

                # 商品を取得または作成して契約詳細を作成
                if contract_name:
                    product = get_or_create_product(contract_name, brand, tenant_id)

                    if product:
                        ContractDetail.objects.update_or_create(
                            tenant_id=tenant_id,
                            contract=contract,
                            product=product,
                            defaults={
                                'quantity': 1,
                                'unit_price': product.base_price,
                                'subtotal': product.base_price,
                                'total': product.base_price,
                                'start_date': start_date or datetime.now().date(),
                                'end_date': end_date
                            }
                        )

            except Exception as e:
                stats['errors'].append({
                    'row': stats['total_rows'],
                    'enrollment_id': enrollment_id,
                    'error': str(e)
                })

    # 結果表示
    print("\n" + "=" * 50)
    print("Import Complete!")
    print("=" * 50)
    print(f"Total rows processed: {stats['total_rows']}")
    print(f"Contracts created: {stats['contracts_created']}")
    print(f"Contracts updated: {stats['contracts_updated']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Errors: {len(stats['errors'])}")

    if stats['errors']:
        print("\nFirst 10 errors:")
        for err in stats['errors'][:10]:
            print(f"  - Row {err['row']}: {err['error']}")

    return stats


if __name__ == '__main__':
    csv_path = '/Users/hirosesuzu/Desktop/アンシステム/Claude-Code-Communication/instructions/おざ/T4_ユーザー契約情報_202511272047_UTF8.csv'

    if len(sys.argv) > 1:
        csv_path = sys.argv[1]

    import_t4_csv(csv_path)
