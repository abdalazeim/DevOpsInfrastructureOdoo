"""Typed, permission-checked gateway for infrastructure adapter operations.

Web views call this engine instead of invoking SSH, Docker, or command helpers
directly. Only registered operations with validated structured parameters run.
Mutations remain disabled until a durable task dispatcher is installed.
"""

from dataclasses import dataclass, field
from datetime import timedelta
import re
from typing import Any, Callable

from django.conf import settings
from django.utils import timezone

from apps.accounts.services.permission_service import has_permission, is_identity_active
from apps.containers.models import DockerContainer, DockerEngine
from apps.containers.services.inventory import DockerInventoryService
from apps.core.services.audit_service import log_audit
from apps.infrastructure.models import ManagedHost
from apps.infrastructure.services.discovery import discover_host
from infrastructure_engine.adapters.ssh.connection import (
    SSHConnectionAdapter,
    SSHConnectionConfigurationError,
    SSHConnectionError,
)
from infrastructure_engine.adapters.docker.client import (
    DockerAdapterError,
    perform_container_action,
)
from infrastructure_engine.adapters.systemd.service_manager import SystemdOperationError, SystemdServiceManager
from infrastructure_engine.security.command_validator import (
    InvalidOperationParameters, validate_structured_parameters,
)
from infrastructure_engine.security.execution_policy import ExecutionPolicy, PolicyViolation


class OperationRejected(Exception):
    """Operation failed policy, permission, target, or configuration checks."""

    def __init__(self, message, *, status_code=400):
        self.status_code = status_code
        super().__init__(message)


@dataclass(frozen=True)
class OperationSpec:
    code: str
    permission: str
    legacy_permissions: tuple[str, ...] = ()
    mutating: bool = False
    requires_confirmation: bool = False
    handler: Callable[..., dict[str, Any]] | None = None
    parameter_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class OperationResult:
    operation: str
    status: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)


def _ssh_test(*, host, parameters):
    if parameters:
        raise OperationRejected("This operation does not accept client-supplied command parameters.")
    return SSHConnectionAdapter.inspect(host)


def _discover_server(*, host, parameters):
    if parameters:
        raise OperationRejected("This operation does not accept client-supplied parameters.")
    try:
        snapshot = discover_host(host)
    except ValueError as exc:
        raise OperationRejected(str(exc), status_code=409) from exc
    available = sum(item.get("status") == "available" for item in snapshot.availability.values())
    data = {
        "snapshot_id": snapshot.pk,
        "source": snapshot.source,
        "snapshot_status": snapshot.status,
        "captured_at": snapshot.captured_at.isoformat(),
        "is_stale": snapshot.is_stale,
        "available_sections": available,
        "total_sections": len(snapshot.availability),
        "collection_duration_ms": snapshot.collection_duration_ms,
    }
    connection = snapshot.availability.get("connection", {})
    if connection.get("reason") == "configuration":
        data["_operation_status"] = "not_configured"
    return data


def _restart_systemd_service(*, host, parameters):
    if set(parameters) != {"unit"}:
        raise OperationRejected("A service unit is required for this operation.")
    try:
        return SystemdServiceManager.restart(host, parameters["unit"])
    except SystemdOperationError as exc:
        raise OperationRejected(str(exc), status_code=exc.status_code) from exc


def _discover_docker(*, host, parameters):
    if parameters:
        raise OperationRejected("This operation does not accept client-supplied parameters.")
    try:
        engine = host.docker_engine
    except DockerEngine.DoesNotExist as exc:
        raise OperationRejected("Register a Docker engine for this server first.", status_code=409) from exc
    result = DockerInventoryService.discover(engine)
    if not result["available"]:
        result["_operation_status"] = "failed"
    return result


def _docker_container_action(action):
    def handle(*, host, parameters):
        container_id = parameters.get("container_id")
        try:
            container = DockerContainer.objects.select_related(
                "engine", "engine__host"
            ).get(engine__host=host, docker_id=container_id)
        except DockerContainer.DoesNotExist as exc:
            raise OperationRejected(
                "The container is not in this server's managed Docker inventory.",
                status_code=404,
            ) from exc
        if timezone.now() - container.observed_at > timedelta(minutes=5):
            raise OperationRejected(
                "Refresh Docker inventory before requesting this action.",
                status_code=409,
            )

        if container.state not in _DOCKER_ACTION_STATES[action]:
            raise OperationRejected(
                f"The container state does not allow {action}.", status_code=409
            )
        try:
            return perform_container_action(
                container.engine, container.docker_id, action
            )
        except DockerAdapterError as exc:
            raise OperationRejected(
                f"Docker {action} failed: {exc}", status_code=503
            ) from exc

    return handle


