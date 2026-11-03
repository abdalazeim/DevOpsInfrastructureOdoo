from django.apps import AppConfig
from django.conf import settings


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    verbose_name = "الحسابات والمستخدمين"

    def ready(self):
        import logging

        logger = logging.getLogger(__name__)
        try:
            from django.contrib.auth import get_user_model
            from django.db.models.signals import post_migrate

            def seed_admin(sender, **kwargs):
                if not getattr(settings, "SEED_DEFAULT_ADMIN", False):
                    return
                password = settings.DEFAULT_ADMIN_PASSWORD
                if not password:
                    logger.warning("SEED_DEFAULT_ADMIN=true but no password set; skipping")
                    return
                User = get_user_model()
                username = settings.DEFAULT_ADMIN_USERNAME
                if not User.objects.filter(username=username).exists():
                    User.objects.create_superuser(
                        username, settings.DEFAULT_ADMIN_EMAIL, password
                    )
                    logger.info("Created default admin user %r", username)

            post_migrate.connect(seed_admin, sender=self)
        except Exception:
            logger.exception("Failed to connect post_migrate signal for admin seeding")
