"""
Add QR code field to User model for attendance management.
"""
import uuid
from django.db import migrations, models


def generate_qr_codes(apps, schema_editor):
    """既存のユーザーにQRコードを付与（すべてユニークなUUID）"""
    User = apps.get_model('users', 'User')
    for user in User.objects.filter(qr_code__isnull=True):
        user.qr_code = uuid.uuid4()
        user.save(update_fields=['qr_code'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_user_must_change_password'),
    ]

    operations = [
        # Step 1: Add field without unique constraint (null allowed)
        migrations.AddField(
            model_name='user',
            name='qr_code',
            field=models.UUIDField(
                null=True,
                blank=True,
                editable=False,
                verbose_name='QRコード識別子',
            ),
        ),
        # Step 2: Generate unique QR codes for all users
        migrations.RunPython(generate_qr_codes, migrations.RunPython.noop),
        # Step 3: Make field non-null with unique constraint
        migrations.AlterField(
            model_name='user',
            name='qr_code',
            field=models.UUIDField(
                default=uuid.uuid4,
                unique=True,
                editable=False,
                db_index=True,
                verbose_name='QRコード識別子',
            ),
        ),
    ]
