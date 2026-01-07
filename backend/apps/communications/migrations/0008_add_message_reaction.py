# Generated migration for MessageReaction model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('communications', '0007_add_feed_publish_dates'),
    ]

    operations = [
        migrations.CreateModel(
            name='MessageReaction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('emoji', models.CharField(max_length=10, verbose_name='絵文字')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reactions', to='communications.message', verbose_name='メッセージ')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='message_reactions', to=settings.AUTH_USER_MODEL, verbose_name='ユーザー')),
            ],
            options={
                'verbose_name': 'メッセージリアクション',
                'verbose_name_plural': 'メッセージリアクション',
                'db_table': 'communication_message_reactions',
                'ordering': ['created_at'],
                'unique_together': {('message', 'user', 'emoji')},
            },
        ),
    ]
