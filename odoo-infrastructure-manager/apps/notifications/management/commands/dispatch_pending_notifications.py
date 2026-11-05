from django.core.management.base import BaseCommand, CommandError

from apps.notifications.services.delivery import (
    MAX_BATCH_SIZE,
    dispatch_pending_notifications,
)


class Command(BaseCommand):
    help = "Deliver due notification emails and persist bounded retry state."

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=100)

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        if not 1 <= batch_size <= MAX_BATCH_SIZE:
            raise CommandError(
                f"--batch-size must be between 1 and {MAX_BATCH_SIZE}."
            )
        result = dispatch_pending_notifications(batch_size=batch_size)
        self.stdout.write(
            self.style.SUCCESS(
                f"Notifications sent: {result.sent}; retry scheduled: "
                f"{result.retried}; suppressed: {result.suppressed}; "
                f"permanently failed: {result.failed}."
            )
        )
