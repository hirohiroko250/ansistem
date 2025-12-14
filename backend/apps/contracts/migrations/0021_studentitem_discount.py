# Generated manually on 2025-12-13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("contracts", "0020_studentitem_schedule_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentitem",
            name="discount",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="student_items",
                to="contracts.discount",
                verbose_name="適用割引",
            ),
        ),
    ]
