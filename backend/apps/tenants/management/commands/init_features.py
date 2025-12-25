"""
機能マスタの初期データを作成するコマンド

Usage:
    python manage.py init_features
"""
from django.core.management.base import BaseCommand
from apps.tenants.models import FeatureMaster


# 初期機能一覧（OZAWorksベース）
DEFAULT_FEATURES = [
    # 基本機能
    {'code': '1000', 'name': '仕事クラス登録', 'category': '基本', 'order': 100},
    {'code': '2000', 'name': '生徒出欠簿', 'category': '基本', 'order': 200},
    {'code': '2010', 'name': '生徒出欠簿（講師削除ボタン）', 'parent': '2000', 'category': '基本', 'order': 201},
    {'code': '3000', 'name': '生徒検索', 'category': '基本', 'order': 300},
    {'code': '4000', 'name': '給与計算', 'category': '基本', 'order': 400},
    {'code': '5000', 'name': '新規作成', 'category': '基本', 'order': 500},
    {'code': '6000', 'name': 'お休み申請', 'category': '基本', 'order': 600},
    {'code': '7000', 'name': '請求（売上マージン）', 'category': '基本', 'order': 700},
    {'code': '8000', 'name': '作業一覧（権利別）', 'category': '基本', 'order': 800},
    {'code': '9000', 'name': 'クラス検索', 'category': '基本', 'order': 900},

    # クラス作成系
    {'code': '10010', 'name': '校舎マスタ', 'parent': '10000', 'category': 'クラス作成', 'order': 1001},
    {'code': '10020', 'name': 'ブランドマスタ', 'parent': '10000', 'category': 'クラス作成', 'order': 1002},
    {'code': '10030', 'name': '開催曜日設定', 'parent': '10000', 'category': 'クラス作成', 'order': 1003},
    {'code': '10040', 'name': 'クラス作成', 'parent': '10000', 'category': 'クラス作成', 'order': 1004},
    {'code': '10050', 'name': '時間割作成', 'parent': '10000', 'category': 'クラス作成', 'order': 1005},
    {'code': '10060', 'name': '時間割作成（日付指定）', 'parent': '10000', 'category': 'クラス作成', 'order': 1006},
    {'code': '10070', 'name': '教材マスタ', 'parent': '10000', 'category': 'クラス作成', 'order': 1007},
    {'code': '10080', 'name': '受入可否フラグマスタ', 'parent': '10000', 'category': 'クラス作成', 'order': 1008},
    {'code': '10090', 'name': 'カレンダー登録', 'parent': '10000', 'category': 'クラス作成', 'order': 1009},
    {'code': '10100', 'name': '対象学年登録', 'parent': '10000', 'category': 'クラス作成', 'order': 1010},
    {'code': '10110', 'name': 'ブランドメーリングリスト', 'parent': '10000', 'category': 'クラス作成', 'order': 1011},
    {'code': '10120', 'name': '伝言板関連カテゴリマスタ', 'parent': '10000', 'category': 'クラス作成', 'order': 1012},
    {'code': '10130', 'name': '限定公開機能', 'parent': '10000', 'category': 'クラス作成', 'order': 1013},

    # 運用系
    {'code': '11000', 'name': 'AB Swap運用中カレンダー', 'category': '運用', 'order': 1100},
    {'code': '12000', 'name': 'カレンダー作成', 'category': '運用', 'order': 1200},
    {'code': '13000', 'name': '講師検索', 'category': '運用', 'order': 1300},
    {'code': '14000', 'name': '商品マスタ', 'category': '運用', 'order': 1400},
    {'code': '15000', 'name': '権利付与', 'category': '運用', 'order': 1500},

    # 請求計算系
    {'code': '16010', 'name': '契約情報Excel取込み', 'parent': '16000', 'category': '請求計算', 'order': 1601},
    {'code': '16020', 'name': '口座取込（引落開始日設定）', 'parent': '16000', 'category': '請求計算', 'order': 1602},
    {'code': '16030', 'name': '封入記号設定', 'parent': '16000', 'category': '請求計算', 'order': 1603},
    {'code': '16041', 'name': '請求計算-仮計算', 'parent': '16000', 'category': '請求計算', 'order': 1604},
    {'code': '16042', 'name': '請求計算-請求明細ダウンロード', 'parent': '16000', 'category': '請求計算', 'order': 1605},
    {'code': '16043', 'name': '請求計算-確定計算', 'parent': '16000', 'category': '請求計算', 'order': 1606},
    {'code': '16044', 'name': '請求計算-請求書作成', 'parent': '16000', 'category': '請求計算', 'order': 1607},
    {'code': '16045', 'name': '請求計算-封入物チェック用名簿ダウンロード', 'parent': '16000', 'category': '請求計算', 'order': 1608},
    {'code': '16050', 'name': 'ワイドネット処理', 'parent': '16000', 'category': '請求計算', 'order': 1609},
    {'code': '16060', 'name': '振込処理', 'parent': '16000', 'category': '請求計算', 'order': 1610},

    # 管理系
    {'code': '17000', 'name': '画面制限マスタ', 'category': '管理', 'order': 1700},
    {'code': '18000', 'name': '伝言板（承認依頼）', 'category': '管理', 'order': 1800},
    {'code': '19000', 'name': '伝言板（送信済）', 'category': '管理', 'order': 1900},
    {'code': '20000', 'name': '日報照会', 'category': '管理', 'order': 2000},
    {'code': '21000', 'name': '日報照会（クラス別）', 'category': '管理', 'order': 2100},
    {'code': '22000', 'name': 'ボタン押下ログ', 'category': '管理', 'order': 2200},
    {'code': '23000', 'name': '給与種別マスタ', 'category': '管理', 'order': 2300},
]


