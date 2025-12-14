# Generated manually - Fix tenant_id type from bigint to uuid
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0003_invoice_carry_over_payment_method'),
    ]

    operations = [
        # Alter tenant_id columns from bigint to uuid
        migrations.RunSQL(
            # Forward: convert bigint to uuid (need to drop and recreate since types are incompatible)
            """
            -- PaymentProvider
            ALTER TABLE billing_payment_providers
            DROP CONSTRAINT IF EXISTS unique_provider_code;

            ALTER TABLE billing_payment_providers
            ALTER COLUMN tenant_id TYPE uuid USING (
                CASE
                    WHEN tenant_id = 0 THEN '00000000-0000-0000-0000-000000000000'::uuid
                    ELSE '00000000-0000-0000-0000-000000000000'::uuid
                END
            );

            -- BillingPeriod
            ALTER TABLE billing_periods
            DROP CONSTRAINT IF EXISTS unique_billing_period;

            ALTER TABLE billing_periods
            ALTER COLUMN tenant_id TYPE uuid USING (
                CASE
                    WHEN tenant_id = 0 THEN '00000000-0000-0000-0000-000000000000'::uuid
                    ELSE '00000000-0000-0000-0000-000000000000'::uuid
                END
            );

            -- DebitExportBatch
            ALTER TABLE billing_debit_export_batches
            DROP CONSTRAINT IF EXISTS unique_batch_no;

            ALTER TABLE billing_debit_export_batches
            ALTER COLUMN tenant_id TYPE uuid USING (
                CASE
                    WHEN tenant_id = 0 THEN '00000000-0000-0000-0000-000000000000'::uuid
                    ELSE '00000000-0000-0000-0000-000000000000'::uuid
                END
            );

            -- DebitExportLine
            ALTER TABLE billing_debit_export_lines
            ALTER COLUMN tenant_id TYPE uuid USING (
                CASE
                    WHEN tenant_id = 0 THEN '00000000-0000-0000-0000-000000000000'::uuid
                    ELSE '00000000-0000-0000-0000-000000000000'::uuid
                END
            );

            -- Recreate unique constraints
            ALTER TABLE billing_payment_providers
            ADD CONSTRAINT unique_provider_code UNIQUE (tenant_id, code);

            ALTER TABLE billing_periods
            ADD CONSTRAINT unique_billing_period UNIQUE (tenant_id, provider_id, year, month);

            ALTER TABLE billing_debit_export_batches
            ADD CONSTRAINT unique_batch_no UNIQUE (tenant_id, batch_no);
            """,
            # Reverse: convert uuid back to bigint
            """
            -- PaymentProvider
            ALTER TABLE billing_payment_providers
            DROP CONSTRAINT IF EXISTS unique_provider_code;

            ALTER TABLE billing_payment_providers
            ALTER COLUMN tenant_id TYPE bigint USING 0;

            ALTER TABLE billing_payment_providers
            ADD CONSTRAINT unique_provider_code UNIQUE (tenant_id, code);

            -- BillingPeriod
            ALTER TABLE billing_periods
            DROP CONSTRAINT IF EXISTS unique_billing_period;

            ALTER TABLE billing_periods
            ALTER COLUMN tenant_id TYPE bigint USING 0;

            ALTER TABLE billing_periods
            ADD CONSTRAINT unique_billing_period UNIQUE (tenant_id, provider_id, year, month);

            -- DebitExportBatch
            ALTER TABLE billing_debit_export_batches
            DROP CONSTRAINT IF EXISTS unique_batch_no;

            ALTER TABLE billing_debit_export_batches
            ALTER COLUMN tenant_id TYPE bigint USING 0;

            ALTER TABLE billing_debit_export_batches
            ADD CONSTRAINT unique_batch_no UNIQUE (tenant_id, batch_no);

            -- DebitExportLine
            ALTER TABLE billing_debit_export_lines
            ALTER COLUMN tenant_id TYPE bigint USING 0;
            """
        ),
    ]
