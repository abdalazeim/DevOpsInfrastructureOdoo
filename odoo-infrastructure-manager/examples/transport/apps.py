from django.apps import AppConfig


class TransportConfig(AppConfig):
    name = "examples.transport"
    verbose_name = "وحدة النقل"

    def ready(self):
        from apps.accounts.permissions.catalog import register_permissions

        from .permissions import PERMISSIONS, GROUPS

        register_permissions(PERMISSIONS, GROUPS)
