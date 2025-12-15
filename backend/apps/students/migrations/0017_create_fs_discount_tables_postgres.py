# Generated manually - create FS discount tables for PostgreSQL
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0016_fix_bank_tenant_fields'),
    ]

    operations = [
        # FriendshipRegistration テーブル作成
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS t17_friendship_registrations (
                id uuid PRIMARY KEY,
                tenant_id uuid,
                tenant_ref_id uuid NULL REFERENCES tenants(id) ON DELETE SET NULL,
                deleted_at timestamp with time zone NULL,
                requester_id uuid NOT NULL REFERENCES t01_guardians(id) ON DELETE CASCADE,
                target_id uuid NOT NULL REFERENCES t01_guardians(id) ON DELETE CASCADE,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                requested_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
                accepted_at timestamp with time zone NULL,
                friend_code VARCHAR(20) DEFAULT '',
                notes TEXT DEFAULT '',
                created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(requester_id, target_id)
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS t17_friendship_registrations;",
        ),
        # FriendshipRegistration インデックス
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS idx_friendship_tenant ON t17_friendship_registrations(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_friendship_requester ON t17_friendship_registrations(requester_id);
            CREATE INDEX IF NOT EXISTS idx_friendship_target ON t17_friendship_registrations(target_id);
            CREATE INDEX IF NOT EXISTS idx_friendship_status ON t17_friendship_registrations(status);
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS idx_friendship_tenant;
            DROP INDEX IF EXISTS idx_friendship_requester;
            DROP INDEX IF EXISTS idx_friendship_target;
            DROP INDEX IF EXISTS idx_friendship_status;
            """,
        ),
        # FSDiscount テーブル作成
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS t18_fs_discounts (
                id uuid PRIMARY KEY,
                tenant_id uuid,
                tenant_ref_id uuid NULL REFERENCES tenants(id) ON DELETE SET NULL,
                deleted_at timestamp with time zone NULL,
                guardian_id uuid NOT NULL REFERENCES t01_guardians(id) ON DELETE CASCADE,
                friendship_id uuid NOT NULL REFERENCES t17_friendship_registrations(id) ON DELETE CASCADE,
                discount_type VARCHAR(20) NOT NULL DEFAULT 'fixed',
                discount_value DECIMAL(10,2) NOT NULL DEFAULT 0,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                valid_from DATE NOT NULL,
                valid_until DATE NULL,
                used_at timestamp with time zone NULL,
                used_invoice_id uuid NULL,
                applied_amount DECIMAL(10,0) NULL,
                notes TEXT DEFAULT '',
                created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """,
            reverse_sql="DROP TABLE IF EXISTS t18_fs_discounts;",
        ),
        # FSDiscount インデックス
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS idx_fsdiscount_tenant ON t18_fs_discounts(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_fsdiscount_guardian ON t18_fs_discounts(guardian_id);
            CREATE INDEX IF NOT EXISTS idx_fsdiscount_friendship ON t18_fs_discounts(friendship_id);
            CREATE INDEX IF NOT EXISTS idx_fsdiscount_status ON t18_fs_discounts(status);
            CREATE INDEX IF NOT EXISTS idx_fsdiscount_valid_from ON t18_fs_discounts(valid_from);
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS idx_fsdiscount_tenant;
            DROP INDEX IF EXISTS idx_fsdiscount_guardian;
            DROP INDEX IF EXISTS idx_fsdiscount_friendship;
            DROP INDEX IF EXISTS idx_fsdiscount_status;
            DROP INDEX IF EXISTS idx_fsdiscount_valid_from;
            """,
        ),
    ]
