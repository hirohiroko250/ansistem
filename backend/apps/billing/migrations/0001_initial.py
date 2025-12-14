# Generated manually
import uuid
from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('students', '0001_initial'),
        ('contracts', '0001_initial'),
        ('users', '0001_initial'),
        ('tenants', '0001_initial'),
    ]

    operations = [
        # Invoice (請求書)
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('tenant_id', models.BigIntegerField(db_index=True, default=0, editable=False, verbose_name='テナントID')),
                ('tenant_ref', models.ForeignKey(blank=True, db_column='tenant_ref_id', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='tenants.tenant', verbose_name='テナント')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='削除日時')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('invoice_no', models.CharField(max_length=30, verbose_name='請求番号')),
                ('guardian', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='invoices', to='students.guardian', verbose_name='保護者')),
                ('billing_year', models.IntegerField(verbose_name='請求年')),
                ('billing_month', models.IntegerField(verbose_name='請求月')),
                ('issue_date', models.DateField(blank=True, null=True, verbose_name='発行日')),
                ('due_date', models.DateField(blank=True, null=True, verbose_name='支払期限')),
                ('subtotal', models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name='小計')),
                ('tax_amount', models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name='消費税')),
                ('discount_total', models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name='割引合計')),
                ('miles_used', models.IntegerField(default=0, verbose_name='使用マイル')),
                ('miles_discount', models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name='マイル割引額')),
                ('total_amount', models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name='請求合計')),
                ('paid_amount', models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name='入金済額')),
                ('balance_due', models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name='未払額')),
                ('status', models.CharField(choices=[('draft', '下書き'), ('issued', '発行済'), ('paid', '支払済'), ('partial', '一部入金'), ('overdue', '滞納'), ('cancelled', '取消')], default='draft', max_length=20, verbose_name='ステータス')),
                ('confirmed_at', models.DateTimeField(blank=True, null=True, verbose_name='確定日時')),
                ('confirmed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='confirmed_invoices', to='users.user', verbose_name='確定者')),
                ('notes', models.TextField(blank=True, verbose_name='備考')),
            ],
            options={
                'db_table': 'billing_invoices',
                'verbose_name': '請求書',
                'verbose_name_plural': '請求書',
                'ordering': ['-billing_year', '-billing_month'],
            },
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(fields=['guardian', 'billing_year', 'billing_month'], name='billing_inv_guardia_idx'),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(fields=['status'], name='billing_inv_status_idx'),
        ),
        migrations.AddConstraint(
            model_name='invoice',
            constraint=models.UniqueConstraint(fields=('tenant_id', 'invoice_no'), name='unique_invoice_no'),
        ),

        # InvoiceLine (請求明細)
        migrations.CreateModel(
            name='InvoiceLine',
            fields=[
                ('tenant_id', models.BigIntegerField(db_index=True, default=0, editable=False, verbose_name='テナントID')),
                ('tenant_ref', models.ForeignKey(blank=True, db_column='tenant_ref_id', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='tenants.tenant', verbose_name='テナント')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='削除日時')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='billing.invoice', verbose_name='請求書')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='invoice_lines', to='students.student', verbose_name='生徒')),
                ('student_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invoice_lines', to='contracts.studentitem', verbose_name='生徒商品')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invoice_lines', to='contracts.product', verbose_name='商品')),
                ('item_name', models.CharField(max_length=200, verbose_name='項目名')),
                ('item_type', models.CharField(blank=True, max_length=30, verbose_name='項目種別')),
                ('description', models.TextField(blank=True, verbose_name='説明')),
                ('period_start', models.DateField(blank=True, null=True, verbose_name='対象開始日')),
                ('period_end', models.DateField(blank=True, null=True, verbose_name='対象終了日')),
                ('quantity', models.IntegerField(default=1, verbose_name='数量')),
                ('unit_price', models.DecimalField(decimal_places=0, default=0, max_digits=10, verbose_name='単価')),
                ('line_total', models.DecimalField(decimal_places=0, default=0, max_digits=10, verbose_name='小計')),
                ('tax_category', models.CharField(choices=[('tax_10', '課税10%'), ('tax_8', '軽減税率8%'), ('exempt', '非課税')], default='tax_10', max_length=10, verbose_name='税区分')),
                ('tax_rate', models.DecimalField(decimal_places=2, default=Decimal('0.10'), max_digits=5, verbose_name='税率')),
                ('tax_amount', models.DecimalField(decimal_places=0, default=0, max_digits=10, verbose_name='税額')),
                ('discount_amount', models.DecimalField(decimal_places=0, default=0, max_digits=10, verbose_name='割引額')),
                ('discount_reason', models.CharField(blank=True, max_length=100, verbose_name='割引理由')),
                ('company_discount', models.DecimalField(decimal_places=0, default=0, max_digits=10, verbose_name='会社負担割引')),
                ('partner_discount', models.DecimalField(decimal_places=0, default=0, max_digits=10, verbose_name='他社負担割引')),
                ('sort_order', models.IntegerField(default=0, verbose_name='表示順')),
            ],
            options={
                'db_table': 'billing_invoice_lines',
                'verbose_name': '請求明細',
                'verbose_name_plural': '請求明細',
                'ordering': ['invoice', 'sort_order'],
            },
        ),

        # Payment (入金)
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('tenant_id', models.BigIntegerField(db_index=True, default=0, editable=False, verbose_name='テナントID')),
                ('tenant_ref', models.ForeignKey(blank=True, db_column='tenant_ref_id', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='tenants.tenant', verbose_name='テナント')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='削除日時')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('payment_no', models.CharField(max_length=30, verbose_name='入金番号')),
                ('guardian', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payments', to='students.guardian', verbose_name='保護者')),
                ('invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payments', to='billing.invoice', verbose_name='請求書')),
                ('payment_date', models.DateField(verbose_name='入金日')),
                ('amount', models.DecimalField(decimal_places=0, max_digits=12, verbose_name='入金額')),
                ('method', models.CharField(choices=[('direct_debit', '口座振替'), ('bank_transfer', '銀行振込'), ('cash', '現金'), ('credit_card', 'クレジットカード'), ('offset', '相殺'), ('other', 'その他')], default='direct_debit', max_length=20, verbose_name='入金方法')),
                ('status', models.CharField(choices=[('pending', '処理中'), ('success', '成功'), ('failed', '失敗'), ('cancelled', '取消')], default='pending', max_length=20, verbose_name='ステータス')),
                ('debit_result_code', models.CharField(blank=True, max_length=10, verbose_name='振替結果コード')),
                ('debit_result_message', models.CharField(blank=True, max_length=200, verbose_name='振替結果メッセージ')),
                ('payer_name', models.CharField(blank=True, max_length=100, verbose_name='振込人名義')),
                ('bank_name', models.CharField(blank=True, max_length=100, verbose_name='振込元銀行')),
                ('notes', models.TextField(blank=True, verbose_name='備考')),
                ('registered_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='registered_payments', to='users.user', verbose_name='登録者')),
            ],
            options={
                'db_table': 'billing_payments',
                'verbose_name': '入金',
                'verbose_name_plural': '入金',
                'ordering': ['-payment_date'],
            },
        ),
        migrations.AddConstraint(
            model_name='payment',
            constraint=models.UniqueConstraint(fields=('tenant_id', 'payment_no'), name='unique_payment_no'),
        ),

        # GuardianBalance (預り金残高)
        migrations.CreateModel(
            name='GuardianBalance',
            fields=[
                ('tenant_id', models.BigIntegerField(db_index=True, default=0, editable=False, verbose_name='テナントID')),
                ('tenant_ref', models.ForeignKey(blank=True, db_column='tenant_ref_id', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='tenants.tenant', verbose_name='テナント')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='削除日時')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('guardian', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='balance', to='students.guardian', verbose_name='保護者')),
                ('balance', models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name='残高')),
                ('last_updated', models.DateTimeField(auto_now=True, verbose_name='最終更新日時')),
                ('notes', models.TextField(blank=True, verbose_name='メモ')),
            ],
            options={
                'db_table': 'billing_guardian_balances',
                'verbose_name': '預り金残高',
                'verbose_name_plural': '預り金残高',
            },
        ),

        # OffsetLog (相殺ログ)
        migrations.CreateModel(
            name='OffsetLog',
            fields=[
                ('tenant_id', models.BigIntegerField(db_index=True, default=0, editable=False, verbose_name='テナントID')),
                ('tenant_ref', models.ForeignKey(blank=True, db_column='tenant_ref_id', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='tenants.tenant', verbose_name='テナント')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='削除日時')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('guardian', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='offset_logs', to='students.guardian', verbose_name='保護者')),
                ('invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='offset_logs', to='billing.invoice', verbose_name='請求書')),
                ('payment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='offset_logs', to='billing.payment', verbose_name='入金')),
                ('transaction_type', models.CharField(choices=[('deposit', '入金'), ('offset', '相殺'), ('refund', '返金'), ('adjustment', '調整')], max_length=20, verbose_name='取引種別')),
                ('amount', models.DecimalField(decimal_places=0, max_digits=12, verbose_name='金額')),
                ('balance_after', models.DecimalField(decimal_places=0, max_digits=12, verbose_name='取引後残高')),
                ('reason', models.TextField(blank=True, verbose_name='理由')),
            ],
            options={
                'db_table': 'billing_offset_logs',
                'verbose_name': '相殺ログ',
                'verbose_name_plural': '相殺ログ',
                'ordering': ['-created_at'],
            },
        ),

        # RefundRequest (返金申請)
        migrations.CreateModel(
            name='RefundRequest',
            fields=[
                ('tenant_id', models.BigIntegerField(db_index=True, default=0, editable=False, verbose_name='テナントID')),
                ('tenant_ref', models.ForeignKey(blank=True, db_column='tenant_ref_id', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='tenants.tenant', verbose_name='テナント')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='削除日時')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('request_no', models.CharField(max_length=30, verbose_name='申請番号')),
                ('guardian', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='refund_requests', to='students.guardian', verbose_name='保護者')),
                ('invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='refund_requests', to='billing.invoice', verbose_name='請求書')),
                ('refund_amount', models.DecimalField(decimal_places=0, max_digits=12, verbose_name='返金額')),
                ('refund_method', models.CharField(choices=[('bank_transfer', '銀行振込'), ('cash', '現金'), ('offset_next', '次回相殺')], default='bank_transfer', max_length=20, verbose_name='返金方法')),
                ('reason', models.TextField(verbose_name='返金理由')),
                ('status', models.CharField(choices=[('pending', '申請中'), ('approved', '承認済'), ('processing', '処理中'), ('completed', '完了'), ('rejected', '却下'), ('cancelled', '取消')], default='pending', max_length=20, verbose_name='ステータス')),
                ('requested_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='refund_requests', to='users.user', verbose_name='申請者')),
                ('requested_at', models.DateTimeField(auto_now_add=True, verbose_name='申請日時')),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_refund_requests', to='users.user', verbose_name='承認者')),
                ('approved_at', models.DateTimeField(blank=True, null=True, verbose_name='承認日時')),
                ('processed_at', models.DateTimeField(blank=True, null=True, verbose_name='処理日時')),
                ('process_notes', models.TextField(blank=True, verbose_name='処理メモ')),
            ],
            options={
                'db_table': 'billing_refund_requests',
                'verbose_name': '返金申請',
                'verbose_name_plural': '返金申請',
                'ordering': ['-requested_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='refundrequest',
            constraint=models.UniqueConstraint(fields=('tenant_id', 'request_no'), name='unique_refund_request_no'),
        ),

        # MileTransaction (マイル取引)
        migrations.CreateModel(
            name='MileTransaction',
            fields=[
                ('tenant_id', models.BigIntegerField(db_index=True, default=0, editable=False, verbose_name='テナントID')),
                ('tenant_ref', models.ForeignKey(blank=True, db_column='tenant_ref_id', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='tenants.tenant', verbose_name='テナント')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='削除日時')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('guardian', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='mile_transactions', to='students.guardian', verbose_name='保護者')),
                ('invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mile_transactions', to='billing.invoice', verbose_name='請求書')),
                ('transaction_type', models.CharField(choices=[('earn', '付与'), ('use', '使用'), ('expire', '失効'), ('adjustment', '調整')], max_length=20, verbose_name='取引種別')),
                ('miles', models.IntegerField(verbose_name='マイル数')),
                ('balance_after', models.IntegerField(verbose_name='取引後残高')),
                ('discount_amount', models.DecimalField(decimal_places=0, default=0, max_digits=10, verbose_name='割引額')),
                ('earn_source', models.CharField(blank=True, max_length=100, verbose_name='付与元')),
                ('earn_date', models.DateField(blank=True, null=True, verbose_name='付与日')),
                ('expire_date', models.DateField(blank=True, null=True, verbose_name='有効期限')),
                ('notes', models.TextField(blank=True, verbose_name='備考')),
            ],
            options={
                'db_table': 'billing_mile_transactions',
                'verbose_name': 'マイル取引',
                'verbose_name_plural': 'マイル取引',
                'ordering': ['-created_at'],
            },
        ),

        # DirectDebitResult (引落結果)
        migrations.CreateModel(
            name='DirectDebitResult',
            fields=[
                ('tenant_id', models.BigIntegerField(db_index=True, default=0, editable=False, verbose_name='テナントID')),
                ('tenant_ref', models.ForeignKey(blank=True, db_column='tenant_ref_id', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='tenants.tenant', verbose_name='テナント')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='削除日時')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('guardian', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='direct_debit_results', to='students.guardian', verbose_name='保護者')),
                ('invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='direct_debit_results', to='billing.invoice', verbose_name='請求書')),
                ('debit_date', models.DateField(verbose_name='引落日')),
                ('amount', models.DecimalField(decimal_places=0, max_digits=12, verbose_name='引落金額')),
                ('result_status', models.CharField(choices=[('success', '成功'), ('failed', '失敗'), ('pending', '処理中'), ('cancelled', '取消')], default='pending', max_length=20, verbose_name='結果ステータス')),
                ('failure_reason', models.CharField(blank=True, choices=[('insufficient_funds', '残高不足'), ('account_closed', '口座解約'), ('account_not_found', '口座なし'), ('invalid_account', '口座相違'), ('rejected', '振替拒否'), ('other', 'その他')], max_length=30, verbose_name='失敗理由')),
                ('failure_detail', models.TextField(blank=True, verbose_name='失敗詳細')),
                ('notice_flag', models.BooleanField(default=False, verbose_name='通知済')),
                ('notice_date', models.DateTimeField(blank=True, null=True, verbose_name='通知日時')),
                ('retry_count', models.IntegerField(default=0, verbose_name='再引落回数')),
                ('next_retry_date', models.DateField(blank=True, null=True, verbose_name='次回再引落日')),
                ('notes', models.TextField(blank=True, verbose_name='備考')),
            ],
            options={
                'db_table': 'billing_direct_debit_results',
                'verbose_name': '引落結果',
                'verbose_name_plural': '引落結果',
                'ordering': ['-debit_date'],
            },
        ),
        migrations.AddIndex(
            model_name='directdebitresult',
            index=models.Index(fields=['guardian', 'debit_date'], name='billing_ddr_guardian_idx'),
        ),
        migrations.AddIndex(
            model_name='directdebitresult',
            index=models.Index(fields=['result_status'], name='billing_ddr_status_idx'),
        ),

        # CashManagement (現金管理)
        migrations.CreateModel(
            name='CashManagement',
            fields=[
                ('tenant_id', models.BigIntegerField(db_index=True, default=0, editable=False, verbose_name='テナントID')),
                ('tenant_ref', models.ForeignKey(blank=True, db_column='tenant_ref_id', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='tenants.tenant', verbose_name='テナント')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='削除日時')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('guardian', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cash_transactions', to='students.guardian', verbose_name='保護者')),
                ('invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cash_transactions', to='billing.invoice', verbose_name='請求書')),
                ('transaction_date', models.DateField(verbose_name='取引日')),
                ('amount', models.DecimalField(decimal_places=0, max_digits=12, verbose_name='金額')),
                ('transaction_type', models.CharField(choices=[('payment', '入金'), ('refund', '返金'), ('adjustment', '調整')], default='payment', max_length=20, verbose_name='取引種別')),
                ('status', models.CharField(choices=[('pending', '未処理'), ('completed', '完了'), ('cancelled', '取消')], default='pending', max_length=20, verbose_name='ステータス')),
                ('received_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='received_cash_transactions', to='users.user', verbose_name='受領者')),
                ('received_at', models.DateTimeField(blank=True, null=True, verbose_name='受領日時')),
                ('receipt_no', models.CharField(blank=True, max_length=30, verbose_name='領収書番号')),
                ('receipt_issued', models.BooleanField(default=False, verbose_name='領収書発行済')),
                ('notes', models.TextField(blank=True, verbose_name='備考')),
            ],
            options={
                'db_table': 'billing_cash_management',
                'verbose_name': '現金管理',
                'verbose_name_plural': '現金管理',
                'ordering': ['-transaction_date'],
            },
        ),
        migrations.AddIndex(
            model_name='cashmanagement',
            index=models.Index(fields=['guardian', 'transaction_date'], name='billing_cash_guardian_idx'),
        ),
        migrations.AddIndex(
            model_name='cashmanagement',
            index=models.Index(fields=['status'], name='billing_cash_status_idx'),
        ),

        # BankTransfer (振込入金)
        migrations.CreateModel(
            name='BankTransfer',
            fields=[
                ('tenant_id', models.BigIntegerField(db_index=True, default=0, editable=False, verbose_name='テナントID')),
                ('tenant_ref', models.ForeignKey(blank=True, db_column='tenant_ref_id', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='tenants.tenant', verbose_name='テナント')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='削除日時')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('guardian', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='bank_transfers', to='students.guardian', verbose_name='保護者')),
                ('invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bank_transfers', to='billing.invoice', verbose_name='請求書')),
                ('transfer_date', models.DateField(verbose_name='振込日')),
                ('amount', models.DecimalField(decimal_places=0, max_digits=12, verbose_name='振込金額')),
                ('payer_name', models.CharField(max_length=100, verbose_name='振込人名義')),
                ('payer_name_kana', models.CharField(blank=True, max_length=100, verbose_name='振込人名義（カナ）')),
                ('source_bank_name', models.CharField(blank=True, max_length=100, verbose_name='振込元銀行')),
                ('source_branch_name', models.CharField(blank=True, max_length=100, verbose_name='振込元支店')),
                ('status', models.CharField(choices=[('pending', '確認中'), ('matched', '照合済'), ('applied', '入金適用済'), ('unmatched', '不明入金'), ('cancelled', '取消')], default='pending', max_length=20, verbose_name='ステータス')),
                ('matched_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='matched_bank_transfers', to='users.user', verbose_name='照合者')),
                ('matched_at', models.DateTimeField(blank=True, null=True, verbose_name='照合日時')),
                ('import_batch_id', models.CharField(blank=True, max_length=50, verbose_name='インポートバッチID')),
                ('import_row_no', models.IntegerField(blank=True, null=True, verbose_name='インポート行番号')),
                ('notes', models.TextField(blank=True, verbose_name='備考')),
            ],
            options={
                'db_table': 'billing_bank_transfers',
                'verbose_name': '振込入金',
                'verbose_name_plural': '振込入金',
                'ordering': ['-transfer_date'],
            },
        ),
        migrations.AddIndex(
            model_name='banktransfer',
            index=models.Index(fields=['transfer_date'], name='billing_bt_date_idx'),
        ),
        migrations.AddIndex(
            model_name='banktransfer',
            index=models.Index(fields=['payer_name'], name='billing_bt_payer_idx'),
        ),
        migrations.AddIndex(
            model_name='banktransfer',
            index=models.Index(fields=['status'], name='billing_bt_status_idx'),
        ),
    ]
