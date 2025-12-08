# Generated manually to match existing database tables

from django.db import migrations


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('schools', '0001_initial'),
        ('students', '0001_initial'),
        ('tenants', '0001_initial'),
    ]

    operations = [
        # Tables already exist in database - this migration is marked as applied
        # to synchronize Django's migration state with actual database schema
    ]
