# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0002_add_provider_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="carry_over_amount",
            field=models.DecimalField(
                decimal_places=0,
                default=0,
                help_text="前月からの繰越額（プラス=未払い繰越、マイナス=過払い繰越）",
                max_digits=12,
                verbose_name="繰越額",
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="payment_method",
            field=models.CharField(
                choices=[
                    ("direct_debit", "口座引落"),
                    ("bank_transfer", "振込"),
                    ("credit_card", "クレジットカード"),
                    ("cash", "現金"),
                    ("other", "その他"),
                ],
                default="direct_debit",
                max_length=20,
                verbose_name="支払方法",
            ),
        ),
    ]
