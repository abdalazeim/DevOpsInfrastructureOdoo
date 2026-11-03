from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max, Sum
from django.db.models.functions import Length
from django.utils import timezone
import json
import re

from apps.accounts.services.permission_service import has_permission, is_identity_active
from apps.core.services.audit_service import log_audit

from ..models import Task, TaskLog
from .redaction import redact_output


_TRANSITIONS = {
    Task.Status.PENDING: {Task.Status.QUEUED, Task.Status.CANCELLED, Task.Status.FAILED, Task.Status.TIMEOUT},
    Task.Status.QUEUED: {Task.Status.RUNNING, Task.Status.CANCELLED, Task.Status.FAILED, Task.Status.TIMEOUT},
    Task.Status.RUNNING: {Task.Status.COMPLETED, Task.Status.FAILED, Task.Status.CANCELLED, Task.Status.TIMEOUT},
    Task.Status.FAILED: {Task.Status.QUEUED},
    Task.Status.TIMEOUT: {Task.Status.QUEUED},
    Task.Status.COMPLETED: set(),
    Task.Status.CANCELLED: set(),
}
MAX_LOG_CHUNK = 8192
MAX_TASK_LOG_CHARS = 262144


def create_task(*, name, operation, actor, target_server=None, source=None,
                priority=Task.Priority.NORMAL, max_attempts=1, safe_metadata=None, request=None):
    if actor is not None and not is_identity_active(actor):
        raise PermissionDenied("An active account is required to create a task.")
    if not name or not operation:
        raise ValidationError("Task name and operation are required.")
    metadata = _sanitize_metadata(safe_metadata if isinstance(safe_metadata, dict) else {})
    if len(json.dumps(metadata, ensure_ascii=True).encode("utf-8")) > 4096:
        metadata = {}
    task = Task.objects.create(
        name=redact_output(name, max_length=160),
        operation=operation,
        requested_by=actor,
        target_server=target_server,
        source_app=(source or {}).get("app", "")[:80],
        source_model=(source or {}).get("model", "")[:100],
        source_pk=str((source or {}).get("pk", ""))[:100],
        priority=priority,
        max_attempts=max(1, min(int(max_attempts), 10)),
        safe_metadata=metadata,
    )
    log_audit(request, user=actor, action="other", module="tasks", object_id=task.pk,
              object_repr=task.name, new_value={"status": task.status, "operation": operation})
    return task


def transition_task(task_id, new_status, *, actor=None, result_summary="", error_category="",
                    error_message="", request=None):
    if new_status not in Task.Status.values:
        raise ValidationError("Unknown task state.")
    with transaction.atomic():
        task = Task.objects.select_for_update().get(pk=task_id)
        if new_status not in _TRANSITIONS[task.status]:
            raise ValidationError(f"Task cannot transition from {task.status} to {new_status}.")
        if new_status == Task.Status.QUEUED and task.status in {Task.Status.FAILED, Task.Status.TIMEOUT}:
            if task.attempt_count >= task.max_attempts:
                raise ValidationError("Task has no retry attempts remaining.")
        old_status = task.status
        now = timezone.now()
        task.status = new_status
        if new_status == Task.Status.QUEUED:
            task.queued_at = now
        if new_status == Task.Status.RUNNING:
            task.started_at = task.started_at or now
            task.attempt_count += 1
        if new_status in {Task.Status.COMPLETED, Task.Status.FAILED, Task.Status.CANCELLED, Task.Status.TIMEOUT}:
            task.finished_at = now
        task.result_summary = redact_output(result_summary, max_length=1000)
        task.error_category = str(error_category or "")[:80]
        task.error_message = redact_output(error_message, max_length=1000)
        task.save(update_fields=["status", "queued_at", "started_at", "finished_at", "attempt_count",
                                 "result_summary", "error_category", "error_message"])
        log_audit(request, user=actor, action="other", module="tasks", object_id=task.pk,
                  object_repr=task.name, old_value={"status": old_status},
                  new_value={"status": task.status, "error_category": task.error_category})
    return task


def request_task_cancellation(task_id, *, actor, request=None):
    if not is_identity_active(actor) or not has_permission(actor, "task.cancel", "tasks_manage"):
        raise PermissionDenied("Task cancellation permission is required.")
    with transaction.atomic():
        task = Task.objects.select_for_update().get(pk=task_id)
        if task.status not in {Task.Status.PENDING, Task.Status.QUEUED, Task.Status.RUNNING}:
            raise ValidationError("Only pending, queued, or running tasks can be cancelled.")
        now = timezone.now()
        old_status = task.status
        if task.status in {Task.Status.PENDING, Task.Status.QUEUED}:
            task.status = Task.Status.CANCELLED
            task.finished_at = now
        else:
            task.cancel_requested_at = now
        task.save(update_fields=["status", "finished_at", "cancel_requested_at"])
        log_audit(request, user=actor, action="other", module="tasks", object_id=task.pk,
                  object_repr=task.name, old_value={"status": old_status},
                  new_value={"status": task.status, "cancel_requested": True})
    return task


def append_task_log(task_id, *, stream=TaskLog.Stream.SYSTEM, content):
    if stream not in TaskLog.Stream.values:
        raise ValidationError("Unknown task log stream.")
    with transaction.atomic():
        task = Task.objects.select_for_update().get(pk=task_id)
        total = task.logs.aggregate(total=Sum(Length("content")))["total"] or 0
        remaining = MAX_TASK_LOG_CHARS - total
        if remaining <= 0:
            return False
        safe_content = redact_output(content, max_length=min(MAX_LOG_CHUNK, remaining))
        if len(safe_content) > remaining:
            safe_content = safe_content[:remaining]
        next_sequence = (task.logs.aggregate(sequence=Max("sequence"))["sequence"] or 0) + 1
        TaskLog.objects.create(task=task, sequence=next_sequence, stream=stream, content=safe_content)
        return len(safe_content) >= MAX_LOG_CHUNK or len(str(content or "")) <= MAX_LOG_CHUNK


_SENSITIVE_KEY = re.compile(r"(?i)(password|passwd|token|secret|private.?key|authorization|api.?key)")


def _sanitize_metadata(value, depth=0):
    if depth > 5:
        return "[MAX DEPTH]"
    if isinstance(value, dict):
        safe = {}
        for key, item in list(value.items())[:100]:
            key = str(key)[:80]
            if _SENSITIVE_KEY.search(key):
                safe[key] = "[REDACTED]"
            else:
                safe[key] = _sanitize_metadata(item, depth + 1)
        return safe
    if isinstance(value, (list, tuple)):
        return [_sanitize_metadata(item, depth + 1) for item in value[:100]]
    if isinstance(value, str):
        return redact_output(value, max_length=1000)
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return str(type(value).__name__)
