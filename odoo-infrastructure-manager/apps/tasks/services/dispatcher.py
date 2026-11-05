"""Optional Redis/Celery publishing for durable infrastructure task records."""
import importlib.util
from django.conf import settings
from django.core.exceptions import ValidationError

from apps.tasks.models import Task
from apps.tasks.services.task_service import transition_task


class TaskDispatchUnavailable(Exception):
    """The configured queue cannot accept infrastructure work."""


def dispatch_is_configured():
    return dispatch_status()["ready"]


def dispatch_status():
    if not getattr(settings, "TASK_DISPATCH_ENABLED", False):
        return {"ready": False, "status": "disabled", "message": "Task dispatch is disabled."}
    broker_url = getattr(settings, "CELERY_BROKER_URL", "")
    if not broker_url:
        return {"ready": False, "status": "missing_broker", "message": "Configure CELERY_BROKER_URL."}
    if importlib.util.find_spec("celery") is None:
        return {"ready": False, "status": "missing_dependency", "message": "Install the Celery task runtime."}
    if broker_url.startswith(("redis://", "rediss://")) and importlib.util.find_spec("redis") is None:
        return {"ready": False, "status": "missing_dependency", "message": "Install the Redis transport dependency."}
    return {"ready": True, "status": "configured", "message": "Queue settings are configured; worker availability has not been checked."}


def publish_task(task_id):
    from apps.tasks.tasks import execute_infrastructure_task

    execute_infrastructure_task.apply_async(args=[str(task_id)], task_id=str(task_id))


def enqueue_task(task: Task, *, actor, allow_retry=False):
    status = dispatch_status()
    if not status["ready"]:
        raise TaskDispatchUnavailable(status["message"])
    if allow_retry and task.status not in {Task.Status.FAILED, Task.Status.TIMEOUT}:
        raise ValidationError("Only failed or timed out tasks can be retried.")
    queued = transition_task(task.pk, Task.Status.QUEUED, actor=actor)
    try:
        publish_task(queued.pk)
    except Exception as exc:
        failed = transition_task(
            queued.pk, Task.Status.FAILED, actor=actor,
            error_category="queue_publish", error_message=type(exc).__name__,
        )
        return failed
    return queued
