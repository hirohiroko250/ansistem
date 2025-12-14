# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('schools', '0012_add_ticket_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='classschedule',
            name='grade',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='class_schedules',
                to='schools.grade',
                verbose_name='対象学年'
            ),
        ),
    ]
