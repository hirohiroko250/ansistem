"""
ConfirmedBillingにcarry_over_amount（繰越額）フィールドを追加

前月からの繰越額を記録するためのフィールド
プラス: 未払い繰越
マイナス: 過払い繰越
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0009_add_confirmed_billing'),
    ]

    operations = [
        migrations.AddField(
            model_name='confirmedbilling',
            name='carry_over_amount',
            field=models.DecimalField(
                decimal_places=0,
                default=0,
                help_text='前月からの繰越額（プラス=未払い繰越、マイナス=過払い繰越）',
                max_digits=12,
                verbose_name='繰越額'
            ),
        ),
    ]
