# Generated migration for MessageMention model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('communications', '0008_add_message_reaction'),
    ]

    operations = [
        migrations.CreateModel(
            name='MessageMention',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('start_index', models.IntegerField(default=0, verbose_name='開始位置')),
                ('end_index', models.IntegerField(default=0, verbose_name='終了位置')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mentions', to='communications.message', verbose_name='メッセージ')),
                ('mentioned_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='message_mentions', to=settings.AUTH_USER_MODEL, verbose_name='メンションされたユーザー')),
            ],
            options={
                'verbose_name': 'メッセージメンション',
                'verbose_name_plural': 'メッセージメンション',
                'db_table': 'communication_message_mentions',
                'ordering': ['start_index'],
                'unique_together': {('message', 'mentioned_user')},
            },
        ),
    ]
