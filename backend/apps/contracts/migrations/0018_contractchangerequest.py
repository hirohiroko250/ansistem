# Generated migration for ContractChangeRequest

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('schools', '0012_add_ticket_models'),
        ('contracts', '0017_add_ticket_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContractChangeRequest',
            fields=[
                ('tenant_id', models.UUIDField(db_index=True, verbose_name='テナントID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='削除日時')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('request_type', models.CharField(choices=[('class_change', 'クラス変更'), ('school_change', '校舎変更'), ('suspension', '休会申請'), ('cancellation', '退会申請')], max_length=20, verbose_name='申請種別')),
                ('status', models.CharField(choices=[('pending', '申請中'), ('approved', '承認済'), ('rejected', '却下'), ('cancelled', '取消')], default='pending', max_length=20, verbose_name='ステータス')),
                ('new_day_of_week', models.IntegerField(blank=True, null=True, verbose_name='新曜日')),
                ('new_start_time', models.TimeField(blank=True, null=True, verbose_name='新開始時間')),
                ('effective_date', models.DateField(blank=True, null=True, verbose_name='適用日')),
                ('suspend_from', models.DateField(blank=True, null=True, verbose_name='休会開始日')),
                ('suspend_until', models.DateField(blank=True, null=True, verbose_name='休会終了日')),
                ('keep_seat', models.BooleanField(default=False, verbose_name='座席保持')),
                ('cancel_date', models.DateField(blank=True, null=True, verbose_name='退会日')),
                ('refund_amount', models.DecimalField(blank=True, decimal_places=0, max_digits=10, null=True, verbose_name='相殺金額')),
                ('reason', models.TextField(blank=True, verbose_name='理由')),
                ('requested_at', models.DateTimeField(auto_now_add=True, verbose_name='申請日時')),
                ('processed_at', models.DateTimeField(blank=True, null=True, verbose_name='処理日時')),
                ('process_notes', models.TextField(blank=True, verbose_name='処理メモ')),
                ('contract', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='change_requests', to='contracts.contract', verbose_name='契約')),
                ('new_class_schedule', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='change_requests', to='schools.classschedule', verbose_name='新クラススケジュール')),
                ('new_school', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='change_requests', to='schools.school', verbose_name='新校舎')),
                ('processed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='processed_contract_requests', to=settings.AUTH_USER_MODEL, verbose_name='処理者')),
                ('requested_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='contract_change_requests', to=settings.AUTH_USER_MODEL, verbose_name='申請者')),
            ],
            options={
                'verbose_name': '契約変更申請',
                'verbose_name_plural': '契約変更申請',
                'db_table': 'contract_change_requests',
                'ordering': ['-requested_at'],
            },
        ),
    ]
