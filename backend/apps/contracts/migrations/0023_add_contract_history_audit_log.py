# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("schools", "0017_add_calendar_operation_log"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tenants", "0001_initial"),
        ("students", "0011_add_fs_discount_models"),
        ("contracts", "0022_add_class_schedule_to_student_item"),
    ]

    operations = [
        # Contract への新規フィールド追加
        migrations.AddField(
            model_name="contract",
            name="discount_applied",
            field=models.DecimalField(
                decimal_places=0,
                default=0,
                help_text="兄弟割引など適用されている割引額",
                max_digits=10,
                verbose_name="適用割引額",
            ),
        ),
        migrations.AddField(
            model_name="contract",
            name="discount_type",
            field=models.CharField(
                blank=True,
                help_text="兄弟割引、キャンペーン等",
                max_length=50,
                verbose_name="割引種別",
            ),
        ),
        migrations.AddField(
            model_name="contract",
            name="mile_discount_applied",
            field=models.DecimalField(
                decimal_places=0,
                default=0,
                help_text="マイル使用による割引額",
                max_digits=10,
                verbose_name="マイル割引額",
            ),
        ),
        migrations.AddField(
            model_name="contract",
            name="mile_earn_monthly",
            field=models.IntegerField(
                default=0,
                help_text="この契約で毎月獲得するマイル数",
                verbose_name="月間獲得マイル",
            ),
        ),
        migrations.AddField(
            model_name="contract",
            name="mile_used",
            field=models.IntegerField(
                default=0,
                help_text="この契約で使用したマイル数",
                verbose_name="使用マイル",
            ),
        ),
        # SystemAuditLog テーブル作成
        migrations.CreateModel(
            name="SystemAuditLog",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="作成日時"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新日時"),
                ),
                (
                    "tenant_id",
                    models.UUIDField(db_index=True, verbose_name="テナントID"),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="削除日時"
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "entity_type",
                    models.CharField(
                        choices=[
                            ("student", "生徒"),
                            ("guardian", "保護者"),
                            ("contract", "契約"),
                            ("student_item", "生徒商品"),
                            ("invoice", "請求書"),
                            ("payment", "入金"),
                            ("mile", "マイル"),
                            ("discount", "割引"),
                            ("school", "校舎"),
                            ("course", "コース"),
                            ("class_schedule", "クラススケジュール"),
                            ("enrollment", "受講登録"),
                            ("user", "ユーザー"),
                            ("other", "その他"),
                        ],
                        max_length=30,
                        verbose_name="エンティティ種別",
                    ),
                ),
                (
                    "entity_id",
                    models.CharField(max_length=100, verbose_name="エンティティID"),
                ),
                (
                    "entity_name",
                    models.CharField(
                        blank=True, max_length=200, verbose_name="エンティティ名"
                    ),
                ),
                (
                    "action_type",
                    models.CharField(
                        choices=[
                            ("create", "作成"),
                            ("update", "更新"),
                            ("delete", "削除"),
                            ("soft_delete", "論理削除"),
                            ("restore", "復元"),
                            ("login", "ログイン"),
                            ("logout", "ログアウト"),
                            ("export", "エクスポート"),
                            ("import", "インポート"),
                            ("approve", "承認"),
                            ("reject", "却下"),
                            ("cancel", "キャンセル"),
                            ("other", "その他"),
                        ],
                        max_length=30,
                        verbose_name="操作種別",
                    ),
                ),
                (
                    "action_detail",
                    models.CharField(max_length=500, verbose_name="操作詳細"),
                ),
                (
                    "before_data",
                    models.JSONField(
                        blank=True, null=True, verbose_name="変更前データ"
                    ),
                ),
                (
                    "after_data",
                    models.JSONField(
                        blank=True, null=True, verbose_name="変更後データ"
                    ),
                ),
                (
                    "changed_fields",
                    models.JSONField(
                        blank=True,
                        help_text="変更されたフィールド名のリスト",
                        null=True,
                        verbose_name="変更フィールド",
                    ),
                ),
                (
                    "user_name",
                    models.CharField(
                        blank=True, max_length=100, verbose_name="操作者名"
                    ),
                ),
                (
                    "user_email",
                    models.CharField(
                        blank=True, max_length=200, verbose_name="操作者メール"
                    ),
                ),
                (
                    "is_system_action",
                    models.BooleanField(default=False, verbose_name="システム操作"),
                ),
                (
                    "ip_address",
                    models.GenericIPAddressField(
                        blank=True, null=True, verbose_name="IPアドレス"
                    ),
                ),
                (
                    "user_agent",
                    models.TextField(blank=True, verbose_name="ユーザーエージェント"),
                ),
                (
                    "request_path",
                    models.CharField(
                        blank=True, max_length=500, verbose_name="リクエストパス"
                    ),
                ),
                (
                    "request_method",
                    models.CharField(
                        blank=True, max_length=10, verbose_name="リクエストメソッド"
                    ),
                ),
                ("is_success", models.BooleanField(default=True, verbose_name="成功")),
                (
                    "error_message",
                    models.TextField(blank=True, verbose_name="エラーメッセージ"),
                ),
                ("notes", models.TextField(blank=True, verbose_name="備考")),
                (
                    "contract",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to="contracts.contract",
                        verbose_name="関連契約",
                    ),
                ),
                (
                    "guardian",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to="students.guardian",
                        verbose_name="関連保護者",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to="students.student",
                        verbose_name="関連生徒",
                    ),
                ),
                (
                    "tenant_ref",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_set",
                        to="tenants.tenant",
                        verbose_name="テナント",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="操作者",
                    ),
                ),
            ],
            options={
                "verbose_name": "システム監査ログ",
                "verbose_name_plural": "システム監査ログ",
                "db_table": "system_audit_logs",
                "ordering": ["-created_at"],
            },
        ),
        # ContractHistory テーブル作成
        migrations.CreateModel(
            name="ContractHistory",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="作成日時"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新日時"),
                ),
                (
                    "tenant_id",
                    models.UUIDField(db_index=True, verbose_name="テナントID"),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="削除日時"
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "action_type",
                    models.CharField(
                        choices=[
                            ("created", "新規作成"),
                            ("updated", "更新"),
                            ("cancelled", "解約"),
                            ("paused", "休会"),
                            ("resumed", "再開"),
                            ("course_changed", "コース変更"),
                            ("schedule_changed", "スケジュール変更"),
                            ("school_changed", "校舎変更"),
                            ("price_changed", "料金変更"),
                            ("discount_applied", "割引適用"),
                            ("mile_applied", "マイル適用"),
                            ("promotion", "進級"),
                            ("other", "その他"),
                        ],
                        max_length=30,
                        verbose_name="変更種別",
                    ),
                ),
                (
                    "before_data",
                    models.JSONField(
                        blank=True,
                        help_text="変更前の契約情報をJSON形式で保存",
                        null=True,
                        verbose_name="変更前データ",
                    ),
                ),
                (
                    "after_data",
                    models.JSONField(
                        blank=True,
                        help_text="変更後の契約情報をJSON形式で保存",
                        null=True,
                        verbose_name="変更後データ",
                    ),
                ),
                (
                    "change_summary",
                    models.CharField(max_length=500, verbose_name="変更概要"),
                ),
                (
                    "change_detail",
                    models.TextField(blank=True, verbose_name="変更詳細"),
                ),
                (
                    "amount_before",
                    models.DecimalField(
                        blank=True,
                        decimal_places=0,
                        max_digits=10,
                        null=True,
                        verbose_name="変更前金額",
                    ),
                ),
                (
                    "amount_after",
                    models.DecimalField(
                        blank=True,
                        decimal_places=0,
                        max_digits=10,
                        null=True,
                        verbose_name="変更後金額",
                    ),
                ),
                (
                    "discount_amount",
                    models.DecimalField(
                        blank=True,
                        decimal_places=0,
                        max_digits=10,
                        null=True,
                        verbose_name="割引額",
                    ),
                ),
                (
                    "mile_used",
                    models.IntegerField(
                        blank=True, null=True, verbose_name="使用マイル"
                    ),
                ),
                (
                    "mile_discount",
                    models.DecimalField(
                        blank=True,
                        decimal_places=0,
                        max_digits=10,
                        null=True,
                        verbose_name="マイル割引額",
                    ),
                ),
                (
                    "effective_date",
                    models.DateField(blank=True, null=True, verbose_name="適用日"),
                ),
                (
                    "changed_by_name",
                    models.CharField(
                        blank=True, max_length=100, verbose_name="変更者名"
                    ),
                ),
                (
                    "is_system_change",
                    models.BooleanField(
                        default=False,
                        help_text="自動処理による変更の場合True",
                        verbose_name="システム変更",
                    ),
                ),
                (
                    "ip_address",
                    models.GenericIPAddressField(
                        blank=True, null=True, verbose_name="IPアドレス"
                    ),
                ),
                ("notes", models.TextField(blank=True, verbose_name="備考")),
                (
                    "changed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="contract_histories",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="変更者",
                    ),
                ),
                (
                    "contract",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="histories",
                        to="contracts.contract",
                        verbose_name="契約",
                    ),
                ),
                (
                    "tenant_ref",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_set",
                        to="tenants.tenant",
                        verbose_name="テナント",
                    ),
                ),
            ],
            options={
                "verbose_name": "契約履歴",
                "verbose_name_plural": "契約履歴",
                "db_table": "contract_histories",
                "ordering": ["-created_at"],
            },
        ),
        # インデックス追加
        migrations.AddIndex(
            model_name="systemauditlog",
            index=models.Index(
                fields=["entity_type", "entity_id"],
                name="system_audi_entity__9395e8_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="systemauditlog",
            index=models.Index(
                fields=["action_type"], name="system_audi_action__97ec99_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="systemauditlog",
            index=models.Index(
                fields=["-created_at"], name="system_audi_created_3f05c8_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="contracthistory",
            index=models.Index(
                fields=["contract", "-created_at"],
                name="contract_hi_contrac_d69715_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="contracthistory",
            index=models.Index(
                fields=["action_type"], name="contract_hi_action__df5906_idx"
            ),
        ),
    ]
