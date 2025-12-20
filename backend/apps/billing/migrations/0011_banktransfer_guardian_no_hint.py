from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0010_add_carry_over_to_confirmed_billing'),
    ]

    operations = [
        migrations.AddField(
            model_name='banktransfer',
            name='guardian_no_hint',
            field=models.CharField(blank=True, help_text='振込人名義から抽出したID番号', max_length=20, verbose_name='保護者番号（抽出）'),
        ),
    ]
