from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.core.services.backup_service import do_backup


class Command(BaseCommand):
    help = "إنشاء نسخة احتياطية من قاعدة البيانات (pg_dump أو dumpdata تلقائياً)"

    def handle(self, *args, **options):
        backup_dir = getattr(settings, "BACKUP_DIR", Path(settings.BASE_DIR) / "backup")
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = backup_dir / f"backup_{timestamp}.dump"
        filename = do_backup(dest)

        self.stdout.write(self.style.SUCCESS(f"تم إنشاء النسخة الاحتياطية: {filename}"))
