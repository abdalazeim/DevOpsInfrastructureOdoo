from django.apps import AppConfig


class ExampleConfig(AppConfig):
    name = "apps.modules.example"
    verbose_name = "مثال عام"

    def ready(self):
        from apps.accounts.permissions.catalog import register_permissions

        from .permissions import GROUPS, PERMISSIONS

        register_permissions(PERMISSIONS, GROUPS)
        from .sync import register_example_sync

        register_example_sync()