def _execute_automation_template(*, host, parameters, actor):
    from apps.automation.services.execution import execute_automation_run

    return execute_automation_run(host, parameters["run_id"], actor)


OPERATIONS = {
    "server.test_connection": OperationSpec(
        code="server.test_connection",
        permission="server.connect",
        legacy_permissions=("infrastructure_manage",),
        handler=_ssh_test,
    ),
    "server.discover": OperationSpec(
        code="server.discover",
        permission="server.discover",
        legacy_permissions=("server.view", "infrastructure_view"),
        handler=_discover_server,
    ),
    "linux.service.restart": OperationSpec(
        code="linux.service.restart",
        permission="linux.service.restart",
        mutating=True,
        requires_confirmation=True,
        handler=_restart_systemd_service,
        parameter_keys=("unit",),
    ),
    "docker.engine.discover": OperationSpec(
        code="docker.engine.discover",
        permission="docker.container.view",
        handler=_discover_docker,
    ),
    "automation.template.execute": OperationSpec(
        code="automation.template.execute",
        permission="automation.playbook.execute",
        legacy_permissions=("infrastructure_manage",),
        mutating=True,
        requires_confirmation=True,
        handler=_execute_automation_template,
        parameter_keys=("run_id",),
    ),
}
_DOCKER_ACTION_STATES = {
    "start": {"created", "exited", "dead"},
    "stop": {"running"},
    "restart": {"running"},
    "pause": {"running"},
    "resume": {"paused"},
    "remove": {"created", "exited", "dead"},
}
for _action in ("start", "stop", "restart", "pause", "resume", "remove"):
    OPERATIONS[f"docker.container.{_action}"] = OperationSpec(
        code=f"docker.container.{_action}",
        permission=(
            "docker.container.delete" if _action == "remove"
            else f"docker.container.{_action}"
        ),
        mutating=True,
        requires_confirmation=True,
        handler=_docker_container_action(_action),
        parameter_keys=("container_id",),
    )


