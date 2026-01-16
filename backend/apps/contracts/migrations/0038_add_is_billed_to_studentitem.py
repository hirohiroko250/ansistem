# Generated manually
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0037_add_certification_purchase_deadline'),
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentitem',
            name='is_billed',
            field=models.BooleanField(
                default=False,
                help_text='確定ボタンで請求に含まれたらTrue',
                verbose_name='請求済み'
            ),
        ),
        migrations.AddField(
            model_name='studentitem',
            name='confirmed_billing',
            field=models.ForeignKey(
                blank=True,
                help_text='どの請求確定に含まれたか',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='student_items',
                to='billing.confirmedbilling',
                verbose_name='請求確定'
            ),
        ),
    ]
