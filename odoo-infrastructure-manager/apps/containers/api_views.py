"""Versioned Docker inventory and task-dispatched container operations."""

from django.conf import settings
from django.core.exceptions import PermissionDenied

from apps.accounts.services.permission_service import has_permission
from apps.containers.models import (
    ComposeProject,
    DockerContainer,
    DockerEngine,
    DockerImage,
    DockerNetwork,
    DockerVolume,
)
from apps.containers.services.inventory import DockerInventoryService
from apps.core.utils.decorators import api_login_required
from apps.core.utils.http import (
    api_error,
    api_response,
    api_response_paginated,
    paginate_queryset,
    parse_json_body,
)
from apps.infrastructure.models import ManagedHost
from apps.tasks.services.dispatcher import TaskDispatchUnavailable
from apps.tasks.services.operation_tasks import queue_infrastructure_operation
from infrastructure_engine.adapters.docker.client import DockerAdapterError
from infrastructure_engine.core.engine import OperationRejected


_ACTIONS = {"start", "stop", "restart", "pause", "resume", "remove"}


@api_login_required
def docker_engines(request):
    if request.method == "GET":
        if not has_permission(request.user, "docker.container.view"):
            return api_error("Docker view permission required.", status=403)
        page, meta = paginate_queryset(
            DockerEngine.objects.select_related("host"), request
        )
        return api_response_paginated(
            [engine_to_dict(engine) for engine in page],
            meta,
            message="Docker engines loaded.",
        )
    if request.method != "POST":
        return api_error("Method not allowed.", status=405)
    if not has_permission(request.user, "docker.engine.manage"):
        return api_error("Docker engine management permission required.", status=403)
    payload, error = parse_json_body(request)
    if error:
        return error
    if not isinstance(payload, dict) or set(payload) != {"server_id"}:
        return api_error("Only a server_id may be supplied.", status=400)
    try:
        host_id = int(payload["server_id"])
    except (TypeError, ValueError):
        return api_error("server_id must be a positive integer.", status=400)
    if host_id < 1:
        return api_error("server_id must be a positive integer.", status=400)
    try:
        engine = DockerInventoryService.register_local_engine(host_id)
    except ManagedHost.DoesNotExist:
        return api_error("An enabled local managed server is required.", status=400)
    except DockerAdapterError as exc:
        return api_error(str(exc), status=503)
    return api_response(
        engine_to_dict(engine),
        message="Docker engine registered.",
        status=201,
    )


@api_login_required
def docker_engine_detail(request, engine_id):
    if request.method != "GET":
        return api_error("Method not allowed.", status=405)
    if not has_permission(request.user, "docker.container.view"):
        return api_error("Docker view permission required.", status=403)
    try:
        engine = DockerEngine.objects.select_related("host").get(pk=engine_id)
    except DockerEngine.DoesNotExist:
        return api_error("Docker engine not found.", status=404)
    return api_response(
        engine_to_dict(engine, include_resources=True),
        message="Docker engine loaded.",
    )


@api_login_required
def discover_docker_engine(request, engine_id):
    if request.method != "POST":
        return api_error("Method not allowed.", status=405)
    if request.body.strip():
        return api_error("Docker discovery does not accept a request body.", status=400)
    if not has_permission(request.user, "docker.container.view"):
        return api_error("Docker view permission required.", status=403)
    if not settings.INFRA_DOCKER_READ_ENABLED:
        return api_error("Docker discovery is not configured.", status=503)
    try:
        engine = DockerEngine.objects.select_related("host").get(pk=engine_id)
    except DockerEngine.DoesNotExist:
        return api_error("Docker engine not found.", status=404)
    return _queue_operation(
        request, engine, "docker.engine.discover", parameters={}
    )


