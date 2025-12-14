"""
友達登録・FS割引モデル追加マイグレーション
"""
from django.db import migrations


class Migration(migrations.Migration):
    """FS割引用テーブル追加"""

    dependencies = [
        ('students', '0010_merge_0002_initial_0009_add_brands_many_to_many'),
    ]

    operations = [
        # FriendshipRegistration テーブル作成
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS t17_friendship_registrations (
                id CHAR(32) PRIMARY KEY,
                tenant_id INTEGER NOT NULL,
                tenant_ref_id CHAR(32) NULL,
                requester_id CHAR(32) NOT NULL REFERENCES t01_guardians(id),
                target_id CHAR(32) NOT NULL REFERENCES t01_guardians(id),
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                accepted_at DATETIME NULL,
                friend_code VARCHAR(20) DEFAULT '',
                notes TEXT DEFAULT '',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(requester_id, target_id)
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS t17_friendship_registrations;",
        ),
        # FriendshipRegistration インデックス
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS idx_friendship_requester ON t17_friendship_registrations(requester_id);
            CREATE INDEX IF NOT EXISTS idx_friendship_target ON t17_friendship_registrations(target_id);
            CREATE INDEX IF NOT EXISTS idx_friendship_status ON t17_friendship_registrations(status);
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS idx_friendship_requester;
            DROP INDEX IF EXISTS idx_friendship_target;
            DROP INDEX IF EXISTS idx_friendship_status;
            """,
        ),
        # FSDiscount テーブル作成
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS t18_fs_discounts (
                id CHAR(32) PRIMARY KEY,
                tenant_id INTEGER NOT NULL,
                tenant_ref_id CHAR(32) NULL,
                guardian_id CHAR(32) NOT NULL REFERENCES t01_guardians(id),
                friendship_id CHAR(32) NOT NULL REFERENCES t17_friendship_registrations(id),
                discount_type VARCHAR(20) NOT NULL DEFAULT 'fixed',
                discount_value DECIMAL(10,2) NOT NULL DEFAULT 0,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                valid_from DATE NOT NULL,
                valid_until DATE NULL,
                used_at DATETIME NULL,
                used_invoice_id CHAR(32) NULL,
                applied_amount DECIMAL(10,0) NULL,
                notes TEXT DEFAULT '',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS t18_fs_discounts;",
        ),
        # FSDiscount インデックス
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS idx_fsdiscount_guardian ON t18_fs_discounts(guardian_id);
            CREATE INDEX IF NOT EXISTS idx_fsdiscount_friendship ON t18_fs_discounts(friendship_id);
            CREATE INDEX IF NOT EXISTS idx_fsdiscount_status ON t18_fs_discounts(status);
            CREATE INDEX IF NOT EXISTS idx_fsdiscount_valid_from ON t18_fs_discounts(valid_from);
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS idx_fsdiscount_guardian;
            DROP INDEX IF EXISTS idx_fsdiscount_friendship;
            DROP INDEX IF EXISTS idx_fsdiscount_status;
            DROP INDEX IF EXISTS idx_fsdiscount_valid_from;
            """,
        ),
    ]
