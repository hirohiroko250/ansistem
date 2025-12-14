from django.apps import AppConfig


class SchoolsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.schools'
    verbose_name = '校舎管理'

    def ready(self):
        # シグナルをインポートして登録
        import apps.schools.signals  # noqa: F401
