import json
import re

from django.utils import timezone

from apps.automation.models import ApprovedTaskTemplate, AutomationRun
from apps.automation.services.semaphore_client import SemaphoreClient, SemaphoreError


_REDACTIONS = (
    (re.compile(r'''(?i)(["']?authorization["']?\s*[=:]\s*["']?)bearer\s+[^\s,"';}]+'''), r"\1[redacted]"),
    (re.compile(r'''(?i)(["']?(?:password|token|secret|authorization|api[_-]?key)["']?\s*[=:]\s*["']?)[^\s,"';}]+'''), r"\1[redacted]"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/-]+=*"), "[redacted]"),
    (re.compile(r"(?i)(https?://)[^/@\s]+:[^/@\s]+@"), r"\1[redacted]@"),
)


def redact_automation_output(value):
    for pattern, replacement in _REDACTIONS:
        value = pattern.sub(replacement, value)
    return value


def format_automation_output(output):
    if isinstance(output, str):
        return output
    if isinstance(output, dict):
        for key in ("output", "stdout", "text"):
            value = output.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, list):
                return "\n".join(str(line) for line in value)
        return json.dumps(output, ensure_ascii=False, indent=2)
    if isinstance(output, list):
        return "\n".join(format_automation_output(item) for item in output)
    return str(output or "")


def _sync_backup_artifact(run, output):
    if (
        run.template.category == ApprovedTaskTemplate.Category.BACKUP
        and not run.dry_run
    ):
        from apps.backup.services.workflows import sync_backup_artifact

        sync_backup_artifact(run, output)


def refresh_automation_run(run):
    if run.external_task_id is None:
        return "The Semaphore task has not started."
    try:
        task = SemaphoreClient().get_task(
            run.template.project_id, run.external_task_id
        )
    except SemaphoreError as exc:
        return str(exc)

    output_error = ""
    updates = []
    if isinstance(task, dict):
        status = str(task.get("status", "")).lower()
        mapping = {
            "running": AutomationRun.Status.RUNNING,
            "waiting": AutomationRun.Status.QUEUED,
            "success": AutomationRun.Status.SUCCESS,
            "failed": AutomationRun.Status.FAILED,
            "stopped": AutomationRun.Status.FAILED,
        }
        if status in mapping:
            run.status = mapping[status]
            updates.extend(["status"])
            if run.status in {AutomationRun.Status.SUCCESS, AutomationRun.Status.FAILED}:
                run.finished_at = timezone.now()
                updates.append("finished_at")
            run.summary = redact_automation_output(
                str(task.get("error", "") or task.get("status", ""))
            )[:500]
            updates.append("summary")
        try:
            output = SemaphoreClient().task_output(
                run.template.project_id, run.external_task_id
            )
        except SemaphoreError as exc:
            output_error = str(exc)
            if updates:
                run.save(update_fields=list(dict.fromkeys(updates)))
            if run.status in {AutomationRun.Status.SUCCESS, AutomationRun.Status.FAILED}:
                _sync_backup_artifact(run, None)
            return output_error
        raw_output = format_automation_output(output)
        run.output_excerpt = redact_automation_output(raw_output)[:30000]
        updates.append("output_excerpt")
        if updates:
            run.save(update_fields=list(dict.fromkeys(updates)))
        _sync_backup_artifact(run, raw_output)
    return output_error
