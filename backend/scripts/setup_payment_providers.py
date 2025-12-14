#!/usr/bin/env python
"""
決済代行会社の初期データ投入スクリプト

Usage:
    python manage.py shell < scripts/setup_payment_providers.py
    または
    python manage.py runscript setup_payment_providers
"""
import sys
import django

# Django環境のセットアップ（必要な場合）
if 'django' not in sys.modules or not django.conf.settings.configured:
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
    django.setup()

from apps.billing.models import PaymentProvider


def setup_payment_providers(tenant_id=0):
    """決済代行会社の初期データを投入"""

    providers_data = [
        {
            'code': 'ufj_factor',
            'name': 'UFJファクター',
            'consignor_code': '',  # 実際の委託者コードは設定画面で入力
            'default_bank_code': '',
            'file_encoding': 'shift_jis',
            'closing_day': 25,
            'debit_day': 27,
            'sort_order': 1,
            'notes': '三菱UFJファクター株式会社',
        },
        {
            'code': 'jaccs',
            'name': 'JACCS',
            'consignor_code': '',
            'default_bank_code': '',
            'file_encoding': 'shift_jis',
            'closing_day': 25,
            'debit_day': 27,
            'sort_order': 2,
            'notes': '株式会社ジャックス',
        },
        {
            'code': 'chukyo_finance',
            'name': '中京ファイナンス',
            'consignor_code': '',
            'default_bank_code': '',
            'file_encoding': 'shift_jis',
            'closing_day': 25,
            'debit_day': 27,
            'sort_order': 3,
            'notes': '中京ファイナンス株式会社',
        },
    ]

    created_count = 0
    updated_count = 0

    for data in providers_data:
        code = data.pop('code')
        provider, created = PaymentProvider.objects.update_or_create(
            tenant_id=tenant_id,
            code=code,
            defaults=data
        )

        if created:
            print(f"Created: {provider.name} ({code})")
            created_count += 1
        else:
            print(f"Updated: {provider.name} ({code})")
            updated_count += 1

    print(f"\n完了: 作成 {created_count}件, 更新 {updated_count}件")
    return created_count, updated_count


if __name__ == '__main__':
    setup_payment_providers()
