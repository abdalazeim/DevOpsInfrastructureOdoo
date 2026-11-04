"""Idempotent database-backed worker entry point for typed operations."""
from django.db import transaction

from apps.tasks.models import Task, TaskLog
from apps.tasks.services.task_service import append_task_log, transition_task
from infrastructure_engine.core.engine import InfrastructureEngine, OperationRejected


def run_infrastructure_task(task_id):
    with transaction.atomic():
        task = Task.objects.select_for_update().select_related("requested_by").get(pk=task_id)
        if task.status != Task.Status.QUEUED:
            return {"status": task.status, "message": "Task is no longer queued."}
        actor = task.requested_by
        task_id = task.pk
        transition_task(task.pk, Task.Status.RUNNING, actor=actor)

    task = Task.objects.select_related("requested_by").get(pk=task_id)
    actor = task.requested_by
    operation_request = task.safe_metadata.get("operation_request", {})
    try:
        if not actor or not actor.is_active:
            raise OperationRejected("The requesting account is no longer active.", status_code=401)
        result = InfrastructureEngine.execute(
            operation_request.get("operation", task.operation),
            target_id=operation_request.get("target_id", task.target_server_id),
            actor=actor,
            parameters=operation_request.get("parameters", {}),
            confirmation=operation_request.get("confirmation"),
            via_task=True,
        )
        if result.status == "success":
            append_task_log(task.pk, content=result.message)
            transition_task(task.pk, Task.Status.COMPLETED, actor=actor, result_summary=result.message)
        else:
            append_task_log(task.pk, stream=TaskLog.Stream.STDERR, content=result.message)
            transition_task(task.pk, Task.Status.FAILED, actor=actor,
                            error_category=result.status, error_message=result.message)
    except OperationRejected as exc:
        append_task_log(task.pk, stream=TaskLog.Stream.STDERR, content=str(exc))
        transition_task(task.pk, Task.Status.FAILED, actor=actor,
                        error_category=f"operation_{exc.status_code}", error_message=str(exc))
    except Exception:
        append_task_log(task.pk, stream=TaskLog.Stream.STDERR, content="The worker could not complete this operation.")
        transition_task(task.pk, Task.Status.FAILED, actor=actor,
                        error_category="worker_error", error_message="The worker could not complete this operation.")

    task.refresh_from_db()
    return {"status": task.status, "task_id": str(task.pk)}
