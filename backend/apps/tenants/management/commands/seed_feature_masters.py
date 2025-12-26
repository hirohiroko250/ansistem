"""
Seed Feature Masters for Permission Settings
Based on the OZA system permission matrix
"""
from django.core.management.base import BaseCommand
from apps.tenants.models import FeatureMaster, Tenant


class Command(BaseCommand):
    help = 'Seed feature masters for permission settings'

    # 機能マスタ定義（HTMLから抽出）
    FEATURES = [
        # 基本機能
        {'code': '1000', 'name': '仕事クラス登録', 'category': '基本機能', 'order': 1},
        {'code': '2000', 'name': '生徒出欠簿', 'category': '基本機能', 'order': 2},
        {'code': '2010', 'name': '生徒出欠簿（講師削除ボタン）', 'category': '基本機能', 'order': 3, 'parent': '2000'},
        {'code': '3000', 'name': '生徒検索', 'category': '基本機能', 'order': 4},
        {'code': '4000', 'name': '給与計算', 'category': '基本機能', 'order': 5},
        {'code': '5000', 'name': '新規作成', 'category': '基本機能', 'order': 6},
        {'code': '6000', 'name': 'お休み申請', 'category': '基本機能', 'order': 7},
        {'code': '7000', 'name': '請求（売上マージン）', 'category': '基本機能', 'order': 8},
        {'code': '8000', 'name': '作業一覧（権利別）', 'category': '基本機能', 'order': 9},
        {'code': '9000', 'name': 'クラス検索', 'category': '基本機能', 'order': 10},

        # クラス作成関連
        {'code': '10010', 'name': '校舎マスタ', 'category': 'クラス作成', 'order': 11, 'parent': '10000'},
        {'code': '10020', 'name': 'ブランドマスタ', 'category': 'クラス作成', 'order': 12, 'parent': '10000'},
        {'code': '10030', 'name': '開催曜日設定', 'category': 'クラス作成', 'order': 13, 'parent': '10000'},
        {'code': '10040', 'name': 'クラス作成', 'category': 'クラス作成', 'order': 14, 'parent': '10000'},
        {'code': '10050', 'name': '時間割作成', 'category': 'クラス作成', 'order': 15, 'parent': '10000'},
        {'code': '10060', 'name': '時間割作成（日付指定）', 'category': 'クラス作成', 'order': 16, 'parent': '10000'},
        {'code': '10070', 'name': '教材マスタ', 'category': 'クラス作成', 'order': 17, 'parent': '10000'},
        {'code': '10080', 'name': '受入可否フラグマスタ', 'category': 'クラス作成', 'order': 18, 'parent': '10000'},
        {'code': '10090', 'name': 'カレンダー登録', 'category': 'クラス作成', 'order': 19, 'parent': '10000'},
        {'code': '10100', 'name': '対象学年登録', 'category': 'クラス作成', 'order': 20, 'parent': '10000'},
        {'code': '10110', 'name': 'ブランドメーリングリスト', 'category': 'クラス作成', 'order': 21, 'parent': '10000'},
        {'code': '10120', 'name': '伝言板関連カテゴリマスタ', 'category': 'クラス作成', 'order': 22, 'parent': '10000'},
        {'code': '10130', 'name': '限定公開機能', 'category': 'クラス作成', 'order': 23, 'parent': '10000'},

        # 運用機能
        {'code': '11000', 'name': 'AB Swap運用中カレンダー', 'category': '運用機能', 'order': 24},
        {'code': '12000', 'name': 'カレンダー作成', 'category': '運用機能', 'order': 25},
        {'code': '13000', 'name': '講師検索', 'category': '運用機能', 'order': 26},
        {'code': '14000', 'name': '商品マスタ', 'category': '運用機能', 'order': 27},
        {'code': '15000', 'name': '権利付与', 'category': '運用機能', 'order': 28},

        # 請求計算
        {'code': '16010', 'name': '契約情報Excel取込み', 'category': '請求計算', 'order': 29, 'parent': '16000'},
        {'code': '16020', 'name': '口座取込（引落開始日設定）', 'category': '請求計算', 'order': 30, 'parent': '16000'},
        {'code': '16030', 'name': '封入記号設定', 'category': '請求計算', 'order': 31, 'parent': '16000'},
        {'code': '16041', 'name': '請求計算-仮計算', 'category': '請求計算', 'order': 32, 'parent': '16000'},
        {'code': '16042', 'name': '請求計算-請求明細ダウンロード', 'category': '請求計算', 'order': 33, 'parent': '16000'},
        {'code': '16043', 'name': '請求計算-確定計算', 'category': '請求計算', 'order': 34, 'parent': '16000'},
        {'code': '16044', 'name': '請求計算-請求書作成', 'category': '請求計算', 'order': 35, 'parent': '16000'},
        {'code': '16045', 'name': '請求計算-封入物チェック用名簿ダウンロード', 'category': '請求計算', 'order': 36, 'parent': '16000'},
        {'code': '16050', 'name': 'ワイドネット処理', 'category': '請求計算', 'order': 37, 'parent': '16000'},
        {'code': '16060', 'name': '振込処理', 'category': '請求計算', 'order': 38, 'parent': '16000'},

        # 管理機能
        {'code': '17000', 'name': '画面制限マスタ', 'category': '管理機能', 'order': 39},
        {'code': '18000', 'name': '伝言板（承認依頼）', 'category': '管理機能', 'order': 40},
        {'code': '19000', 'name': '伝言板（送信済）', 'category': '管理機能', 'order': 41},
        {'code': '20000', 'name': '日報照会', 'category': '管理機能', 'order': 42},
        {'code': '21000', 'name': '日報照会クラス別', 'category': '管理機能', 'order': 43},
        {'code': '22000', 'name': 'ボタン押下ログ', 'category': '管理機能', 'order': 44},
        {'code': '23000', 'name': '給与種別マスタ', 'category': '管理機能', 'order': 45},
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Tenant code to seed features for (default: all tenants)',
        )

    def handle(self, *args, **options):
        tenant_code = options.get('tenant')

        if tenant_code:
            tenants = Tenant.objects.filter(tenant_code=tenant_code)
            if not tenants.exists():
                self.stderr.write(self.style.ERROR(f'Tenant not found: {tenant_code}'))
                return
        else:
            tenants = Tenant.objects.filter(is_active=True)

        for tenant in tenants:
            self.stdout.write(f'Seeding features for tenant: {tenant.tenant_name}')

            created_count = 0
            updated_count = 0

            for feature_data in self.FEATURES:
                feature, created = FeatureMaster.objects.update_or_create(
                    tenant_ref=tenant,
                    tenant_id=tenant.id,
                    feature_code=feature_data['code'],
                    defaults={
                        'feature_name': feature_data['name'],
                        'category': feature_data['category'],
                        'parent_code': feature_data.get('parent', ''),
                        'display_order': feature_data['order'],
                        'is_active': True,
                    }
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            self.stdout.write(self.style.SUCCESS(
                f'  Created: {created_count}, Updated: {updated_count}'
            ))

        self.stdout.write(self.style.SUCCESS('Feature masters seeded successfully!'))
