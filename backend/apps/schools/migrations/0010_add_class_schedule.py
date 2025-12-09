# Generated manually for ClassSchedule model

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0001_initial"),
        ("schools", "0009_add_lesson_calendar_csv_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClassSchedule",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True, verbose_name="削除日時")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="作成日時")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新日時")),
                ("schedule_code", models.CharField(help_text="例: 尾張旭月4_Ti10000025", max_length=50, verbose_name="時間割コード")),
                ("day_of_week", models.IntegerField(choices=[(1, "月曜日"), (2, "火曜日"), (3, "水曜日"), (4, "木曜日"), (5, "金曜日"), (6, "土曜日"), (7, "日曜日")], verbose_name="曜日")),
                ("period", models.IntegerField(help_text="1, 2, 3...（V表示時限）", verbose_name="時限")),
                ("start_time", models.TimeField(verbose_name="開始時間")),
                ("duration_minutes", models.IntegerField(default=50, verbose_name="授業時間（分）")),
                ("end_time", models.TimeField(verbose_name="終了時間")),
                ("break_time", models.TimeField(blank=True, help_text="当日の休憩時間", null=True, verbose_name="休憩時間")),
                ("class_name", models.CharField(help_text="例: Purple ペア", max_length=100, verbose_name="クラス名")),
                ("class_type", models.CharField(blank=True, help_text="例: Purpleペア", max_length=50, verbose_name="クラス種名")),
                ("display_course_name", models.CharField(blank=True, help_text="例: ④小５以上(英語歴5年以上)", max_length=200, verbose_name="保護者用コース名")),
                ("display_pair_name", models.CharField(blank=True, help_text="例: Purple_ペア", max_length=100, verbose_name="保護者用ペア名")),
                ("display_description", models.TextField(blank=True, help_text="例: 【通称】:Purpleクラス【対象】④小５以上...", verbose_name="保護者用説明")),
                ("ticket_name", models.CharField(blank=True, help_text="例: Purple ペア　50分×週1回", max_length=100, verbose_name="チケット名")),
                ("ticket_id", models.CharField(blank=True, help_text="例: Ti10000025", max_length=50, verbose_name="チケットID")),
                ("transfer_group", models.CharField(blank=True, help_text="同じグループ内で振替可能", max_length=50, verbose_name="振替グループ")),
                ("schedule_group", models.CharField(blank=True, max_length=50, verbose_name="時間割グループ")),
                ("capacity", models.IntegerField(default=12, verbose_name="定員")),
                ("trial_capacity", models.IntegerField(default=2, verbose_name="体験受入可能数")),
                ("reserved_seats", models.IntegerField(default=0, verbose_name="予約済み席数")),
                ("pause_seat_fee", models.DecimalField(decimal_places=0, default=0, max_digits=10, verbose_name="休会時座席料金")),
                ("calendar_pattern", models.CharField(blank=True, help_text="例: 1003_AEC_P", max_length=50, verbose_name="カレンダーパターン")),
                ("approval_type", models.IntegerField(choices=[(1, "自動承認"), (2, "承認制")], default=1, verbose_name="承認種別")),
                ("room_name", models.CharField(blank=True, help_text="Roomマスタにない場合の教室名", max_length=50, verbose_name="教室名")),
                ("display_start_date", models.DateField(blank=True, null=True, verbose_name="保護者表示開始日")),
                ("class_start_date", models.DateField(blank=True, null=True, verbose_name="クラス開始日")),
                ("class_end_date", models.DateField(blank=True, null=True, verbose_name="クラス終了日")),
                ("is_active", models.BooleanField(default=True, verbose_name="有効")),
                ("brand", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="class_schedules", to="schools.brand", verbose_name="ブランド")),
                ("brand_category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="class_schedules", to="schools.brandcategory", verbose_name="ブランドカテゴリ")),
                ("room", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="class_schedules", to="schools.classroom", verbose_name="教室")),
                ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="class_schedules", to="schools.school", verbose_name="校舎")),
                ("tenant_id", models.CharField(db_index=True, max_length=50, verbose_name="テナントID")),
            ],
            options={
                "verbose_name": "T14c_開講時間割",
                "verbose_name_plural": "T14c_開講時間割",
                "db_table": "t14c_class_schedules",
                "ordering": ["school", "brand_category", "brand", "day_of_week", "period"],
            },
        ),
        migrations.AddConstraint(
            model_name="classschedule",
            constraint=models.UniqueConstraint(fields=("tenant_id", "schedule_code"), name="unique_class_schedule_code"),
        ),
    ]
