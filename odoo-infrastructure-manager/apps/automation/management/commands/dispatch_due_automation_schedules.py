from datetime import timedelta

from django.core.management.base import BaseCommand
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.automation.models import AutomationSchedule
from apps.automation.services.execution import (
    AutomationValidationError,
    load_schedule_variables,
    queue_automation_run,
)
from apps.core.services.audit_service import log_audit


class Command(BaseCommand):
    help = "Queue due, dry-run-only approved automation schedules."

    def handle(self, *args, **options):
        now = timezone.now()
        due_ids = list(
            AutomationSchedule.objects.filter(
                enabled=True, next_run_at__lte=now
            ).order_by("next_run_at").values_list("pk", flat=True)[:100]
        )
        queued = failed = 0
        for schedule_id in due_ids:
            with transaction.atomic():
                try:
                    schedule = AutomationSchedule.objects.select_for_update().select_related(
                        "template", "created_by"
                    ).get(pk=schedule_id, enabled=True)
                except AutomationSchedule.DoesNotExist:
                    continue
                if not schedule.next_run_at or schedule.next_run_at > now:
                    continue
                schedule.next_run_at = now + timedelta(minutes=schedule.interval_minutes)
                schedule.last_run_at = now
                schedule.last_error = ""
                schedule.save(update_fields=["next_run_at", "last_run_at", "last_error", "updated_at"])

            try:
                run = queue_automation_run(
                    template=schedule.template,
                    actor=schedule.created_by,
                    dry_run=True,
                    variables=load_schedule_variables(schedule),
                )
                if run.status == run.Status.FAILED:
                    raise AutomationValidationError(run.summary)
            except (AutomationValidationError, PermissionDenied) as exc:
                schedule.last_error = str(exc)[:500]
                schedule.save(update_fields=["last_error", "updated_at"])
                log_audit(
                    user=schedule.created_by, action="other", module="automation.schedule",
                    object_id=schedule.pk, object_repr=schedule.template.name,
                    new_value={"result": "failed", "error": schedule.last_error},
                )
                failed += 1
                self.stderr.write(self.style.ERROR(
                    f"Schedule {schedule.pk} was not dispatched: {schedule.last_error}"
                ))
            else:
                log_audit(
                    user=schedule.created_by, action="create", module="automation.schedule",
                    object_id=schedule.pk, object_repr=schedule.template.name,
                    new_value={"result": "queued", "run_id": run.pk, "task_id": str(run.task_id or "")},
                )
                queued += 1
        self.stdout.write(self.style.SUCCESS(
            f"Processed {len(due_ids)} due schedule(s): {queued} queued, {failed} failed."
        ))