class InfrastructureEngine:
    """Policy boundary for registered infrastructure operations."""

    @classmethod
    def validate_request(cls, operation, *, target_id, actor, parameters=None,
                         confirmation=None, via_task=False):
        spec = OPERATIONS.get(operation)
        if spec is None:
            raise OperationRejected("This infrastructure operation is not registered.", status_code=404)
        if not is_identity_active(actor):
            raise OperationRejected("An active authenticated account is required.", status_code=401)
        if not has_permission(actor, spec.permission, *spec.legacy_permissions):
            raise OperationRejected("You do not have permission for this operation.", status_code=403)
        try:
            ExecutionPolicy.authorize(
                spec, confirmation=confirmation,
                task_dispatch_enabled=bool(via_task and getattr(settings, "TASK_DISPATCH_ENABLED", False)),
            )
        except PolicyViolation as exc:
            raise OperationRejected(str(exc), status_code=503 if spec.mutating else 400) from exc
        try:
            parameters = validate_structured_parameters(parameters or {}, allowed_keys=spec.parameter_keys)
        except InvalidOperationParameters as exc:
            raise OperationRejected(str(exc), status_code=400) from exc

        try:
            target_id = int(target_id)
        except (TypeError, ValueError) as exc:
            raise OperationRejected("A valid server target is required.", status_code=400) from exc
        try:
            host = ManagedHost.objects.select_related("credential").get(pk=target_id)
        except ManagedHost.DoesNotExist as exc:
            raise OperationRejected("The server target was not found.", status_code=404) from exc
        if not host.enabled:
            raise OperationRejected("Disabled servers cannot be inspected.", status_code=409)
        if spec.code == "linux.service.restart":
            try:
                SystemdServiceManager.validate(host, parameters.get("unit"))
            except SystemdOperationError as exc:
                raise OperationRejected(str(exc), status_code=exc.status_code) from exc
        if spec.code.startswith("docker.container."):
            if not getattr(settings, "INFRA_DOCKER_WRITE_ENABLED", False):
                raise OperationRejected("Docker write operations are disabled.", status_code=503)
            if not confirmation:
                raise OperationRejected("Explicit confirmation is required.", status_code=400)
            container_id = parameters.get("container_id", "")
            if not isinstance(container_id, str) or not re.fullmatch(r"[0-9a-f]{64}", container_id):
                raise OperationRejected("A full Docker container ID is required.", status_code=400)
            try:
                engine = DockerEngine.objects.get(host=host, enabled=True)
            except DockerEngine.DoesNotExist as exc:
                raise OperationRejected("No enabled Docker engine is registered for this server.", status_code=409) from exc
            if not host.is_local or engine.status != DockerEngine.Status.AVAILABLE:
                raise OperationRejected("Only an available local Docker engine can be modified.", status_code=409)
            try:
                container = DockerContainer.objects.get(engine=engine, docker_id=container_id)
            except DockerContainer.DoesNotExist as exc:
                raise OperationRejected("The container is not in this server's managed Docker inventory.", status_code=404) from exc
            if timezone.now() - container.observed_at > timedelta(minutes=5):
                raise OperationRejected("Refresh Docker inventory before requesting this action.", status_code=409)
            action = spec.code.rsplit(".", 1)[-1]
            if container.state not in _DOCKER_ACTION_STATES[action]:
                raise OperationRejected(
                    f"The container state does not allow {action}.", status_code=409
                )
        return spec, host, parameters

    @classmethod
    def execute(cls, operation, *, target_id, actor, parameters=None, confirmation=None,
                request=None, via_task=False):
        spec, host, parameters = cls.validate_request(
            operation, target_id=target_id, actor=actor, parameters=parameters,
            confirmation=confirmation, via_task=via_task,
        )

        old_status = host.connection_status
        checked_at = timezone.now()
        try:
            handler_args = {"host": host, "parameters": parameters or {}}
            if spec.code == "automation.template.execute":
                handler_args["actor"] = actor
            data = spec.handler(**handler_args)
        except SSHConnectionConfigurationError as exc:
            cls._audit(request, actor, spec, host, old_status, "not_configured")
            return OperationResult(spec.code, "not_configured", str(exc))
        except SSHConnectionError as exc:
            if spec.code == "server.test_connection":
                host.connection_status = ManagedHost.ConnectionStatus.UNREACHABLE
                host.last_checked_at = checked_at
                host.save(update_fields=["connection_status", "last_checked_at", "updated_at"])
            cls._audit(request, actor, spec, host, old_status, "failed")
            return OperationResult(spec.code, "unreachable", str(exc))
        except OperationRejected:
            raise
        except Exception:
            if spec.code == "server.test_connection":
                host.connection_status = ManagedHost.ConnectionStatus.UNREACHABLE
                host.last_checked_at = checked_at
                host.save(update_fields=["connection_status", "last_checked_at", "updated_at"])
            cls._audit(request, actor, spec, host, old_status, "failed")
            return OperationResult(spec.code, "failed", "The infrastructure adapter could not complete the operation.")

        if spec.code == "server.test_connection":
            host.connection_status = ManagedHost.ConnectionStatus.ONLINE
            host.last_checked_at = checked_at
            host.last_connection_at = checked_at
            host.operating_system = data.get("operating_system", host.operating_system)
            host.os_version = data.get("os_version", host.os_version)
            host.architecture = data.get("architecture", host.architecture)
            host.save(update_fields=["connection_status", "last_checked_at", "last_connection_at",
                                     "operating_system", "os_version", "architecture", "updated_at"])
        result_status = data.pop("_operation_status", None)
        if result_status is None:
            result_status = (
                "failed"
                if spec.code == "server.discover" and data.get("snapshot_status") == "failed"
                else "success"
            )
        cls._audit(request, actor, spec, host, old_status, result_status, data)
        message = data.get("message", f"{spec.code} completed.")
        if spec.code == "server.discover":
            message = f"System discovery {data.get('snapshot_status', 'finished')}."
        return OperationResult(spec.code, result_status, message, data)

    @staticmethod
    def _audit(request, actor, spec, host, old_status, result, data=None):
        log_audit(
            request, user=actor, action="other", module="infrastructure.operation",
            object_id=host.pk, object_repr=f"{spec.code}: {host.name}",
            old_value={"connection_status": old_status},
            new_value={"operation": spec.code, "result": result,
                       "connection_status": host.connection_status,
                       **(data or {})},
        )
