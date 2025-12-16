"""
友達登録・FS割引モデル追加マイグレーション
"""
from django.db import migrations


class Migration(migrations.Migration):
    """FS割引用テーブル追加 - 0013で作成されるため空"""

    dependencies = [
        ('students', '0010_merge_0002_initial_0009_add_brands_many_to_many'),
    ]

    operations = [
        # テーブルは0013_add_discount_operation_logで作成される
    ]
