# Generated manually for LessonCalendar model changes

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("schools", "0010_add_class_schedule"),
    ]

    operations = [
        # 既存のunique_togetherを削除
        migrations.AlterUniqueTogether(
            name='lessoncalendar',
            unique_together=set(),
        ),
        # brandをオプションに変更
        migrations.AlterField(
            model_name='lessoncalendar',
            name='brand',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='lesson_calendars',
                to='schools.brand',
                verbose_name='ブランド'
            ),
        ),
        # schoolをオプションに変更
        migrations.AlterField(
            model_name='lessoncalendar',
            name='school',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='lesson_calendars',
                to='schools.school',
                verbose_name='校舎（後方互換用）'
            ),
        ),
        # calendar_codeにインデックスを追加
        migrations.AlterField(
            model_name='lessoncalendar',
            name='calendar_code',
            field=models.CharField(
                db_index=True,
                help_text='例: 1001_SKAEC_A, 1003_AEC_P, Int_24',
                max_length=50,
                verbose_name='カレンダーコード'
            ),
        ),
        # lesson_typeに新しい選択肢を追加
        migrations.AlterField(
            model_name='lessoncalendar',
            name='lesson_type',
            field=models.CharField(
                choices=[
                    ('A', 'Aパターン（外国人講師あり）'),
                    ('B', 'Bパターン（日本人講師のみ）'),
                    ('P', 'Pパターン（ペア）'),
                    ('Y', 'Yパターン（インター）'),
                    ('closed', '休講')
                ],
                default='closed',
                max_length=10,
                verbose_name='授業タイプ'
            ),
        ),
        # 新しいunique_togetherを設定
        migrations.AlterUniqueTogether(
            name='lessoncalendar',
            unique_together={('tenant_id', 'calendar_code', 'lesson_date')},
        ),
        # orderingを変更
        migrations.AlterModelOptions(
            name='lessoncalendar',
            options={
                'db_table': 't13_lesson_calendars',
                'ordering': ['calendar_code', 'lesson_date'],
                'verbose_name': 'T13_開講カレンダー',
                'verbose_name_plural': 'T13_開講カレンダー'
            },
        ),
    ]
