# Generated manually on 2025-12-13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contracts", "0019_add_monthly_prices_to_product"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentitem",
            name="day_of_week",
            field=models.IntegerField(
                blank=True,
                help_text="0=日, 1=月, 2=火, 3=水, 4=木, 5=金, 6=土",
                null=True,
                verbose_name="曜日",
            ),
        ),
        migrations.AddField(
            model_name="studentitem",
            name="end_time",
            field=models.TimeField(blank=True, null=True, verbose_name="終了時間"),
        ),
        migrations.AddField(
            model_name="studentitem",
            name="start_time",
            field=models.TimeField(blank=True, null=True, verbose_name="開始時間"),
        ),
    ]
