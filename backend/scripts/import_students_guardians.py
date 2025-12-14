"""
生徒・保護者インポートスクリプト

ExcelファイルからStudent、Guardian、StudentGuardianを作成する。
「保護者との続柄」が「保護者」「本人」のレコードはGuardianとして登録
「保護者との続柄」が「子」のレコードはStudentとして登録
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

from apps.students.models import Student, Guardian, StudentGuardian
from apps.schools.models import School
from apps.tenants.models import Tenant

# 定数
EXCEL_PATH = '/tmp/import_data.xlsx'
SHEET_NAME = 'T2_個人・生徒情報'


def get_tenant():
    """テナントを取得"""
    tenant = Tenant.objects.first()
    if not tenant:
        print("テナントが見つかりません。先にテナントを作成してください。")
        sys.exit(1)
    return tenant


def normalize_phone(phone):
    """電話番号を正規化"""
    if pd.isna(phone):
        return ''
    phone = str(phone).strip()
    # ハイフンを保持
    return phone[:20]  # 20文字以内に


def normalize_postal_code(code):
    """郵便番号を正規化"""
    if pd.isna(code):
        return ''
    code = str(code).strip().replace('-', '').replace('－', '')
    if len(code) == 7:
        return f"{code[:3]}-{code[3:]}"
    return code[:8]


def parse_date(date_val):
    """日付を解析"""
    if pd.isna(date_val):
        return None
    if isinstance(date_val, pd.Timestamp):
        return date_val.date()
    if isinstance(date_val, datetime):
        return date_val.date()
    return None


def get_gender(gender_str):
    """性別を変換"""
    if pd.isna(gender_str):
        return ''
    if gender_str == '男':
        return 'male'
    elif gender_str == '女':
        return 'female'
    return ''


def get_status_from_state(state_str):
    """状態からステータスを変換"""
    if pd.isna(state_str):
        return Student.Status.REGISTERED
    state = str(state_str).strip()
    mapping = {
        '受講中': Student.Status.ENROLLED,
        '休会': Student.Status.SUSPENDED,
        '無': Student.Status.REGISTERED,
        '外部生': Student.Status.REGISTERED,
    }
    return mapping.get(state, Student.Status.REGISTERED)


def get_relationship(relation_str):
    """続柄を変換"""
    if pd.isna(relation_str):
        return Guardian.Relationship.OTHER
    relation = str(relation_str).strip()
    mapping = {
        '父': Guardian.Relationship.FATHER,
        '母': Guardian.Relationship.MOTHER,
        '祖父': Guardian.Relationship.GRANDFATHER,
        '祖母': Guardian.Relationship.GRANDMOTHER,
        '子': Guardian.Relationship.OTHER,  # 子は生徒側なのでOTHER
        '保護者': Guardian.Relationship.OTHER,
        '本人': Guardian.Relationship.OTHER,
    }
    return mapping.get(relation, Guardian.Relationship.OTHER)


def find_school_by_name(school_name, tenant):
    """校舎を名前で検索"""
    if pd.isna(school_name):
        return None
    school_name = str(school_name).strip()

    # 「校」を除去して検索
    search_name = school_name.replace('校', '')

    school = School.objects.filter(
        tenant_id=tenant.id,
        school_name__icontains=search_name
    ).first()

    if not school:
        # 短縮名でも検索
        school = School.objects.filter(
            tenant_id=tenant.id,
            school_name_short__icontains=search_name
        ).first()

    return school


def import_data(dry_run=True):
    """データをインポート"""
    tenant = get_tenant()
    print(f"テナント: {tenant.tenant_name} ({tenant.id})")

    # Excelを読み込み
    print(f"\nExcelファイルを読み込み中: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
    print(f"総レコード数: {len(df)}")

    # 保護者IDでグループ化
    grouped = df.groupby('保護者ID')
    print(f"ユニークな保護者ID数: {len(grouped)}")

    created_guardians = 0
    created_students = 0
    created_relations = 0
    errors = []

    guardian_map = {}  # old_id -> Guardian

    with transaction.atomic():
        # 既存の保護者を old_id でマッピング
        existing_guardians = Guardian.objects.filter(
            tenant_id=tenant.id,
            old_id__isnull=False
        ).exclude(old_id='')
        for g in existing_guardians:
            guardian_map[str(g.old_id)] = g
        print(f"既存保護者（old_id付き）: {len(guardian_map)}")

        # 既存の生徒を old_id でマッピング
        existing_students = {}
        for s in Student.objects.filter(tenant_id=tenant.id, old_id__isnull=False).exclude(old_id=''):
            existing_students[str(s.old_id)] = s
        print(f"既存生徒（old_id付き）: {len(existing_students)}")

        for guardian_old_id, group in grouped:
            guardian_old_id = str(int(guardian_old_id) if not pd.isna(guardian_old_id) else 0)

            if guardian_old_id in guardian_map:
                guardian = guardian_map[guardian_old_id]
            else:
                # 保護者を探す（本人 or 保護者 の行）
                guardian_rows = group[group['保護者との続柄'].isin(['保護者', '本人'])]

                if len(guardian_rows) == 0:
                    # 保護者行がない場合、最初の行から住所情報を使用して保護者を作成
                    first_row = group.iloc[0]
                    guardian_data = first_row
                else:
                    guardian_data = guardian_rows.iloc[0]

                # 保護者を作成
                try:
                    guardian = Guardian(
                        tenant_id=tenant.id,
                        old_id=guardian_old_id,
                        last_name=str(guardian_data['苗字']) if not pd.isna(guardian_data['苗字']) else '',
                        first_name=str(guardian_data['お名前']) if not pd.isna(guardian_data['お名前']) else '',
                        last_name_kana=str(guardian_data['苗字(ヨミ)']) if not pd.isna(guardian_data['苗字(ヨミ)']) else '',
                        first_name_kana=str(guardian_data['お名前(ヨミ)']) if not pd.isna(guardian_data['お名前(ヨミ)']) else '',
                        last_name_roman=str(guardian_data['苗字(ローマ字)']) if not pd.isna(guardian_data['苗字(ローマ字)']) else '',
                        first_name_roman=str(guardian_data['お名前(ローマ字)']) if not pd.isna(guardian_data['お名前(ローマ字)']) else '',
                        email=str(guardian_data['メールアドレス']) if not pd.isna(guardian_data['メールアドレス']) else '',
                        phone=normalize_phone(guardian_data['電話1番号']),
                        phone_mobile=normalize_phone(guardian_data['電話2番号']),
                        postal_code=normalize_postal_code(guardian_data['郵便番号']),
                        prefecture=str(guardian_data['都道府県']) if not pd.isna(guardian_data['都道府県']) else '',
                        city=str(guardian_data['市区町村']) if not pd.isna(guardian_data['市区町村']) else '',
                        address1=str(guardian_data['番地']) if not pd.isna(guardian_data['番地']) else '',
                        address2=str(guardian_data['建物・部屋番号']) if not pd.isna(guardian_data['建物・部屋番号']) else '',
                        workplace=str(guardian_data['勤務先1']) if not pd.isna(guardian_data['勤務先1']) else '',
                        workplace2=str(guardian_data['勤務先2']) if not pd.isna(guardian_data['勤務先2']) else '',
                    )

                    # 最寄り校舎を設定
                    if not pd.isna(guardian_data['近くの校舎']):
                        school = find_school_by_name(guardian_data['近くの校舎'], tenant)
                        if school:
                            guardian.nearest_school = school

                    if not dry_run:
                        guardian.save()

                    guardian_map[guardian_old_id] = guardian
                    created_guardians += 1

                except Exception as e:
                    errors.append(f"保護者作成エラー (ID:{guardian_old_id}): {str(e)}")
                    continue

            # 生徒を作成（子の行）
            student_rows = group[group['保護者との続柄'] == '子']

            for idx, row in student_rows.iterrows():
                student_old_id = str(int(row['個人ID']) if not pd.isna(row['個人ID']) else 0)

                if student_old_id in existing_students:
                    # 既存の生徒がいる場合はスキップ
                    continue

                try:
                    student = Student(
                        tenant_id=tenant.id,
                        old_id=student_old_id,
                        last_name=str(row['苗字']) if not pd.isna(row['苗字']) else '',
                        first_name=str(row['お名前']) if not pd.isna(row['お名前']) else '',
                        last_name_kana=str(row['苗字(ヨミ)']) if not pd.isna(row['苗字(ヨミ)']) else '',
                        first_name_kana=str(row['お名前(ヨミ)']) if not pd.isna(row['お名前(ヨミ)']) else '',
                        last_name_roman=str(row['苗字(ローマ字)']) if not pd.isna(row['苗字(ローマ字)']) else '',
                        first_name_roman=str(row['お名前(ローマ字)']) if not pd.isna(row['お名前(ローマ字)']) else '',
                        nickname=str(row['ニックネーム']) if not pd.isna(row['ニックネーム']) else '',
                        birth_date=parse_date(row['生年月日']),
                        gender=get_gender(row['性別']),
                        school_name=str(row['現在の学校名']) if not pd.isna(row['現在の学校名']) else '',
                        grade_text=str(row['現在の学年']) if not pd.isna(row['現在の学年']) else '',
                        status=get_status_from_state(row['状態']),
                        contract_status=str(int(row['契約ステータス'])) if not pd.isna(row['契約ステータス']) else '',
                        email=str(row['メールアドレス']) if not pd.isna(row['メールアドレス']) else '',
                        phone=normalize_phone(row['電話1番号']),
                        phone2=normalize_phone(row['電話2番号']),
                        postal_code=normalize_postal_code(row['郵便番号']),
                        prefecture=str(row['都道府県']) if not pd.isna(row['都道府県']) else '',
                        city=str(row['市区町村']) if not pd.isna(row['市区町村']) else '',
                        address1=str(row['番地']) if not pd.isna(row['番地']) else '',
                        address2=str(row['建物・部屋番号']) if not pd.isna(row['建物・部屋番号']) else '',
                        guardian=guardian,
                        registered_date=parse_date(row['登録日時']),
                    )

                    # 紹介者ID
                    if not pd.isna(row['招待者保護者ID']):
                        student.referrer_old_id = str(int(row['招待者保護者ID']))

                    # 主所属校舎を設定
                    if not pd.isna(row['近くの校舎']):
                        school = find_school_by_name(row['近くの校舎'], tenant)
                        if school:
                            student.primary_school = school

                    if not dry_run:
                        student.save()

                    existing_students[student_old_id] = student
                    created_students += 1

                    # StudentGuardian関連を作成
                    if not dry_run:
                        StudentGuardian.objects.get_or_create(
                            tenant_id=tenant.id,
                            student=student,
                            guardian=guardian,
                            defaults={
                                'relationship': Guardian.Relationship.OTHER,
                                'is_primary': True,
                                'is_billing_target': True,
                            }
                        )
                    created_relations += 1

                except Exception as e:
                    errors.append(f"生徒作成エラー (ID:{student_old_id}): {str(e)}")
                    import traceback
                    traceback.print_exc()

        if dry_run:
            print("\n=== ドライラン結果 ===")
            print(f"作成予定の保護者数: {created_guardians}")
            print(f"作成予定の生徒数: {created_students}")
            print(f"作成予定の関連数: {created_relations}")
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
            print(f"作成した保護者数: {created_guardians}")
            print(f"作成した生徒数: {created_students}")
            print(f"作成した関連数: {created_relations}")
            if errors:
                print(f"\nエラー数: {len(errors)}")
                for err in errors[:10]:
                    print(f"  - {err}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='生徒・保護者インポート')
    parser.add_argument('--execute', action='store_true', help='実際にインポートを実行')
    args = parser.parse_args()

    if args.execute:
        print("実際のインポートを実行します...")
        import_data(dry_run=False)
    else:
        print("ドライランモード（--execute で実行）")
        import_data(dry_run=True)