@api_login_required
def docker_container_action(request, engine_id, container_id, action):
    if request.method != "POST":
        return api_error("Method not allowed.", status=405)
    if action not in _ACTIONS:
        return api_error("Unsupported Docker action.", status=404)
    payload, error = parse_json_body(request)
    if error:
        return error
    if not isinstance(payload, dict) or payload != {"confirmation": True}:
        return api_error("Explicit confirmation is required.", status=400)
    permission = "docker.container.delete" if action == "remove" else f"docker.container.{action}"
    if not has_permission(request.user, permission):
        return api_error("Docker action permission required.", status=403)
    if not has_permission(request.user, "task.view", "tasks_manage"):
        return api_error("Task view permission is required.", status=403)
    try:
        engine = DockerEngine.objects.select_related("host").get(pk=engine_id)
    except DockerEngine.DoesNotExist:
        return api_error("Docker engine not found.", status=404)
    try:
        task = queue_infrastructure_operation(
            operation=f"docker.container.{action}",
            target_id=engine.host_id,
            actor=request.user,
            parameters={"container_id": container_id},
            confirmation=True,
            request=request,
        )
    except TaskDispatchUnavailable as exc:
        return api_error(str(exc), status=503)
    except PermissionDenied as exc:
        return api_error(str(exc), status=403)
    except OperationRejected as exc:
        return api_error(str(exc), status=exc.status_code)
    return _task_response(task, "Docker action submitted.")


def _queue_operation(request, engine, operation, *, parameters):
    if not has_permission(request.user, "task.view", "tasks_manage"):
        return api_error("Task view permission is required.", status=403)
    try:
        task = queue_infrastructure_operation(
            operation=operation,
            target_id=engine.host_id,
            actor=request.user,
            parameters=parameters,
            request=request,
        )
    except TaskDispatchUnavailable as exc:
        return api_error(str(exc), status=503)
    except PermissionDenied as exc:
        return api_error(str(exc), status=403)
    except OperationRejected as exc:
        return api_error(str(exc), status=exc.status_code)
    return _task_response(task, "Docker discovery submitted.")


def _task_response(task, message):
    return api_response(
        {"task_id": str(task.pk), "status": task.status, "operation": task.operation},
        message=message,
        status=202,
    )


def engine_to_dict(engine, *, include_resources=False):
    payload = {
        "id": engine.pk,
        "server": {"id": engine.host_id, "name": engine.host.name},
        "enabled": engine.enabled,
        "status": engine.status,
        "endpoint": engine.endpoint,
        "engine_version": engine.engine_version,
        "api_version": engine.api_version,
        "info": engine.info,
        "last_checked_at": engine.last_checked_at,
    }
    if include_resources:
        payload["containers"] = [
            container_to_dict(item)
            for item in DockerContainer.objects.filter(engine=engine).select_related("image_record")[:500]
        ]
        payload["images"] = list(
            DockerImage.objects.filter(engine=engine).values(
                "docker_id", "repositories", "size_bytes", "created_at", "observed_at"
            )[:500]
        )
        payload["volumes"] = list(
            DockerVolume.objects.filter(engine=engine).values(
                "name", "driver", "mountpoint", "observed_at"
            )[:500]
        )
        payload["networks"] = list(
            DockerNetwork.objects.filter(engine=engine).values(
                "docker_id", "name", "driver", "scope", "subnets", "observed_at"
            )[:500]
        )
        payload["compose_projects"] = list(
            ComposeProject.objects.filter(engine=engine).values(
                "name", "status", "services", "observed_at"
            )[:500]
        )
    return payload


def container_to_dict(container):
    return {
        "id": container.docker_id,
        "name": container.name,
        "image": container.image,
        "state": container.state,
        "status": container.status,
        "health": container.health,
        "ports": container.ports,
        "networks": list(container.networks.values_list("name", flat=True)),
        "volumes": list(container.volumes.values_list("name", flat=True)),
        "mounts": container.mounts,
        "created_at": container.created_at,
        "started_at": container.started_at,
        "observed_at": container.observed_at,
    }
