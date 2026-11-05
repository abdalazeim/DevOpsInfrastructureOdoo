"""Safe task API representations; operation metadata is intentionally omitted."""

from apps.tasks.models import Task


def task_to_dict(task, *, include_logs=False):
    payload = {
        "id": str(task.pk),
        "name": task.name,
        "operation": task.operation,
        "source": {
            "app": task.source_app,
            "model": task.source_model,
            "pk": task.source_pk,
        },
        "target_server": (
            {"id": task.target_server_id, "name": task.target_server.name}
            if task.target_server_id and task.target_server
            else None
        ),
        "requested_by": (
            {"id": task.requested_by_id, "username": task.requested_by.get_username()}
            if task.requested_by_id and task.requested_by
            else None
        ),
        "priority": task.priority,
        "status": task.status,
        "status_label": task.get_status_display(),
        "result_summary": task.result_summary,
        "error_category": task.error_category,
        "error_message": task.error_message,
        "attempt_count": task.attempt_count,
        "max_attempts": task.max_attempts,
        "created_at": task.created_at,
        "queued_at": task.queued_at,
        "started_at": task.started_at,
        "finished_at": task.finished_at,
        "cancel_requested_at": task.cancel_requested_at,
    }
    if include_logs:
        logs = task.logs.order_by("-sequence")[:100]
        payload["logs"] = [
            {
                "sequence": log.sequence,
                "stream": log.stream,
                "content": log.content,
                "created_at": log.created_at,
            }
            for log in reversed(list(logs))
        ]
    return payload


def task_queryset():
    return Task.objects.select_related("requested_by", "target_server")
