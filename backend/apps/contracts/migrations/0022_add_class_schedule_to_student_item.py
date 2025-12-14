"""Add class_schedule ForeignKey to StudentItem model."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0017_add_calendar_operation_log'),
        ('contracts', '0021_studentitem_discount'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentitem',
            name='class_schedule',
            field=models.ForeignKey(
                blank=True,
                help_text='チケット購入時に選択したクラス',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='student_items',
                to='schools.classschedule',
                verbose_name='受講クラス',
            ),
        ),
    ]
