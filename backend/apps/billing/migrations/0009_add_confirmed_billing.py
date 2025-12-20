# Generated manually - creates ConfirmedBilling model only

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('students', '0001_initial'),
        ('tenants', '0001_initial'),
        ('billing', '0008_add_bank_transfer_import'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfirmedBilling',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('tenant_id', models.UUIDField(db_index=True, verbose_name='テナントID')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='削除日時')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('year', models.IntegerField(verbose_name='請求年')),
                ('month', models.IntegerField(verbose_name='請求月')),
                ('subtotal', models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name='小計')),
                ('discount_total', models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name='割引合計')),
                ('tax_amount', models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name='税額')),
                ('total_amount', models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name='合計金額')),
                ('paid_amount', models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name='入金済金額')),
                ('balance', models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name='残高')),
                ('items_snapshot', models.JSONField(default=list, verbose_name='明細スナップショット')),
                ('discounts_snapshot', models.JSONField(default=list, verbose_name='割引スナップショット')),
                ('status', models.CharField(
                    choices=[
                        ('confirmed', '確定'),
                        ('unpaid', '未入金'),
                        ('partial', '一部入金'),
                        ('paid', '入金済'),
                        ('cancelled', '取消')
                    ],
                    default='confirmed',
                    max_length=20,
                    verbose_name='ステータス'
                )),
                ('payment_method', models.CharField(
                    choices=[
                        ('direct_debit', '口座振替'),
                        ('bank_transfer', '振込'),
                        ('cash', '現金'),
                        ('other', 'その他')
                    ],
                    default='direct_debit',
                    max_length=20,
                    verbose_name='支払方法'
                )),
                ('confirmed_at', models.DateTimeField(auto_now_add=True, verbose_name='確定日時')),
                ('paid_at', models.DateTimeField(blank=True, null=True, verbose_name='入金完了日時')),
                ('notes', models.TextField(blank=True, verbose_name='備考')),
                ('billing_deadline', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='confirmed_billings',
                    to='billing.monthlybillingdeadline',
                    verbose_name='締日'
                )),
                ('confirmed_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='confirmed_billings',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='確定者'
                )),
                ('guardian', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='confirmed_billings',
                    to='students.guardian',
                    verbose_name='保護者'
                )),
                ('student', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='confirmed_billings',
                    to='students.student',
                    verbose_name='生徒'
                )),
                ('tenant_ref', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='%(app_label)s_%(class)s_set',
                    to='tenants.tenant',
                    verbose_name='テナント'
                )),
            ],
            options={
                'verbose_name': '請求確定',
                'verbose_name_plural': '請求確定',
                'db_table': 't_confirmed_billing',
                'ordering': ['-year', '-month', '-confirmed_at'],
            },
        ),
        migrations.AddIndex(
            model_name='confirmedbilling',
            index=models.Index(fields=['student', 'year', 'month'], name='t_confirmed_student_2c3c15_idx'),
        ),
        migrations.AddIndex(
            model_name='confirmedbilling',
            index=models.Index(fields=['guardian', 'year', 'month'], name='t_confirmed_guardia_b7e9c4_idx'),
        ),
        migrations.AddIndex(
            model_name='confirmedbilling',
            index=models.Index(fields=['status'], name='t_confirmed_status_8b5a47_idx'),
        ),
        migrations.AddIndex(
            model_name='confirmedbilling',
            index=models.Index(fields=['-confirmed_at'], name='t_confirmed_confirm_b2e2d3_idx'),
        ),
        migrations.AddConstraint(
            model_name='confirmedbilling',
            constraint=models.UniqueConstraint(
                fields=('tenant_id', 'student', 'year', 'month'),
                name='unique_confirmed_billing_per_student_month'
            ),
        ),
    ]
