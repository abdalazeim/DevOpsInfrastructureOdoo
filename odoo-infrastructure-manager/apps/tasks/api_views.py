"""Authenticated REST API for durable infrastructure task records."""

from django.core.exceptions import PermissionDenied, ValidationError

from apps.accounts.services.permission_service import has_permission
from apps.core.utils.decorators import api_login_required
from apps.core.utils.http import (
    api_error,
    api_response,
    api_response_paginated,
    paginate_queryset,
)
from apps.tasks.api_serializers import task_queryset, task_to_dict
from apps.tasks.models import Task
from apps.tasks.services.dispatcher import TaskDispatchUnavailable
from apps.tasks.services.operation_tasks import retry_infrastructure_task
from apps.tasks.services.task_service import request_task_cancellation
from infrastructure_engine.core.engine import OperationRejected


@api_login_required
def task_list(request):
    if request.method != "GET":
        return api_error("Method not allowed.", status=405)
    if not has_permission(request.user, "task.view", "tasks_manage"):
        return api_error("Task view permission required.", status=403)

    queryset = task_queryset()
    status = request.GET.get("status", "").strip()
    if status:
        if status not in Task.Status.values:
            return api_error("Unknown task status filter.", status=400)
        queryset = queryset.filter(status=status)
    operation = request.GET.get("operation", "").strip()
    if operation:
        queryset = queryset.filter(operation=operation)
    target_server = request.GET.get("target_server", "").strip()
    if target_server:
        try:
            target_server = int(target_server)
        except ValueError:
            return api_error("target_server must be a positive integer.", status=400)
        if target_server < 1:
            return api_error("target_server must be a positive integer.", status=400)
        queryset = queryset.filter(target_server_id=target_server)

    page, meta = paginate_queryset(queryset, request)
    return api_response_paginated(
        [task_to_dict(task) for task in page],
        meta,
        message="Tasks loaded.",
    )


@api_login_required
def task_detail(request, task_id):
    if request.method != "GET":
        return api_error("Method not allowed.", status=405)
    if not has_permission(request.user, "task.view", "tasks_manage"):
        return api_error("Task view permission required.", status=403)
    try:
        task = task_queryset().get(pk=task_id)
    except Task.DoesNotExist:
        return api_error("Task not found.", status=404)
    return api_response(task_to_dict(task, include_logs=True), message="Task loaded.")


@api_login_required
def cancel_task(request, task_id):
    if request.method != "POST":
        return api_error("Method not allowed.", status=405)
    try:
        task = request_task_cancellation(
            task_id, actor=request.user, request=request
        )
    except PermissionDenied as exc:
        return api_error(str(exc), status=403)
    except Task.DoesNotExist:
        return api_error("Task not found.", status=404)
    except ValidationError as exc:
        return api_error("; ".join(exc.messages), status=400)
    return api_response(
        task_to_dict(task),
        message="Task cancellation recorded.",
    )


@api_login_required
def retry_task(request, task_id):
    if request.method != "POST":
        return api_error("Method not allowed.", status=405)
    try:
        task = retry_infrastructure_task(
            task_id=task_id, actor=request.user, request=request
        )
    except PermissionDenied as exc:
        return api_error(str(exc), status=403)
    except Task.DoesNotExist:
        return api_error("Task not found.", status=404)
    except TaskDispatchUnavailable as exc:
        return api_error(str(exc), status=503)
    except OperationRejected as exc:
        return api_error(str(exc), status=exc.status_code)
    except ValidationError as exc:
        return api_error("; ".join(exc.messages), status=400)

    if task.status == Task.Status.FAILED and task.error_category == "queue_publish":
        return api_response(
            task_to_dict(task),
            success=False,
            message="Retry was recorded but the task could not be published.",
            status=503,
        )
    return api_response(task_to_dict(task), message="Task retry submitted.", status=202)
