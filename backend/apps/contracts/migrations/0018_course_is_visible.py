# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0017_add_ticket_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='is_visible',
            field=models.BooleanField(
                default=True,
                help_text='チェックを外すと保護者アプリに表示されません',
                verbose_name='保護者に表示'
            ),
        ),
    ]
