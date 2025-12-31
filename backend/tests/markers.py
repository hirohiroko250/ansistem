"""
テストマーカー - 共通のpytestマーカー設定
"""
import os
import pytest

# PostgreSQL環境でのみ実行
requires_postgres = pytest.mark.skipif(
    not os.environ.get('USE_POSTGRES_FOR_TESTS'),
    reason="Requires PostgreSQL. Set USE_POSTGRES_FOR_TESTS=1 or run in Docker."
)

# DBテストのマーカー（PostgreSQL必須）
db_test = [
    pytest.mark.django_db,
    requires_postgres,
]
