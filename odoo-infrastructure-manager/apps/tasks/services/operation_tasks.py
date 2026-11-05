"""Authorized operation-to-task handoff. Worker execution revalidates policy."""
from django.core.exceptions import PermissionDenied, ValidationError

from apps.accounts.services.permission_service import has_permission, is_identity_active
from apps.tasks.models import Task
from apps.tasks.services.dispatcher import (
    TaskDispatchUnavailable,
    dispatch_status,
    enqueue_task,
)
from apps.tasks.services.task_service import append_task_log, create_task
from infrastructure_engine.core.engine import InfrastructureEngine, OperationRejected


def queue_infrastructure_operation(*, operation, target_id, actor, parameters=None,
                                   confirmation=None, request=None, source=None):
    if not actor or not actor.is_authenticated:
        raise PermissionDenied("An authenticated account is required to queue infrastructure work.")
    if not has_permission(actor, "task.view", "tasks_manage"):
        raise PermissionDenied("Task view permission is required to queue infrastructure work.")
    status = dispatch_status()
    if not status["ready"]:
        raise TaskDispatchUnavailable(status["message"])
    spec, host, normalized = InfrastructureEngine.validate_request(
        operation, target_id=target_id, actor=actor, parameters=parameters,
        confirmation=confirmation, via_task=True,
    )
    task = create_task(
        name=f"{spec.code} · {host.name}", operation=spec.code, actor=actor,
        target_server=host,
        source=source or {"app": "infrastructure", "model": "ManagedHost", "pk": host.pk},
        safe_metadata={"operation_request": {
            "operation": spec.code, "target_id": host.pk,
            "parameters": normalized, "confirmation": confirmation,
        }},
        request=request,
    )
    append_task_log(task.pk, content="Infrastructure operation accepted for queue dispatch.")
    return enqueue_task(task, actor=actor)


def retry_infrastructure_task(*, task_id, actor, request=None):
    if not is_identity_active(actor) or not has_permission(actor, "task.retry", "tasks_manage"):
        raise PermissionDenied("Task retry permission is required.")
    task = Task.objects.select_related(
        "target_server", "requested_by"
    ).get(pk=task_id)
    if task.status not in {Task.Status.FAILED, Task.Status.TIMEOUT}:
        raise ValidationError("Only failed or timed out tasks can be retried.")
    if task.attempt_count >= task.max_attempts:
        raise ValidationError("Task has no retry attempts remaining.")

    operation_request = task.safe_metadata.get("operation_request")
    if not isinstance(operation_request, dict):
        raise ValidationError("The task does not contain a retryable operation request.")
    InfrastructureEngine.validate_request(
        operation_request.get("operation", task.operation),
        target_id=operation_request.get("target_id", task.target_server_id),
        actor=actor,
        parameters=operation_request.get("parameters", {}),
        confirmation=operation_request.get("confirmation"),
        via_task=True,
    )
    status = dispatch_status()
    if not status["ready"]:
        raise TaskDispatchUnavailable(status["message"])
    return enqueue_task(task, actor=actor, allow_retry=True)
