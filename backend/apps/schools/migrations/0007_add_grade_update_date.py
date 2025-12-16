from django.db import migrations


class Migration(migrations.Migration):
    # grade_update_day already exists in 0001_initial
    dependencies = [
        ('schools', '0006_alter_classroom_capacity'),
    ]

    operations = []
