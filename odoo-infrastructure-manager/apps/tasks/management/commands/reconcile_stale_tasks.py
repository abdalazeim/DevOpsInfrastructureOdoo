from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.tasks.models import Task
from apps.tasks.services.task_service import transition_task


class Command(BaseCommand):
    help = "Mark tasks left running past the operation timeout as timed out."

    def add_arguments(self, parser):
        parser.add_argument("--older-than", type=int, default=None, help="Age in seconds; defaults to operation timeout plus 60 seconds.")

    def handle(self, *args, **options):
        threshold = options["older_than"]
        if threshold is None:
            threshold = settings.INFRA_OPERATION_TIMEOUT_SECONDS + 60
        if threshold < 1:
            raise CommandError("--older-than must be a positive number of seconds.")
        cutoff = timezone.now() - timedelta(seconds=threshold)
        stale_ids = list(Task.objects.filter(status=Task.Status.RUNNING, started_at__lt=cutoff).values_list("pk", flat=True))
        updated = 0
        for task_id in stale_ids:
            try:
                transition_task(
                    task_id, Task.Status.TIMEOUT, error_category="worker_timeout",
                    error_message="The worker did not finish before the operation timeout.",
                )
                updated += 1
            except ValidationError:
                # A concurrent worker may have completed the task after selection.
                continue
        self.stdout.write(self.style.SUCCESS(f"Marked {updated} stale task(s) as timed out."))
