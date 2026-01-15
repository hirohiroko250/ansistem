"""
Add QR code field to Student model for attendance management.
"""
import uuid
from django.db import migrations, models


def generate_qr_codes(apps, schema_editor):
    """既存の生徒にQRコードを付与（すべてユニークなUUID）"""
    Student = apps.get_model('students', 'Student')
    for student in Student.objects.filter(qr_code__isnull=True):
        student.qr_code = uuid.uuid4()
        student.save(update_fields=['qr_code'])


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0025_guardian_referral_code'),
    ]

    operations = [
        # Step 1: Add field without unique constraint (null allowed)
        migrations.AddField(
            model_name='student',
            name='qr_code',
            field=models.UUIDField(
                null=True,
                blank=True,
                editable=False,
                verbose_name='QRコード識別子',
            ),
        ),
        # Step 2: Generate unique QR codes for all students
        migrations.RunPython(generate_qr_codes, migrations.RunPython.noop),
        # Step 3: Make field non-null with unique constraint
        migrations.AlterField(
            model_name='student',
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
