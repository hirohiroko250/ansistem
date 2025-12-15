"""
OZAパスワードをインポートするスクリプト

Usage:
    python scripts/import_oza_passwords.py --file /path/to/excel.xlsx
    python scripts/import_oza_passwords.py --file /path/to/excel.xlsx --execute

デフォルトはdry-runモードで、--executeオプションで実際にインポートします。
"""
import os
import sys
import django
import argparse

# Django設定
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

import pandas as pd
from django.contrib.auth import get_user_model
from apps.students.models import Guardian
from apps.tenants.models import Tenant

User = get_user_model()


def normalize_phone(phone):
    """電話番号を正規化（ハイフン除去）"""
    if not phone:
        return ''
    return str(phone).replace('-', '').replace(' ', '').replace('　', '').strip()


def import_oza_passwords(file_path, dry_run=True, tenant_id=None):
    """OZAパスワードをインポート"""
    print("=" * 60)
    print("OZAパスワードインポート")
    print("=" * 60)
    print(f"ファイル: {file_path}")
    print(f"モード: {'DRY-RUN（実行しない）' if dry_run else '本番実行'}")
    print()

    # テナント取得
    if tenant_id:
        tenant = Tenant.objects.filter(id=tenant_id).first()
    else:
        # 保護者が最も多いテナントを取得
        from django.db.models import Count
        tenant_with_most = Guardian.objects.values('tenant_id').annotate(
            count=Count('id')
        ).order_by('-count').first()
        if tenant_with_most:
            tenant = Tenant.objects.filter(id=tenant_with_most['tenant_id']).first()
        else:
            tenant = Tenant.objects.first()

    if not tenant:
        print("エラー: テナントが見つかりません")
        return

    print(f"テナント: {tenant.id}")
    print()

    # Excelファイル読み込み
    df = pd.read_excel(file_path)
    print(f"読み込んだ行数: {len(df)}")
    print()

    # 保護者IDでグループ化して重複を除去（最初の行を使用）
    df_unique = df.drop_duplicates(subset=['保護者ID'], keep='first')
    print(f"ユニークな保護者数: {len(df_unique)}")
    print()

    # 統計
    created_users = 0
    updated_users = 0
    linked_guardians = 0
    not_found = 0
    already_has_user = 0
    errors = []

    for idx, row in df_unique.iterrows():
        guardian_no = str(row['保護者ID']).strip()
        phone1 = normalize_phone(row.get('電話番号１', ''))
        login_id = str(row.get('ログインID', '')).strip()
        login_pw = str(row.get('ログインPW', '')).strip()

        if not guardian_no or not login_pw:
            continue

        # 保護者を検索（guardian_no, old_id, または電話番号）
        guardian = Guardian.objects.filter(
            tenant_id=tenant.id,
            guardian_no=guardian_no
        ).first()

        if not guardian:
            guardian = Guardian.objects.filter(
                tenant_id=tenant.id,
                old_id=guardian_no
            ).first()

        if not guardian and phone1:
            # 電話番号で検索（ハイフンあり・なし両方）
            guardian = Guardian.objects.filter(
                tenant_id=tenant.id,
                phone_mobile=phone1
            ).first()
            if not guardian:
                phone_with_hyphen = f"{phone1[:3]}-{phone1[3:7]}-{phone1[7:]}" if len(phone1) == 11 else phone1
                guardian = Guardian.objects.filter(
                    tenant_id=tenant.id,
                    phone_mobile=phone_with_hyphen
                ).first()

        if not guardian:
            not_found += 1
            if not_found <= 10:
                print(f"  保護者が見つかりません: {guardian_no} ({phone1})")
            continue

        # 既にユーザーがリンクされているか確認
        has_user = False
        if guardian.user_id:
            try:
                if guardian.user:
                    # パスワードを更新
                    if not dry_run:
                        guardian.user.set_password(login_pw)
                        guardian.user.save()
                    updated_users += 1
                    if updated_users <= 5:
                        print(f"  パスワード更新: {guardian_no} ({guardian.last_name} {guardian.first_name})")
                    has_user = True
            except User.DoesNotExist:
                # user_idは設定されているがUserが存在しない場合、リンクを解除
                if not dry_run:
                    Guardian.objects.filter(pk=guardian.pk).update(user=None)

        if has_user:
            continue

        # 新しいユーザーを作成
        # メールアドレスがない場合は仮のメールアドレスを生成
        email = guardian.email
        if not email:
            email = f"guardian_{guardian_no}@temp.local"

        # メールアドレスが既に使われているかチェック
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            # 既存ユーザーをリンク
            if not dry_run:
                existing_user.set_password(login_pw)
                existing_user.save()
                guardian.user = existing_user
                guardian.save(update_fields=['user'])
            linked_guardians += 1
            if linked_guardians <= 5:
                print(f"  既存ユーザーをリンク: {guardian_no} -> {email}")
        else:
            # 新しいユーザーを作成
            if not dry_run:
                user = User.objects.create_user(
                    email=email,
                    password=login_pw,
                    tenant_id=tenant.id,
                    user_type='GUARDIAN',
                    first_name=guardian.first_name,
                    last_name=guardian.last_name,
                    is_active=True,
                )
                guardian.user = user
                guardian.save(update_fields=['user'])
            created_users += 1
            if created_users <= 5:
                print(f"  ユーザー作成: {guardian_no} ({guardian.last_name} {guardian.first_name}) -> {email}")

    print()
    print("=" * 60)
    print("結果サマリー")
    print("=" * 60)
    print(f"ユーザー新規作成: {created_users}件")
    print(f"パスワード更新: {updated_users}件")
    print(f"既存ユーザーリンク: {linked_guardians}件")
    print(f"保護者が見つからない: {not_found}件")

    if dry_run:
        print()
        print("※ DRY-RUNモードです。実際に実行するには --execute オプションを追加してください")

    return {
        'created': created_users,
        'updated': updated_users,
        'linked': linked_guardians,
        'not_found': not_found,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='OZAパスワードインポート')
    parser.add_argument('--file', required=True, help='Excelファイルのパス')
    parser.add_argument('--execute', action='store_true', help='実際に実行する（デフォルトはdry-run）')
    parser.add_argument('--tenant', help='テナントID（省略時は自動検出）')
    args = parser.parse_args()

    import_oza_passwords(
        file_path=args.file,
        dry_run=not args.execute,
        tenant_id=args.tenant
    )
