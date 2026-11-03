from django.apps import AppConfig


class InfrastructureConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.infrastructure'
    verbose_name = 'إدارة البنية التحتية لأودو'
    
    def ready(self):
        from apps.accounts.permissions.catalog import register_permissions
        from .permissions import PERMISSIONS, GROUPS
        try:
            register_permissions(PERMISSIONS, GROUPS)
        except Exception:
            pass