class Command(BaseCommand):
    help = '機能マスタの初期データを作成'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant-id',
            type=str,
            help='テナントID（UUID）',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には作成せず、作成内容を表示のみ',
        )

    def handle(self, *args, **options):
        tenant_id = options.get('tenant_id')
        dry_run = options.get('dry_run')

        from apps.tenants.models import Tenant

        if not tenant_id:
            # デフォルトのテナントを使用
            tenant = Tenant.objects.first()
            if not tenant:
                self.stdout.write(self.style.ERROR('テナントが見つかりません。--tenant-id を指定してください。'))
                return
        else:
            tenant = Tenant.objects.filter(id=tenant_id).first()
            if not tenant:
                self.stdout.write(self.style.ERROR(f'テナントID {tenant_id} が見つかりません。'))
                return

        self.stdout.write(f"テナントID: {tenant.id}")

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for feature_data in DEFAULT_FEATURES:
            code = feature_data['code']
            name = feature_data['name']
            parent = feature_data.get('parent', '')
            category = feature_data.get('category', '')
            order = feature_data.get('order', 0)

            if dry_run:
                self.stdout.write(f"[DRY-RUN] {code}: {name} (カテゴリ: {category})")
                continue

            feature, created = FeatureMaster.objects.update_or_create(
                tenant_ref=tenant,
                tenant_id=tenant.id,
                feature_code=code,
                defaults={
                    'feature_name': name,
                    'parent_code': parent,
                    'category': category,
                    'display_order': order,
                    'is_active': True,
                }
            )

            if created:
                created_count += 1
                self.stdout.write(f"作成: {code} - {name}")
            else:
                updated_count += 1
                self.stdout.write(f"更新: {code} - {name}")

        self.stdout.write(self.style.SUCCESS(f"\n=== 処理結果 ==="))
        self.stdout.write(f"作成: {created_count}件")
        self.stdout.write(f"更新: {updated_count}件")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY-RUN モード] 実際の作成は行われていません"))
