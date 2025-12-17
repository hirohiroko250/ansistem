"""
生徒データインポートスクリプト
使用方法: docker compose run --rm backend python scripts/import_students.py <csv_path>
"""
import csv
import sys
import os
import django
from datetime import datetime

# Django設定
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.students.models import Student, Guardian, StudentGuardian
from apps.tenants.models import Tenant


def parse_date(date_str):
    """日付をパース"""
    if not date_str:
        return None
    date_str = date_str.strip()
    # 全角数字を半角に
    date_str = date_str.translate(str.maketrans('０１２３４５６７８９', '0123456789'))

    formats = ['%Y/%m/%d', '%Y-%m-%d', '%Y年%m月%d日', '%m/%d/%Y']
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def convert_gender(gender_str):
    """性別を変換"""
    if not gender_str:
        return ''
    gender_str = gender_str.strip()
    if gender_str in ['男', '男性', 'M', 'Male']:
        return 'male'
    elif gender_str in ['女', '女性', 'F', 'Female']:
        return 'female'
    return ''


def convert_status(status_str):
    """契約ステータスを変換"""
    if not status_str:
        return 'registered'
    status_str = status_str.strip()
    if '受講' in status_str:
        return 'enrolled'
    elif '休会' in status_str:
        return 'suspended'
    elif '退会' in status_str:
        return 'withdrawn'
    elif '体験' in status_str or 'テスト' in status_str:
        return 'trial'
    return 'registered'


def import_students(csv_path):
    """CSVから生徒データをインポート"""

    # アンイングリッシュグループテナント取得
    tenant = Tenant.objects.filter(tenant_code='100000').first()
    if not tenant:
        print("エラー: アンイングリッシュグループテナントが見つかりません")
        sys.exit(1)
    tenant_id = tenant.id
    print(f"テナント: {tenant.tenant_name} ({tenant_id})")

    # 保護者のold_id -> idマッピングを作成
    guardian_map = {}
    for g in Guardian.objects.filter(tenant_id=tenant_id).values('id', 'old_id'):
        if g['old_id']:
            guardian_map[g['old_id']] = g['id']
    print(f"保護者マッピング作成完了: {len(guardian_map)} 件")

    imported = 0
    updated = 0
    errors = []
    guardian_linked = 0

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):
            try:
                student_id = row.get('個人ID', '').strip()
                if not student_id:
                    continue

                # 既存チェック（old_idで）
                existing = Student.objects.filter(old_id=student_id).first()

                # 保護者取得
                guardian_old_id = row.get('保護者ID', '').strip()
                guardian_id = guardian_map.get(guardian_old_id)

                # データ準備
                data = {
                    'tenant_id': tenant_id,
                    'student_no': student_id,
                    'old_id': student_id,
                    'last_name': row.get('苗字', '').strip() or '未設定',
                    'first_name': row.get('お名前', '').strip() or '未設定',
                    'last_name_kana': row.get('苗字(ヨミ)', '').strip() or '',
                    'first_name_kana': row.get('お名前(ヨミ)', '').strip() or '',
                    'last_name_roman': row.get('苗字(ローマ字)', '').strip() or '',
                    'first_name_roman': row.get('お名前(ローマ字)', '').strip() or '',
                    'nickname': row.get('ニﾂクネーム', '').strip() or '',
                    'email': row.get('メールアドレス', '').strip() or '',
                    'gender': convert_gender(row.get('性別', '')),
                    'birth_date': parse_date(row.get('生年月日', '')),
                    'school_name': row.get('現在の学校名', '').strip() or '',
                    'grade_text': row.get('現在の学年', '').strip() or '',
                    'contract_status': row.get('契約ステータス①受講中\n②休会\n③お知らせ会員\n④テスト会員\n⑤ダミー\n⑥ALL退会\n⑦社員用（支払無し）\n⑧業務', '').strip() or '',
                    'status': convert_status(row.get('契約ステータス①受講中\n②休会\n③お知らせ会員\n④テスト会員\n⑤ダミー\n⑥ALL退会\n⑦社員用（支払無し）\n⑧業務', '')),
                    'registered_date': parse_date(row.get('個人ID作成日', '')),
                    'notes': '',
                }

                # 保護者紐付け
                if guardian_id:
                    data['guardian_id'] = guardian_id

                if existing:
                    # 更新
                    for key, value in data.items():
                        setattr(existing, key, value)
                    existing.save()
                    updated += 1
                    student = existing
                else:
                    # 新規作成
                    student = Student.objects.create(**data)
                    imported += 1

                # StudentGuardian（生徒保護者関連）の作成
                if guardian_id:
                    sg, created = StudentGuardian.objects.get_or_create(
                        student=student,
                        guardian_id=guardian_id,
                        defaults={
                            'tenant_id': tenant_id,
                            'is_primary': True,
                            'is_billing_target': True,
                            'is_emergency_contact': True,
                        }
                    )
                    if created:
                        guardian_linked += 1

                if (imported + updated) % 100 == 0:
                    print(f"  処理中... {imported + updated} 件")

            except Exception as e:
                errors.append(f"行 {row_num}: {student_id} - {str(e)}")
                continue

    return imported, updated, guardian_linked, errors


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python scripts/import_students.py <csv_path>")
        sys.exit(1)

    csv_path = sys.argv[1]

    if not os.path.exists(csv_path):
        print(f"エラー: ファイルが見つかりません: {csv_path}")
        sys.exit(1)

    print(f"インポート開始: {csv_path}")
    print("-" * 50)

    imported, updated, guardian_linked, errors = import_students(csv_path)

    print("-" * 50)
    print(f"完了!")
    print(f"  新規作成: {imported} 件")
    print(f"  更新: {updated} 件")
    print(f"  保護者紐付け: {guardian_linked} 件")

    if errors:
        print(f"  エラー: {len(errors)} 件")
        for error in errors[:10]:
            print(f"    - {error}")
        if len(errors) > 10:
            print(f"    ... 他 {len(errors) - 10} 件")
