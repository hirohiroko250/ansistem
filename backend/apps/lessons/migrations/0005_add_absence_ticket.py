# Generated manually for AbsenceTicket model
import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lessons', '0004_add_tenant_ref'),
        ('students', '0001_initial'),
        ('contracts', '0001_initial'),
        ('schools', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AbsenceTicket',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tenant_id', models.IntegerField(db_index=True, default=100000, verbose_name='テナントID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='削除日時')),
                ('consumption_symbol', models.CharField(blank=True, help_text='振替対象を判定するための消化記号', max_length=20, verbose_name='消化記号')),
                ('absence_date', models.DateField(verbose_name='欠席日')),
                ('status', models.CharField(choices=[('issued', '発行済'), ('used', '使用済'), ('expired', '期限切れ')], default='issued', max_length=20, verbose_name='ステータス')),
                ('used_date', models.DateField(blank=True, null=True, verbose_name='使用日')),
                ('valid_until', models.DateField(verbose_name='有効期限')),
                ('notes', models.TextField(blank=True, verbose_name='備考')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='absence_tickets', to='students.student', verbose_name='生徒')),
                ('original_ticket', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='absence_tickets', to='contracts.ticket', verbose_name='元チケット')),
                ('class_schedule', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='absence_tickets', to='schools.classschedule', verbose_name='欠席した授業')),
                ('used_class_schedule', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='used_absence_tickets', to='schools.classschedule', verbose_name='振替先授業')),
            ],
            options={
                'verbose_name': '欠席チケット',
                'verbose_name_plural': '欠席チケット',
                'db_table': 't_absence_tickets',
                'ordering': ['-absence_date'],
            },
        ),
    ]
