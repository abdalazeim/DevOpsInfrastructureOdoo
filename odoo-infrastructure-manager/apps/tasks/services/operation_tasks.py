"""Authorized operation-to-task handoff. Worker execution revalidates policy."""
from django.core.exceptions import PermissionDenied

from apps.accounts.services.permission_service import has_permission
from apps.tasks.services.dispatcher import TaskDispatchUnavailable, dispatch_status, enqueue_task
from apps.tasks.services.task_service import append_task_log, create_task
from infrastructure_engine.core.engine import InfrastructureEngine, OperationRejected


def queue_infrastructure_operation(*, operation, target_id, actor, parameters=None,
                                   confirmation=None, request=None):
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
        source={"app": "infrastructure", "model": "ManagedHost", "pk": host.pk},
        safe_metadata={"operation_request": {
            "operation": spec.code, "target_id": host.pk,
            "parameters": normalized, "confirmation": confirmation,
        }},
        request=request,
    )
    append_task_log(task.pk, content="Infrastructure operation accepted for queue dispatch.")
    return enqueue_task(task, actor=actor)
