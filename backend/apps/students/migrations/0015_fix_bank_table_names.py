# Generated manually - fix table names
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0014_add_schedule_to_student_school'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE IF EXISTS t15_bank_account RENAME TO t15_bank_accounts;',
            reverse_sql='ALTER TABLE IF EXISTS t15_bank_accounts RENAME TO t15_bank_account;',
        ),
        migrations.RunSQL(
            sql='ALTER TABLE IF EXISTS t16_bank_account_change_request RENAME TO t16_bank_account_requests;',
            reverse_sql='ALTER TABLE IF EXISTS t16_bank_account_requests RENAME TO t16_bank_account_change_request;',
        ),
    ]
