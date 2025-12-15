"""
Add invoice lock fields for export tracking
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0005_add_discount_operation_log'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='is_locked',
            field=models.BooleanField(default=False, help_text='エクスポート済みで編集不可', verbose_name='編集ロック'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='locked_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='ロック日時'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='locked_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='locked_invoices', to=settings.AUTH_USER_MODEL, verbose_name='ロック実行者'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='export_batch_no',
            field=models.CharField(blank=True, help_text='引落データ出力時のバッチ番号', max_length=50, verbose_name='エクスポートバッチ番号'),
        ),
    ]
