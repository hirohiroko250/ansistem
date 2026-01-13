"""
Pytest fixtures for pricing tests
"""
import pytest
from decimal import Decimal
from datetime import date

import django
from django.conf import settings


def pytest_configure():
    """Django設定を初期化"""
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.auth',
            ],
        )
        django.setup()


@pytest.fixture
def sample_start_date():
    """サンプル開始日"""
    return date(2026, 1, 7)


@pytest.fixture
def sample_days_of_week():
    """サンプル曜日リスト（月水金）"""
    return [1, 3, 5]
