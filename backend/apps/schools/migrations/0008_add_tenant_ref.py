from django.db import migrations


class Migration(migrations.Migration):
    # tenant_ref already exists in 0001_initial
    dependencies = [
        ('schools', '0007_add_grade_update_date'),
        ('tenants', '0001_initial'),
    ]

    operations = []
