"""Create or update a superuser from command line (generic helper).

Usage:
    python manage.py create_admin --username admin --email admin@localhost --password secret
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.core.services.audit_service import log_audit


class Command(BaseCommand):
    help = "إنشاء أو تحديث مستخدم مشرف (superuser)"

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin", help="اسم المستخدم")
        parser.add_argument("--email", default="admin@localhost", help="البريد الإلكتروني")
        parser.add_argument("--password", default="", help="كلمة المرور")

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"].strip() or "admin"
        email = options["email"].strip() or "admin@localhost"
        password = options["password"]

        user = User.objects.filter(username=username).first()
        if user is None:
            user = User(username=username, email=email, is_staff=True, is_superuser=True, is_active=True)
            user.set_password(password or User.objects.make_random_password())
            user.save()
            action = "created"
            self.stdout.write(self.style.SUCCESS(f"تم إنشاء المشرف: {username}"))
        else:
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            if password:
                user.set_password(password)
            user.save()
            action = "updated"
            self.stdout.write(self.style.SUCCESS(f"تم تحديث المشرف: {username}"))

        if not password:
            self.stdout.write(
                self.style.WARNING(
                    "كلمة المرور لم تُحدد — غيّرها فوراً بعد أول تسجيل دخول."
                )
            )

        log_audit(
            action="create" if action == "created" else "update",
            module="accounts",
            object_id=str(user.id),
            object_repr=username,
            user=user,
        )
