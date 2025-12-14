# Generated manually
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('students', '0006_add_suspension_withdrawal_requests'),
    ]

    operations = [
        # T15: 銀行口座マスタ
        migrations.CreateModel(
            name='BankAccount',
            fields=[
                ('tenant_id', models.PositiveIntegerField(db_index=True, default=100000, verbose_name='テナントID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('bank_name', models.CharField(max_length=100, verbose_name='金融機関名')),
                ('bank_code', models.CharField(blank=True, max_length=4, verbose_name='金融機関コード')),
                ('branch_name', models.CharField(max_length=100, verbose_name='支店名')),
                ('branch_code', models.CharField(blank=True, max_length=3, verbose_name='支店コード')),
                ('account_type', models.CharField(choices=[('ordinary', '普通'), ('current', '当座'), ('savings', '貯蓄')], default='ordinary', max_length=10, verbose_name='口座種別')),
                ('account_number', models.CharField(max_length=8, verbose_name='口座番号')),
                ('account_holder', models.CharField(max_length=100, verbose_name='口座名義')),
                ('account_holder_kana', models.CharField(max_length=100, verbose_name='口座名義（カナ）')),
                ('is_primary', models.BooleanField(default=False, verbose_name='メイン口座')),
                ('is_active', models.BooleanField(default=True, verbose_name='有効')),
                ('notes', models.TextField(blank=True, verbose_name='備考')),
                ('guardian', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bank_accounts', to='students.guardian', verbose_name='保護者')),
            ],
            options={
                'verbose_name': '銀行口座',
                'verbose_name_plural': '銀行口座',
                'db_table': 't15_bank_account',
                'ordering': ['-created_at'],
            },
        ),
        # T16: 銀行口座変更申請
        migrations.CreateModel(
            name='BankAccountChangeRequest',
            fields=[
                ('tenant_id', models.PositiveIntegerField(db_index=True, default=100000, verbose_name='テナントID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('request_type', models.CharField(choices=[('new', '新規登録'), ('update', '変更'), ('delete', '削除')], default='new', max_length=10, verbose_name='申請種別')),
                ('bank_name', models.CharField(blank=True, max_length=100, verbose_name='金融機関名')),
                ('bank_code', models.CharField(blank=True, max_length=4, verbose_name='金融機関コード')),
                ('branch_name', models.CharField(blank=True, max_length=100, verbose_name='支店名')),
                ('branch_code', models.CharField(blank=True, max_length=3, verbose_name='支店コード')),
                ('account_type', models.CharField(blank=True, choices=[('ordinary', '普通'), ('current', '当座'), ('savings', '貯蓄')], max_length=10, verbose_name='口座種別')),
                ('account_number', models.CharField(blank=True, max_length=8, verbose_name='口座番号')),
                ('account_holder', models.CharField(blank=True, max_length=100, verbose_name='口座名義')),
                ('account_holder_kana', models.CharField(blank=True, max_length=100, verbose_name='口座名義（カナ）')),
                ('is_primary', models.BooleanField(default=True, verbose_name='メイン口座にする')),
                ('status', models.CharField(choices=[('pending', '申請中'), ('approved', '承認済'), ('rejected', '却下'), ('cancelled', '取消')], default='pending', max_length=10, verbose_name='ステータス')),
                ('requested_at', models.DateTimeField(auto_now_add=True, verbose_name='申請日時')),
                ('request_notes', models.TextField(blank=True, verbose_name='申請メモ')),
                ('processed_at', models.DateTimeField(blank=True, null=True, verbose_name='処理日時')),
                ('process_notes', models.TextField(blank=True, verbose_name='処理メモ')),
                ('existing_account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='change_requests', to='students.bankaccount', verbose_name='既存口座')),
                ('guardian', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bank_account_requests', to='students.guardian', verbose_name='保護者')),
                ('processed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='processed_bank_requests', to=settings.AUTH_USER_MODEL, verbose_name='処理者')),
                ('requested_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bank_account_requests', to=settings.AUTH_USER_MODEL, verbose_name='申請者')),
            ],
            options={
                'verbose_name': '銀行口座変更申請',
                'verbose_name_plural': '銀行口座変更申請',
                'db_table': 't16_bank_account_change_request',
                'ordering': ['-requested_at'],
            },
        ),
    ]
