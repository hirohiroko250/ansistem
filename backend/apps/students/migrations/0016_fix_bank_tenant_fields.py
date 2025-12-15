# Generated manually - add missing tenant fields to bank tables
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
        ('students', '0015_fix_bank_table_names'),
    ]

    operations = [
        # Fix t15_bank_accounts - drop and recreate tenant_id as UUID
        migrations.RunSQL(
            sql='''
                ALTER TABLE t15_bank_accounts DROP COLUMN IF EXISTS tenant_id;
                ALTER TABLE t15_bank_accounts ADD COLUMN tenant_id uuid;
                CREATE INDEX IF NOT EXISTS t15_bank_accounts_tenant_id_idx ON t15_bank_accounts(tenant_id);
            ''',
            reverse_sql='''
                ALTER TABLE t15_bank_accounts DROP COLUMN IF EXISTS tenant_id;
                ALTER TABLE t15_bank_accounts ADD COLUMN tenant_id integer DEFAULT 100000;
            ''',
        ),
        # Add tenant_ref_id column to t15_bank_accounts
        migrations.RunSQL(
            sql='''
                ALTER TABLE t15_bank_accounts
                ADD COLUMN IF NOT EXISTS tenant_ref_id uuid NULL
                REFERENCES tenants(id) ON DELETE SET NULL;
            ''',
            reverse_sql='ALTER TABLE t15_bank_accounts DROP COLUMN IF EXISTS tenant_ref_id;',
        ),
        # Add deleted_at column to t15_bank_accounts
        migrations.RunSQL(
            sql='ALTER TABLE t15_bank_accounts ADD COLUMN IF NOT EXISTS deleted_at timestamp with time zone NULL;',
            reverse_sql='ALTER TABLE t15_bank_accounts DROP COLUMN IF EXISTS deleted_at;',
        ),
        # Fix t16_bank_account_requests - drop and recreate tenant_id as UUID
        migrations.RunSQL(
            sql='''
                ALTER TABLE t16_bank_account_requests DROP COLUMN IF EXISTS tenant_id;
                ALTER TABLE t16_bank_account_requests ADD COLUMN tenant_id uuid;
                CREATE INDEX IF NOT EXISTS t16_bank_account_requests_tenant_id_idx ON t16_bank_account_requests(tenant_id);
            ''',
            reverse_sql='''
                ALTER TABLE t16_bank_account_requests DROP COLUMN IF EXISTS tenant_id;
                ALTER TABLE t16_bank_account_requests ADD COLUMN tenant_id integer DEFAULT 100000;
            ''',
        ),
        # Add tenant_ref_id column to t16_bank_account_requests
        migrations.RunSQL(
            sql='''
                ALTER TABLE t16_bank_account_requests
                ADD COLUMN IF NOT EXISTS tenant_ref_id uuid NULL
                REFERENCES tenants(id) ON DELETE SET NULL;
            ''',
            reverse_sql='ALTER TABLE t16_bank_account_requests DROP COLUMN IF EXISTS tenant_ref_id;',
        ),
        # Add deleted_at column to t16_bank_account_requests
        migrations.RunSQL(
            sql='ALTER TABLE t16_bank_account_requests ADD COLUMN IF NOT EXISTS deleted_at timestamp with time zone NULL;',
            reverse_sql='ALTER TABLE t16_bank_account_requests DROP COLUMN IF EXISTS deleted_at;',
        ),
    ]
