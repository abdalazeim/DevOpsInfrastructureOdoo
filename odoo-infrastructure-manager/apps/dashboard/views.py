import json
import re
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django.http import HttpResponseForbidden, HttpResponseNotFound, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.core.paginator import Paginator
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.utils import timezone

from apps.automation.models import ApprovedTaskTemplate, AutomationRun, AutomationSchedule
from apps.automation.services import (
    AutomationValidationError,
    SemaphoreClient,
    SemaphoreError,
    queue_automation_run,
)
from apps.automation.services.tracking import (
    refresh_automation_run,
)
from apps.backup.models import BackupArtifact, BackupPolicy
from apps.backup.services.workflows import (
    is_valid_artifact_ref,
    launch_backup_policy,
    queue_backup_restore,
    save_backup_policy as save_backup_policy_workflow,
    sync_backup_artifact,
)
from apps.core.services.audit_service import log_audit
from apps.core.models import AuditLog
from apps.accounts.services.permission_service import has_permission
from apps.containers.models import DockerContainer, DockerEngine
from apps.containers.services.inventory import DockerInventoryService
from apps.databases.models import DatabaseInstance
from apps.django_projects.models import DjangoProject
from apps.infrastructure.models import (
    InfrastructureSyncRecord,
    ManagedHost,
    ManagedService,
    ServerGroup,
    ServerTag,
)
from apps.security.models import Credential
from apps.security.services.credentials import CredentialEncryptionError, is_credential_encryption_ready
from infrastructure_engine.core.engine import InfrastructureEngine, OperationRejected
from apps.monitoring.models import AlertEvent, AlertRule, MetricCollection
from apps.tasks.models import Task
from apps.tasks.services.task_service import request_task_cancellation
from apps.tasks.services.operation_tasks import (
    queue_infrastructure_operation,
    retry_infrastructure_task,
)
from apps.tasks.services.dispatcher import TaskDispatchUnavailable, dispatch_status
from infrastructure_engine.adapters.docker.client import (
    DockerAdapterError,
    read_container_logs,
)

from .forms import (AlertRuleForm, ApprovedTaskTemplateForm, AutomationScheduleForm, BackupPolicyForm, CredentialCreateForm, GlobalSettingsForm,
                    ManagedHostForm, ManagedServiceForm, QuickConnectServerForm,
                    ServerGroupForm, ServerTagForm)
from .services.container_service import ContainerDiscoveryService
from .services.overview_service import DashboardOverviewService
from .services.traefik_service import TraefikReadOnlyService


def infrastructure_view_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not _can_view(request.user):
            return HttpResponseForbidden("Infrastructure view permission required.")
        return view(request, *args, **kwargs)
    return wrapped


def docker_view_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not _can_view(request.user) and not has_permission(
            request.user, "docker.container.view"
        ):
            return HttpResponseForbidden("Docker view permission required.")
        return view(request, *args, **kwargs)
    return wrapped


@infrastructure_view_required
@require_GET
def index(request):
    overview = DashboardOverviewService.build()
    templates = ApprovedTaskTemplate.objects.filter(enabled=True).exclude(
        category__in=[
            ApprovedTaskTemplate.Category.BACKUP,
            ApprovedTaskTemplate.Category.RESTORE,
        ]
    ).select_related("host", "service")
    runs = AutomationRun.objects.select_related("template", "requested_by")[:8]
    recent_alerts = AlertEvent.objects.select_related("rule", "host")[:6]
    return render(request, "dashboard/index.html", {
        "overview": overview,
        "approved_templates": templates,
        "recent_runs": runs,
        "recent_alerts": recent_alerts,
        "can_manage_infrastructure": _can_manage(request.user),
        "can_run_automation": (
            has_permission(request.user, "automation.playbook.execute", "infrastructure_manage")
            and has_permission(request.user, "task.view", "tasks_manage")
        ),
        "nav_sections": _navigation(active="dashboard"),
    })


@docker_view_required
@require_http_methods(["GET", "POST"])
def containers(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "register":
            if not has_permission(request.user, "docker.engine.manage"):
                return HttpResponseForbidden("Docker engine management permission required.")
            try:
                host_id = int(request.POST.get("server_id", ""))
                engine = DockerInventoryService.register_local_engine(host_id)
            except (TypeError, ValueError, ManagedHost.DoesNotExist):
                messages.error(request, "Select an enabled local managed server.")
                return redirect("dashboard:containers")
            messages.success(request, f"Docker engine registered for {engine.host.name}.")
            return redirect(f"{reverse('dashboard:containers')}?engine={engine.pk}")

        try:
            engine = DockerEngine.objects.select_related("host").get(
                pk=int(request.POST.get("engine_id", ""))
            )
        except (TypeError, ValueError, DockerEngine.DoesNotExist):
            messages.error(request, "Select a registered Docker engine.")
            return redirect("dashboard:containers")

        if action == "discover":
            if not has_permission(request.user, "docker.container.view"):
                return HttpResponseForbidden("Docker view permission required.")
            if not settings.INFRA_DOCKER_READ_ENABLED:
                messages.error(request, "Docker discovery is not configured.")
                return redirect(f"{reverse('dashboard:containers')}?engine={engine.pk}")
            if not has_permission(request.user, "task.view", "tasks_manage"):
                return HttpResponseForbidden("Task view permission required.")
            try:
                task = queue_infrastructure_operation(
                    operation="docker.engine.discover",
                    target_id=engine.host_id,
                    actor=request.user,
                    parameters={},
                    request=request,
                )
            except TaskDispatchUnavailable as exc:
                messages.error(request, str(exc))
            except PermissionDenied as exc:
                return HttpResponseForbidden(str(exc))
            except OperationRejected as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, f"Docker discovery queued as task {task.pk}.")
            return redirect(f"{reverse('dashboard:containers')}?engine={engine.pk}")

        action = request.POST.get("container_action", "")
        allowed_actions = {"start", "stop", "restart", "pause", "resume", "remove"}
        permission = "docker.container.delete" if action == "remove" else f"docker.container.{action}"
        if (
            action not in allowed_actions
            or not settings.INFRA_DOCKER_WRITE_ENABLED
            or request.POST.get("confirmation") != "yes"
        ):
            messages.error(request, "The Docker action is unavailable or requires explicit confirmation.")
            return redirect(f"{reverse('dashboard:containers')}?engine={engine.pk}")
        if not has_permission(request.user, permission):
            return HttpResponseForbidden("Docker action permission required.")
        if not has_permission(request.user, "task.view", "tasks_manage"):
            return HttpResponseForbidden("Task view permission required.")
        try:
            task = queue_infrastructure_operation(
                operation=f"docker.container.{action}",
                target_id=engine.host_id,
                actor=request.user,
                parameters={"container_id": request.POST.get("container_id", "")},
                confirmation=True,
                request=request,
            )
        except TaskDispatchUnavailable as exc:
            messages.error(request, str(exc))
        except PermissionDenied as exc:
            return HttpResponseForbidden(str(exc))
        except OperationRejected as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"Docker action queued as task {task.pk}.")
        return redirect(f"{reverse('dashboard:containers')}?engine={engine.pk}")

    engines = DockerEngine.objects.select_related("host").order_by("host__name")
    selected_engine = None
    requested_engine = request.GET.get("engine")
    if requested_engine:
        try:
            selected_engine = engines.filter(pk=int(requested_engine)).first()
        except (TypeError, ValueError):
            selected_engine = None
    if selected_engine is None:
        selected_engine = engines.first()

    result = ContainerDiscoveryService.list_containers(selected_engine)
    if selected_engine is None and not result["available"]:
        result["reason"] = "Docker provider unavailable. " + result["reason"]
    containers = result["containers"]
    queue_status = dispatch_status()
    return render(request, "dashboard/containers.html", {
        "discovery": result,
        "containers": containers,
        "engines": engines,
        "selected_engine": selected_engine,
        "local_hosts": ManagedHost.objects.filter(enabled=True, is_local=True).order_by("name"),
        "can_register_docker": has_permission(request.user, "docker.engine.manage"),
        "can_view_docker": has_permission(request.user, "docker.container.view"),
        "can_discover_docker": (
            settings.INFRA_DOCKER_READ_ENABLED
            and has_permission(request.user, "docker.container.view")
            and has_permission(request.user, "task.view", "tasks_manage")
        ),
        "can_write_docker": (
            settings.INFRA_DOCKER_WRITE_ENABLED
            and queue_status["ready"]
            and has_permission(request.user, "task.view", "tasks_manage")
        ),
        "docker_actions": [
            {
                "name": action,
                "allowed": has_permission(
                    request.user,
                    "docker.container.delete" if action == "remove" else f"docker.container.{action}",
                ),
                "states": (
                    ["created", "exited", "dead"]
                    if action in {"start", "remove"}
                    else ["running"] if action in {"stop", "restart", "pause"}
                    else ["paused"]
                ),
            }
            for action in ("start", "stop", "restart", "pause", "resume", "remove")
        ],
        "can_view_tasks": has_permission(request.user, "task.view", "tasks_manage"),
        "task_dispatch_status": queue_status,
        "nav_sections": _navigation(active="containers"),
    })


@infrastructure_view_required
@require_GET
def inventory(request):
    hosts = list(
        ManagedHost.objects.prefetch_related(
            "groups",
            "tags",
            Prefetch(
                "sync_records",
                queryset=InfrastructureSyncRecord.objects.order_by("-completed_at")[:5],
                to_attr="recent_sync_records",
            ),
        )
        .select_related("latest_snapshot", "credential")
        .all()
    )
    services = list(ManagedService.objects.select_related("host").all())
    queue_status = dispatch_status()
    for host in hosts:
        host.edit_form = ManagedHostForm(instance=host, prefix=f"h{host.pk}")
    for service in services:
        service.edit_form = ManagedServiceForm(instance=service, prefix=f"s{service.pk}")
    return render(request, "dashboard/inventory.html", {
        "hosts": hosts,
        "services": services,
        "host_form": ManagedHostForm(),
        "service_form": ManagedServiceForm(),
        "server_group_form": ServerGroupForm(),
        "server_tag_form": ServerTagForm(),
        "server_groups": ServerGroup.objects.all(),
        "server_tags": ServerTag.objects.all(),
        "credential_form": CredentialCreateForm() if has_permission(request.user, "security.credentials.manage") else None,
        "credentials": Credential.objects.only("id", "name", "kind", "username", "is_active").order_by("name")
            if has_permission(request.user, "security.credentials.manage") else [],
        "credential_encryption_ready": is_credential_encryption_ready(),
        "can_manage_infrastructure": _can_manage(request.user),
        "can_create_servers": has_permission(request.user, "server.create", "infrastructure_manage"),
        "can_update_servers": has_permission(request.user, "server.update", "infrastructure_manage"),
        "can_test_server_connection": has_permission(request.user, "server.connect", "infrastructure_manage"),
        "can_discover_servers": has_permission(
            request.user, "server.discover", "server.view", "infrastructure_view"
        ),
        "task_dispatch_enabled": queue_status["ready"],
        "task_dispatch_status": queue_status,
        "can_view_tasks": has_permission(request.user, "task.view", "tasks_manage"),
        "can_restart_linux_services": has_permission(request.user, "linux.service.restart"),
        "nav_sections": _navigation(active="inventory"),
    })


@login_required
@require_POST
def create_credential(request):
    if not has_permission(request.user, "security.credentials.manage"):
        return HttpResponseForbidden("Credential management permission required.")
    form = CredentialCreateForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Credential was not saved. Review the fields and try again.")
        return redirect("dashboard:inventory")
    try:
        credential = form.save(actor=request.user)
    except CredentialEncryptionError:
        messages.error(request, "Credential encryption is unavailable. Configure CREDENTIAL_ENCRYPTION_KEY first.")
        return redirect("dashboard:inventory")
    log_audit(request, action="create", module="security.credentials", object_id=credential.pk,
              object_repr=f"Credential {credential.name} ({credential.kind})")
    messages.success(request, "Credential saved in encrypted form.")
    return redirect("dashboard:inventory")


@login_required
@require_POST
def toggle_credential(request, credential_id):
    if not has_permission(request.user, "security.credentials.manage"):
        return HttpResponseForbidden("Credential management permission required.")
    credential = get_object_or_404(Credential, pk=credential_id)
    old_state = credential.is_active
    credential.is_active = not old_state
    credential.save(update_fields=["is_active", "updated_at"])
    log_audit(request, action="update", module="security.credentials", object_id=credential.pk,
              object_repr=f"Credential {credential.name}", old_value={"active": old_state},
              new_value={"active": credential.is_active})
    messages.success(request, f"Credential {credential.name} is now {'active' if credential.is_active else 'disabled'}.")
    return redirect("dashboard:inventory")


@login_required
@require_http_methods(["GET", "POST"])
def global_settings(request):
    if not has_permission(request.user, "settings.view", "settings.manage", "settings_manage"):
        return HttpResponseForbidden("Global settings permission required.")
    can_manage = has_permission(request.user, "settings.manage", "settings_manage")
    form = GlobalSettingsForm(request.POST or None)
    if not can_manage:
        for field in form.fields.values():
            field.disabled = True
    if request.method == "POST":
        if not can_manage:
            return HttpResponseForbidden("Global settings management permission required.")
        if form.is_valid():
            changes = form.save()
            for key, old_value, new_value in changes:
                log_audit(request, action="update", module="core.settings", object_id=key,
                          object_repr=key, old_value={"value": old_value},
                          new_value={"value": new_value})
            messages.success(request, f"Saved {len(changes)} setting(s). Environment overrides remain authoritative.")
            return redirect("dashboard:global_settings")
    return render(request, "dashboard/settings.html", {
        "form": form,
        "can_manage_settings": can_manage,
        "quick_connect_form": QuickConnectServerForm() if has_permission(request.user, "server.create", "infrastructure_manage") else None,
        "can_create_servers": has_permission(request.user, "server.create", "infrastructure_manage"),
        "can_test_server_connection": has_permission(request.user, "server.connect", "infrastructure_manage"),
        "credential_encryption_ready": is_credential_encryption_ready(),
        "nav_sections": _navigation(active="settings"),
    })


@login_required
@require_POST
def quick_connect_server(request):
    if not has_permission(request.user, "server.create", "infrastructure_manage"):
        return HttpResponseForbidden("Server registration permission required.")
    form = QuickConnectServerForm(request.POST)
    if not form.is_valid():
        for field, errors in form.errors.items():
            messages.error(request, f"{field}: {', '.join(errors)}")
        return redirect("dashboard:global_settings")
    try:
        host = form.save(actor=request.user)
    except CredentialEncryptionError:
        messages.error(request, "The SSH password was not saved. Configure credential encryption and try again.")
        return redirect("dashboard:global_settings")
    except IntegrityError:
        messages.error(request, "A server with this name is already registered, or the local application host already exists.")
        return redirect("dashboard:global_settings")

    if host.credential_id:
        log_audit(request, action="create", module="security.credentials", object_id=host.credential_id,
                  object_repr=f"SSH credential for {host.name}")
    log_audit(request, action="create", module="infrastructure.host", object_id=host.pk,
              object_repr=f"Managed host {host.name}")

    if host.is_local and has_permission(request.user, "server.view", "infrastructure_view"):
        try:
            result = InfrastructureEngine.execute(
                "server.discover", target_id=host.pk, actor=request.user,
                parameters={}, request=request,
            )
            if result.status == "success":
                messages.success(request, f"{host.name} was added and local system data was collected.")
            else:
                messages.warning(request, f"{host.name} was added, but local discovery returned {result.status}.")
        except OperationRejected as exc:
            messages.warning(request, f"{host.name} was saved. Local discovery: {exc}")
    elif host.connection_type == ManagedHost.ConnectionType.SSH and has_permission(request.user, "server.connect", "infrastructure_manage"):
        try:
            result = InfrastructureEngine.execute(
                "server.test_connection", target_id=host.pk, actor=request.user,
                parameters={}, request=request,
            )
            if result.status == "success":
                messages.success(request, f"{host.name} was saved and the SSH connection was verified.")
            else:
                messages.warning(request, f"{host.name} was saved, but the SSH connection could not be verified: {result.message}")
        except OperationRejected as exc:
            messages.warning(request, f"{host.name} was saved. Connection test: {exc}")
    else:
        messages.success(request, f"{host.name} was added to the server inventory.")
    return redirect("dashboard:inventory")


@login_required
@require_GET
def tasks_list(request):
    if not has_permission(request.user, "task.view", "tasks_manage"):
        return HttpResponseForbidden("Task view permission required.")
    selected_status = request.GET.get("status", "")
    tasks = Task.objects.select_related("requested_by", "target_server")
    if selected_status in Task.Status.values:
        tasks = tasks.filter(status=selected_status)
    page = Paginator(tasks, 25).get_page(request.GET.get("page"))
    return render(request, "dashboard/tasks.html", {
        "page": page, "selected_status": selected_status,
        "statuses": Task.Status.choices,
        "dispatch_status": dispatch_status(),
        "can_cancel_tasks": has_permission(request.user, "task.cancel", "tasks_manage"),
        "nav_sections": _navigation(active="tasks"),
    })


@login_required
@require_GET
def task_detail(request, task_id):
    if not has_permission(request.user, "task.view", "tasks_manage"):
        return HttpResponseForbidden("Task view permission required.")
    task = get_object_or_404(Task.objects.select_related("requested_by", "target_server"), pk=task_id)
    logs = task.logs.order_by("-sequence")[:100]
    return render(request, "dashboard/task_detail.html", {
        "task": task, "logs": reversed(list(logs)),
        "can_cancel_tasks": has_permission(request.user, "task.cancel", "tasks_manage"),
        "can_retry_task": (
            has_permission(request.user, "task.retry", "tasks_manage")
            and task.status in {Task.Status.FAILED, Task.Status.TIMEOUT}
            and task.attempt_count < task.max_attempts
            and dispatch_status()["ready"]
        ),
        "nav_sections": _navigation(active="tasks"),
    })


@login_required
@require_POST
def cancel_task(request, task_id):
    try:
        task = request_task_cancellation(task_id, actor=request.user, request=request)
    except PermissionDenied as exc:
        return HttpResponseForbidden(str(exc))
    except (Task.DoesNotExist, ValidationError) as exc:
        messages.error(request, str(exc))
        return redirect("dashboard:tasks")
    messages.success(request, f"Cancellation recorded for task {task.pk}.")
    return redirect("dashboard:task_detail", task_id=task.pk)


@login_required
@require_POST
def retry_task(request, task_id):
    try:
        task = retry_infrastructure_task(
            task_id=task_id, actor=request.user, request=request
        )
    except PermissionDenied as exc:
        return HttpResponseForbidden(str(exc))
    except Task.DoesNotExist:
        messages.error(request, "Task not found.")
        return redirect("dashboard:tasks")
    except TaskDispatchUnavailable as exc:
        messages.error(request, str(exc))
        return redirect("dashboard:task_detail", task_id=task_id)
    except OperationRejected as exc:
        messages.error(request, str(exc))
        return redirect("dashboard:task_detail", task_id=task_id)
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
        return redirect("dashboard:task_detail", task_id=task_id)
    if task.status == Task.Status.FAILED and task.error_category == "queue_publish":
        messages.error(request, "Retry was recorded but the task could not be published.")
    else:
        messages.success(request, f"Task {task.pk} was queued for retry.")
    return redirect("dashboard:task_detail", task_id=task.pk)


@login_required
@require_POST
def create_inventory_item(request, item_type):
    if item_type == "host":
        if not has_permission(request.user, "server.create", "infrastructure_manage"):
            return JsonResponse({"error": "Server creation permission required."}, status=403)
        form = ManagedHostForm(request.POST)
        module = "infrastructure.host"
        label = "host"
    elif item_type == "service":
        if not _can_manage(request.user):
            return JsonResponse({"error": "Infrastructure management permission required."}, status=403)
        form = ManagedServiceForm(request.POST)
        module = "infrastructure.service"
        label = "service"
    else:
        return JsonResponse({"error": "Unsupported inventory item."}, status=404)
    if form.is_valid():
        obj = form.save()
        log_audit(request, action="create", module=module, object_id=obj.pk, object_repr=str(obj))
        messages.success(request, f"The {label} was added to inventory.")
    else:
        for field, errors in form.errors.items():
            messages.error(request, f"{field}: {', '.join(errors)}")
    return redirect("dashboard:inventory")


@login_required
@require_POST
def create_server_group(request):
    if not has_permission(request.user, "infrastructure_manage"):
        return HttpResponseForbidden("Infrastructure management permission required.")
    form = ServerGroupForm(request.POST)
    if form.is_valid():
        with transaction.atomic():
            group = form.save()
            log_audit(request, action="create", module="infrastructure.server_group",
                      object_id=group.pk, object_repr=group.name)
        messages.success(request, "Server group created.")
    else:
        for field, errors in form.errors.items():
            messages.error(request, f"{field}: {', '.join(errors)}")
    return redirect("dashboard:inventory")


@login_required
@require_POST
def create_server_tag(request):
    if not has_permission(request.user, "infrastructure_manage"):
        return HttpResponseForbidden("Infrastructure management permission required.")
    form = ServerTagForm(request.POST)
    if form.is_valid():
        with transaction.atomic():
            tag = form.save()
            log_audit(request, action="create", module="infrastructure.server_tag",
                      object_id=tag.pk, object_repr=tag.name)
        messages.success(request, "Server tag created.")
    else:
        for field, errors in form.errors.items():
            messages.error(request, f"{field}: {', '.join(errors)}")
    return redirect("dashboard:inventory")


@login_required
@require_POST
def test_server_connection(request, host_id):
    try:
        result = InfrastructureEngine.execute(
            "server.test_connection", target_id=host_id, actor=request.user,
            parameters={}, request=request,
        )
    except OperationRejected as exc:
        return JsonResponse({"error": str(exc)}, status=exc.status_code)
    status_code = {"success": 200, "not_configured": 409, "unreachable": 503, "failed": 503}[result.status]
    return JsonResponse({"status": result.status, "message": result.message, **result.data}, status=status_code)


@login_required
@require_POST
def queue_server_connection_test(request, host_id):
    return _queue_server_operation(request, host_id, "server.test_connection")


@login_required
@require_POST
def queue_server_discovery(request, host_id):
    return _queue_server_operation(request, host_id, "server.discover")


@login_required
@require_POST
def queue_linux_service_restart(request, host_id):
    confirmed = request.POST.get("confirmation", "").strip() == "RESTART"
    try:
        task = queue_infrastructure_operation(
            operation="linux.service.restart", target_id=host_id,
            actor=request.user, parameters={"unit": request.POST.get("unit", "")},
            confirmation=confirmed, request=request,
        )
    except TaskDispatchUnavailable as exc:
        messages.error(request, str(exc))
        return redirect("dashboard:inventory")
    except PermissionDenied as exc:
        return HttpResponseForbidden(str(exc))
    except OperationRejected as exc:
        messages.error(request, str(exc))
        return redirect("dashboard:inventory")
    if task.status == Task.Status.QUEUED:
        messages.success(request, f"Restart of {request.POST.get('unit', 'service')} queued as task {task.pk}.")
    else:
        messages.error(request, f"Service restart task {task.pk} could not be dispatched.")
    return redirect("dashboard:tasks")


def _queue_server_operation(request, host_id, operation):
    try:
        task = queue_infrastructure_operation(
            operation=operation, target_id=host_id,
            actor=request.user, parameters={}, request=request,
        )
    except TaskDispatchUnavailable as exc:
        messages.error(request, str(exc))
        return redirect("dashboard:inventory")
    except PermissionDenied as exc:
        return HttpResponseForbidden(str(exc))
    except OperationRejected as exc:
        return HttpResponseForbidden(str(exc)) if exc.status_code == 403 else JsonResponse(
            {"error": str(exc)}, status=exc.status_code,
        )
    if task.status == Task.Status.QUEUED:
        messages.success(request, f"{operation} queued as task {task.pk}.")
    else:
        messages.error(request, f"{operation} task {task.pk} could not be dispatched.")
    return redirect("dashboard:tasks")


@login_required
@require_POST
def discover_server(request, host_id):
    try:
        result = InfrastructureEngine.execute(
            "server.discover", target_id=host_id, actor=request.user,
            parameters={}, request=request,
        )
    except OperationRejected as exc:
        return JsonResponse({"error": str(exc)}, status=exc.status_code)
    http_status = (
        409 if result.status == "not_configured"
        else 503 if result.status == "failed"
        else 206 if result.data.get("snapshot_status") == "partial"
        else 200
    )
    return JsonResponse({"status": result.status, "message": result.message, **result.data}, status=http_status)


@login_required
@require_POST
def update_inventory_item(request, item_type, item_id):
    if item_type == "host":
        if not has_permission(request.user, "server.update", "infrastructure_manage"):
            return JsonResponse({"error": "Server update permission required."}, status=403)
        obj = get_object_or_404(ManagedHost, pk=item_id)
        form = ManagedHostForm(request.POST, instance=obj, prefix=f"h{obj.pk}")
        module = "infrastructure.host"
    elif item_type == "service":
        if not _can_manage(request.user):
            return JsonResponse({"error": "Infrastructure management permission required."}, status=403)
        obj = get_object_or_404(ManagedService, pk=item_id)
        form = ManagedServiceForm(request.POST, instance=obj, prefix=f"s{obj.pk}")
        module = "infrastructure.service"
    else:
        return JsonResponse({"error": "Unsupported inventory item."}, status=404)
    if form.is_valid():
        updated = form.save()
        log_audit(request, action="update", module=module, object_id=updated.pk, object_repr=str(updated))
        messages.success(request, "Inventory details were updated.")
    else:
        for field, errors in form.errors.items():
            messages.error(request, f"{field}: {', '.join(errors)}")
    return redirect("dashboard:inventory")


@infrastructure_view_required
@require_GET
def automation_templates(request):
    return render(request, "dashboard/automation_templates.html", {
        "templates": ApprovedTaskTemplate.objects.exclude(
            category__in=[
                ApprovedTaskTemplate.Category.BACKUP,
                ApprovedTaskTemplate.Category.RESTORE,
            ]
        ).select_related("host", "service"),
        "schedules": AutomationSchedule.objects.select_related("template", "created_by"),
        "template_form": ApprovedTaskTemplateForm(),
        "can_manage_infrastructure": _can_manage_automation(request.user),
        "nav_sections": _navigation(active="automation"),
    })


@login_required
@require_POST
def create_automation_template(request):
    if not _can_manage_automation(request.user):
        return JsonResponse({"error": "Permission denied."}, status=403)
    form = ApprovedTaskTemplateForm(request.POST)
    if form.is_valid():
        template = form.save(commit=False)
        template.enabled = False
        template.save()
        log_audit(request, action="create", module="automation.template", object_id=template.pk,
                  object_repr=template.name, new_value={"enabled": False})
        messages.success(request, "The template was added disabled. Review its scope before approving it.")
    else:
        for field, errors in form.errors.items():
            messages.error(request, f"{field}: {', '.join(errors)}")
    return redirect("dashboard:automation_templates")


@login_required
@require_POST
def toggle_automation_template(request, template_id):
    if not _can_manage_automation(request.user):
        return JsonResponse({"error": "Permission denied."}, status=403)
    template = get_object_or_404(ApprovedTaskTemplate, pk=template_id)
    enabling = request.POST.get("enabled") == "yes"
    if enabling:
        limit = template.host.ansible_limit if template.host_id else ""
        if not template.host_id or not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", limit) or limit.lower() in {"all", "*", "ungrouped"}:
            messages.error(request, "This template needs a host and a specific inventory limit before approval.")
            return redirect("dashboard:automation_templates")
    if enabling and template.category == ApprovedTaskTemplate.Category.DISCOVERY:
        template.read_only = True
    template.enabled = enabling
    template.save(update_fields=["enabled", "read_only"])
    if not enabling:
        AutomationSchedule.objects.filter(template=template).update(
            enabled=False, next_run_at=None, updated_at=timezone.now()
        )
    log_audit(request, action="approve" if enabling else "update", module="automation.template",
              object_id=template.pk, object_repr=template.name, new_value={"enabled": enabling})
    messages.success(request, "Template approved." if enabling else "Template disabled.")
    return redirect("dashboard:automation_templates")


@login_required
@require_POST
def save_automation_schedule(request, template_id):
    if not _can_manage_automation(request.user):
        return JsonResponse({"error": "Permission denied."}, status=403)
    template = get_object_or_404(ApprovedTaskTemplate, pk=template_id)
    schedule, _ = AutomationSchedule.objects.get_or_create(
        template=template, defaults={"created_by": request.user}
    )
    form = AutomationScheduleForm(request.POST, instance=schedule)
    if not form.is_valid():
        for field, errors in form.errors.items():
            messages.error(request, f"{field}: {', '.join(errors)}")
        return redirect("dashboard:automation_templates")
    schedule = form.save(commit=False)
    variables = form.cleaned_data["variables_json"]
    if variables is not None:
        from apps.security.services.credentials import CredentialEncryptionError, encrypt_secret

        try:
            schedule.encrypted_variables = (
                encrypt_secret(json.dumps(variables, ensure_ascii=True, separators=(",", ":")))
                if variables else ""
            )
        except CredentialEncryptionError:
            messages.error(request, "Secure variable storage is not configured for automation.")
            return redirect("dashboard:automation_templates")
        schedule.variable_names = sorted(variables)
    schedule.created_by = request.user
    schedule.next_run_at = (
        timezone.now() + timedelta(minutes=schedule.interval_minutes) if schedule.enabled else None
    )
    schedule.last_error = ""
    schedule.save()
    log_audit(
        request, action="update", module="automation.schedule", object_id=schedule.pk,
        object_repr=template.name,
        new_value={"enabled": schedule.enabled, "interval_minutes": schedule.interval_minutes},
    )
    messages.success(request, "Automation schedule saved. Scheduled runs use dry-run mode only.")
    return redirect("dashboard:automation_templates")


@docker_view_required
@require_GET
def docker_resources(request, resource_type):
    if resource_type not in {"images", "networks", "volumes", "compose"}:
        return JsonResponse({"error": "Unsupported Docker resource type."}, status=404)
    selected_engine = None
    requested_engine = request.GET.get("engine")
    if requested_engine:
        try:
            selected_engine = DockerEngine.objects.select_related("host").get(
                pk=int(requested_engine)
            )
        except (TypeError, ValueError, DockerEngine.DoesNotExist):
            return HttpResponseNotFound("Docker engine not found.")
    result = ContainerDiscoveryService.list_resources(resource_type, selected_engine)
    return render(request, "dashboard/docker_resources.html", {
        "resource_type": resource_type,
        "discovery": result,
        "items": result["items"],
        "selected_engine": selected_engine or result.get("engine"),
        "nav_sections": _navigation(active="containers"),
    })


@infrastructure_view_required
@require_GET
def odoo_services(request):
    services = DashboardOverviewService.service_items(
        ManagedService.objects.filter(enabled=True, kind=ManagedService.Kind.ODOO).select_related("host")
    )
    return render(request, "dashboard/service_catalog.html", {
        "title": "Odoo environments", "subtitle": "Each registered Odoo environment is shown independently.",
        "services": services, "nav_sections": _navigation(active="odoo"),
    })


@infrastructure_view_required
@require_GET
def django_projects(request):
    projects = DashboardOverviewService.service_items(
        DjangoProject.objects.filter(enabled=True).select_related("host")
    )
    return render(request, "dashboard/service_catalog.html", {
        "title": "Django projects", "subtitle": "Registered projects and their configured run methods.",
        "projects": projects, "nav_sections": _navigation(active="django"),
    })


@infrastructure_view_required
@require_GET
def database_services(request):
    databases = DatabaseInstance.objects.filter(enabled=True).select_related("host")
    redis_services = DashboardOverviewService.service_items(
        ManagedService.objects.filter(enabled=True, kind=ManagedService.Kind.REDIS).select_related("host")
    )
    return render(request, "dashboard/service_catalog.html", {
        "title": "Databases & Redis", "subtitle": "Inventory and container state only; credentials and database contents are never displayed.",
        "databases": databases, "redis_services": redis_services,
        "nav_sections": _navigation(active="databases"),
    })


@login_required
@require_GET
def backups(request):
    if not has_permission(
        request.user, "backup.view", "infrastructure_view", "server.view"
    ):
        return HttpResponseForbidden("Backup view permission required.")
    artifacts = list(BackupArtifact.objects.select_related(
        "host", "service", "policy", "created_by", "automation_run"
    )[:100])
    restore_actions = []
    for artifact in artifacts:
        if (
            artifact.status != BackupArtifact.Status.SUCCESS
            or not is_valid_artifact_ref(artifact.artifact_ref)
        ):
            continue
        compatible_templates = ApprovedTaskTemplate.objects.filter(
            enabled=True,
            category=ApprovedTaskTemplate.Category.RESTORE,
            host_id=artifact.host_id,
            service_id=artifact.service_id,
        )
        if compatible_templates.exists():
            restore_actions.append(
                {"artifact": artifact, "templates": compatible_templates}
            )
    return render(request, "dashboard/backups.html", {
        "policies": BackupPolicy.objects.select_related("service", "template")[:100],
        "artifacts": artifacts,
        "restore_actions": restore_actions,
        "policy_form": BackupPolicyForm(),
        "can_manage_backups": has_permission(
            request.user, "backup.create", "infrastructure_manage"
        ),
        "can_restore_backups": has_permission(
            request.user, "backup.restore", "backup_restore"
        ),
        "can_view_backups": has_permission(
            request.user, "backup.view", "infrastructure_view", "server.view"
        ),
        "nav_sections": _navigation(active="backups"),
    })


@login_required
@require_GET
def alerts(request):
    if not has_permission(
        request.user, "monitoring.view", "infrastructure_view", "server.view"
    ):
        return HttpResponseForbidden("Monitoring view permission required.")
    return render(request, "dashboard/alerts.html", {
        "events": AlertEvent.objects.select_related("rule", "host")[:100],
        "rules": AlertRule.objects.all(),
        "collections": MetricCollection.objects.select_related("host")[:50],
        "rule_form": AlertRuleForm(),
        "can_manage_alerts": has_permission(
            request.user, "monitoring.alert.manage", "infrastructure_manage"
        ),
        "can_acknowledge_alerts": has_permission(
            request.user, "monitoring.alert.acknowledge",
            "monitoring.alert.manage", "infrastructure_manage",
        ),
        "nav_sections": _navigation(active="alerts"),
    })


@login_required
@require_POST
def save_alert_rule(request):
    if not has_permission(
        request.user, "monitoring.alert.manage", "infrastructure_manage"
    ):
        return JsonResponse({"error": "Permission denied."}, status=403)
    form = AlertRuleForm(request.POST)
    if form.is_valid():
        rule = form.save()
        log_audit(request, action="create", module="monitoring.alert_rule", object_id=rule.pk,
                  object_repr=rule.name)
        messages.success(request, "Alert rule saved.")
    else:
        for field, errors in form.errors.items():
            messages.error(request, f"{field}: {', '.join(errors)}")
    return redirect("dashboard:alerts")


@login_required
@require_POST
def save_backup_policy(request):
    if not has_permission(
        request.user, "backup.create", "infrastructure_manage"
    ):
        return JsonResponse({"error": "Permission denied."}, status=403)
    form = BackupPolicyForm(request.POST)
    if form.is_valid():
        policy = form.save(commit=False)
        try:
            policy = save_backup_policy_workflow(policy, request.user)
        except (ValidationError, PermissionDenied) as exc:
            messages.error(request, str(exc))
            return redirect("dashboard:backups")
        messages.success(request, "Backup policy saved.")
    else:
        for field, errors in form.errors.items():
            messages.error(request, f"{field}: {', '.join(errors)}")
    return redirect("dashboard:backups")


@login_required
@require_POST
def run_backup_policy(request, policy_id):
    if not has_permission(
        request.user, "backup.create", "infrastructure_manage"
    ):
        return HttpResponseForbidden("Backup creation permission required.")
    policy = get_object_or_404(
        BackupPolicy.objects.select_related("service__host", "template"),
        pk=policy_id,
    )
    mode = request.POST.get("mode", "dry_run")
    if mode not in {"dry_run", "live"}:
        return JsonResponse({"error": "Unsupported backup mode."}, status=400)
    raw_variables = request.POST.get("variables_json", "{}")
    if len(raw_variables.encode("utf-8")) > 8192:
        messages.error(request, "Backup variables exceed the allowed size.")
        return redirect("dashboard:backups")
    try:
        variables = json.loads(raw_variables or "{}")
        run, artifact = launch_backup_policy(
            policy,
            request.user,
            dry_run=mode != "live",
            confirmed=request.POST.get("confirm") == "yes",
            variables=variables,
            request=request,
        )
    except json.JSONDecodeError:
        messages.error(request, "Backup variables must be valid JSON.")
        return redirect("dashboard:backups")
    except PermissionDenied as exc:
        return HttpResponseForbidden(str(exc))
    except (ValidationError, AutomationValidationError) as exc:
        messages.error(request, str(exc))
        return redirect("dashboard:backups")
    if run.status == AutomationRun.Status.FAILED:
        messages.error(request, "Backup task could not be queued.")
    elif mode == "live":
        messages.success(
            request,
            f"Backup task queued. Artifact record {artifact.pk} is awaiting verification.",
        )
    else:
        messages.success(request, "Backup dry-run was queued.")
    return redirect("dashboard:run_detail", run_id=run.pk)


@login_required
@require_POST
def refresh_backup_artifact(request, artifact_id):
    if not has_permission(
        request.user, "backup.view", "infrastructure_view", "server.view"
    ):
        return JsonResponse({"error": "Backup view permission required."}, status=403)
    artifact = get_object_or_404(
        BackupArtifact.objects.select_related("automation_run__template"),
        pk=artifact_id,
    )
    if artifact.automation_run_id is None:
        return JsonResponse(
            {"status": artifact.status, "message": "No external run is linked."},
            status=409,
        )
    if artifact.automation_run.external_task_id is None:
        return JsonResponse(
            {"status": artifact.status, "message": "The Semaphore task has not started."},
            status=409,
        )
    output_error = refresh_automation_run(artifact.automation_run)
    artifact.refresh_from_db()
    return JsonResponse({
        "status": artifact.status,
        "receipt_error": artifact.receipt_error,
        "output_error": output_error,
    }, status=503 if output_error else 200)


@login_required
@require_POST
def restore_backup_artifact(request, artifact_id):
    if not has_permission(
        request.user, "backup.restore", "backup_restore"
    ):
        return HttpResponseForbidden("Backup restore permission required.")
    artifact = get_object_or_404(
        BackupArtifact.objects.select_related("host", "service"), pk=artifact_id
    )
    try:
        template_id = int(request.POST.get("template_id", ""))
    except (TypeError, ValueError):
        return JsonResponse({"error": "A restore template is required."}, status=400)
    template = get_object_or_404(
        ApprovedTaskTemplate,
        pk=template_id,
        category=ApprovedTaskTemplate.Category.RESTORE,
        enabled=True,
    )
    mode = request.POST.get("mode", "dry_run")
    if mode not in {"dry_run", "live"}:
        return JsonResponse({"error": "Unsupported restore mode."}, status=400)
    raw_variables = request.POST.get("variables_json", "{}")
    if len(raw_variables.encode("utf-8")) > 8192:
        messages.error(request, "Restore variables exceed the allowed size.")
        return redirect("dashboard:backups")
    try:
        variables = json.loads(raw_variables or "{}")
        restore_request = queue_backup_restore(
            artifact,
            template,
            request.user,
            dry_run=mode != "live",
            confirmed=request.POST.get("confirm") == "yes",
            confirm_restore=request.POST.get("confirm_restore", ""),
            variables=variables,
            request=request,
        )
    except json.JSONDecodeError:
        messages.error(request, "Restore variables must be valid JSON.")
        return redirect("dashboard:backups")
    except PermissionDenied as exc:
        return HttpResponseForbidden(str(exc))
    except (ValidationError, AutomationValidationError) as exc:
        messages.error(request, str(exc))
        return redirect("dashboard:backups")
    run = restore_request.automation_run
    if run.status == AutomationRun.Status.FAILED:
        messages.error(request, "Restore task could not be queued.")
    else:
        messages.success(request, "Restore workflow queued through Task Manager.")
    return redirect("dashboard:run_detail", run_id=run.pk)


@login_required
@require_GET
def audit_log(request):
    if not has_permission(request.user, "audit_view", "infrastructure_manage"):
        return JsonResponse({"error": "Permission denied."}, status=403)
    page = Paginator(AuditLog.objects.select_related("user").all(), 50).get_page(request.GET.get("page"))
    return render(request, "dashboard/audit_log.html", {
        "page": page, "nav_sections": _navigation(active="audit"),
    })


@login_required
@require_POST
def acknowledge_alert(request, event_id):
    if not has_permission(
        request.user, "monitoring.alert.acknowledge",
        "monitoring.alert.manage", "infrastructure_manage",
    ):
        return JsonResponse({"error": "Permission denied."}, status=403)
    event = get_object_or_404(AlertEvent, pk=event_id)
    if event.acknowledged_at is None and event.resolved_at is None:
        event.acknowledged_at = timezone.now()
        event.save(update_fields=["acknowledged_at"])
        log_audit(request, action="update", module="alerts", object_id=event.pk,
                  object_repr=f"Acknowledged alert {event.title}")
    return redirect("dashboard:alerts")


@infrastructure_view_required
@require_GET
def traefik(request):
    services = DashboardOverviewService.service_items(
        ManagedService.objects.filter(enabled=True, kind=ManagedService.Kind.TRAEFIK).select_related("host")
    )
    return render(request, "dashboard/service_catalog.html", {
        "title": "Traefik", "subtitle": "Read-only Traefik API inventory and registered services.",
        "services": services, "nav_sections": _navigation(active="traefik"),
        "traefik": TraefikReadOnlyService.inspect(),
    })


@infrastructure_view_required
@require_GET
def overview_api(request):
    return JsonResponse(DashboardOverviewService.build())


@docker_view_required
@require_GET
def container_logs(request, container_id):
    engine = None
    engine_id = request.GET.get("engine")
    if engine_id:
        try:
            engine = DockerEngine.objects.select_related("host").get(pk=int(engine_id))
        except (TypeError, ValueError, DockerEngine.DoesNotExist):
            return JsonResponse({"error": "Docker engine not found."}, status=404)
    result = ContainerDiscoveryService.list_containers(engine)
    if not result["available"]:
        return JsonResponse({"error": "Docker read access is not configured."}, status=503)
    item = next(
        (
            entry for entry in result["containers"]
            if entry["id"] == container_id or entry["name"] == container_id
        ),
        None,
    )
    if item is None:
        return JsonResponse({"error": "Container is not in the current managed Docker listing."}, status=404)
    tail = request.GET.get("tail", "100")
    if not tail.isdigit() or not 1 <= int(tail) <= 200:
        return JsonResponse({"error": "tail must be between 1 and 200."}, status=400)
    try:
        output = read_container_logs(result["engine"], item["id"], int(tail))
    except DockerAdapterError:
        return JsonResponse({"error": "Container logs could not be read."}, status=503)
    logs = _redact(output)
    if request.GET.get("format") == "json":
        return JsonResponse({"container": item["name"], "logs": logs})
    return render(request, "dashboard/container_logs.html", {
        "container": item, "logs": logs, "nav_sections": _navigation(active="containers"),
    })


@login_required
@require_GET
def semaphore_ping(request):
    if not _can_view(request.user):
        return JsonResponse({"status": "forbidden"}, status=403)
    try:
        ok = SemaphoreClient().ping()
    except SemaphoreError as exc:
        messages.error(request, f"Semaphore is unavailable: {exc}")
    else:
        messages.success(request, "Semaphore is connected." if ok else "Could not confirm the Semaphore connection.")
    return redirect("dashboard:index")


@login_required
@require_POST
def run_approved_template(request, template_id):
    if not has_permission(
        request.user, "automation.playbook.execute", "infrastructure_manage"
    ):
        return JsonResponse({"error": "Permission denied."}, status=403)
    template = get_object_or_404(ApprovedTaskTemplate, pk=template_id, enabled=True)
    if template.category == ApprovedTaskTemplate.Category.BACKUP:
        return JsonResponse(
            {"error": "Launch backup templates through an enabled Backup policy."},
            status=400,
        )
    if template.category == ApprovedTaskTemplate.Category.RESTORE:
        if not has_permission(request.user, "backup.restore", "backup_restore"):
            return JsonResponse({"error": "Backup restore permission required."}, status=403)
        return JsonResponse(
            {"error": "Restore templates require a successful source artifact."},
            status=400,
        )
    live = request.POST.get("mode") == "live"
    if live and template.read_only:
        return JsonResponse({"error": "Read-only templates cannot be launched in live mode."}, status=400)
    if live and template.category == ApprovedTaskTemplate.Category.DISCOVERY:
        return JsonResponse({"error": "Discovery templates are limited to dry-run mode."}, status=400)
    raw_variables = request.POST.get("variables_json", "{}")
    if len(raw_variables.encode("utf-8")) > 8192:
        messages.error(request, "Automation variables exceed the allowed size.")
        return redirect(reverse("dashboard:index"))
    try:
        variables = json.loads(raw_variables or "{}")
        run = queue_automation_run(
            template=template,
            actor=request.user,
            dry_run=not live,
            confirmed=request.POST.get("confirm") == "yes",
            confirm_restore=request.POST.get("confirm_restore", ""),
            variables=variables,
            request=request,
        )
    except json.JSONDecodeError:
        messages.error(request, "Automation variables must be valid JSON.")
        return redirect(reverse("dashboard:index"))
    except PermissionDenied as exc:
        return HttpResponseForbidden(str(exc))
    except AutomationValidationError as exc:
        messages.error(request, str(exc))
        return redirect(reverse("dashboard:index"))
    log_audit(
        request, action="create", module="automation", object_id=run.pk,
        object_repr=f"Queued approved template {template.name}",
        new_value={"status": run.status, "dry_run": run.dry_run, "task_id": str(run.task_id or "")},
    )
    if run.status == AutomationRun.Status.FAILED:
        messages.error(request, f"Automation was not queued: {run.summary}")
    else:
        messages.success(request, f"Automation request queued as task {run.task_id}.")
    return redirect(reverse("dashboard:index"))


@login_required
@require_POST
def refresh_run(request, run_id):
    if not _can_view(request.user):
        return JsonResponse({"error": "Permission denied."}, status=403)
    run = get_object_or_404(AutomationRun.objects.select_related("template"), pk=run_id)
    if run.external_task_id is None:
        return JsonResponse({"status": run.status, "summary": run.summary}, status=409)
    output_error = refresh_automation_run(run)
    run.refresh_from_db()
    response = {
        "status": run.status,
        "summary": run.summary,
        "output_error": output_error,
    }
    if output_error:
        response["message"] = output_error
    return JsonResponse(response, status=503 if output_error else 200)


@login_required
@require_GET
def run_detail(request, run_id):
    if not _can_view(request.user):
        return JsonResponse({"error": "Permission denied."}, status=403)
    run = get_object_or_404(AutomationRun.objects.select_related("template", "requested_by"), pk=run_id)
    refresh_error = _reconcile_automation_task(run)
    if run.external_task_id and run.status in {AutomationRun.Status.QUEUED, AutomationRun.Status.RUNNING}:
        refresh_error = refresh_automation_run(run)
        run.refresh_from_db()
    return render(request, "dashboard/run_detail.html", {
        "run": run, "refresh_error": refresh_error,
        "nav_sections": _navigation(active="dashboard"),
    })


def _reconcile_automation_task(run):
    if not run.task_id or run.external_task_id:
        return ""
    task = run.task
    if task.status in {Task.Status.FAILED, Task.Status.CANCELLED, Task.Status.TIMEOUT}:
        run.status = AutomationRun.Status.FAILED
        run.finished_at = task.finished_at or timezone.now()
        run.summary = (
            task.error_message or task.result_summary
            or "The local task ended before it could start a Semaphore execution."
        )[:500]
        run.save(update_fields=["status", "finished_at", "summary"])
        sync_backup_artifact(run, None)
    return ""


def _can_view(user):
    return bool(user.is_authenticated and has_permission(user, "infrastructure_view", "nav_infrastructure", "server.view"))


def _can_manage(user):
    return bool(user.is_authenticated and has_permission(user, "infrastructure_manage"))


def _can_manage_automation(user):
    return bool(
        user.is_authenticated
        and has_permission(user, "automation.playbook.create", "infrastructure_manage")
    )


def _redact(value):
    value = re.sub(r'''(?i)(["']?authorization["']?\s*[=:]\s*["']?)bearer\s+[^\s,"';}]+''', r"\1[redacted]", value)
    value = re.sub(r'''(?i)(["']?(?:password|token|secret|authorization|api[_-]?key)["']?\s*[=:]\s*["']?)[^\s,"';}]+''', r"\1[redacted]", value)
    value = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/-]+=*", "Bearer [redacted]", value)
    value = re.sub(r"(?i)(https?://)[^/@\s]+:[^/@\s]+@", r"\1[redacted]@", value)
    return value


def _navigation(active):
    return [
      {"title": "Operations", "items": [
        {"label": "Dashboard", "icon": "fas fa-gauge-high", "id": "nav-dashboard", "onclick": "window.location.href='/dashboard/'", "active": active == "dashboard"},
        {"label": "Docker containers", "icon": "fab fa-docker", "id": "nav-containers", "onclick": "window.location.href='/dashboard/containers/'", "active": active == "containers"},
        {"label": "Odoo", "icon": "fas fa-cubes", "id": "nav-odoo", "onclick": "window.location.href='/dashboard/services/odoo/'", "active": active == "odoo"},
        {"label": "Django projects", "icon": "fas fa-code", "id": "nav-django", "onclick": "window.location.href='/dashboard/services/django/'", "active": active == "django"},
        {"label": "Databases & Redis", "icon": "fas fa-database", "id": "nav-databases", "onclick": "window.location.href='/dashboard/databases/'", "active": active == "databases"},
        {"label": "Backups", "icon": "fas fa-box-archive", "id": "nav-backups", "onclick": "window.location.href='/dashboard/backups/'", "active": active == "backups"},
        {"label": "Reports", "icon": "fas fa-chart-pie", "id": "nav-reports", "onclick": "window.location.href='/dashboard/reports/'", "active": active == "reports"},
        {"label": "Notifications", "icon": "fas fa-bell", "id": "nav-notifications", "onclick": "window.location.href='/dashboard/notifications/'", "active": active == "notifications"},
        {"label": "Alerts", "icon": "fas fa-bell", "id": "nav-alerts", "onclick": "window.location.href='/dashboard/alerts/'", "active": active == "alerts"},
        {"label": "Traefik", "icon": "fas fa-route", "id": "nav-traefik", "onclick": "window.location.href='/dashboard/traefik/'", "active": active == "traefik"},
      ]},
      {"title": "Settings", "items": [
        {"label": "Hosts & services", "icon": "fas fa-server", "id": "nav-hosts", "onclick": "window.location.href='/dashboard/inventory/'", "active": active == "inventory"},
        {"label": "Global settings", "icon": "fas fa-sliders", "id": "nav-settings", "onclick": "window.location.href='/dashboard/settings/'", "active": active == "settings"},
        {"label": "Task center", "icon": "fas fa-list-check", "id": "nav-tasks", "onclick": "window.location.href='/dashboard/tasks/'", "active": active == "tasks"},
        {"label": "Automation templates", "icon": "fas fa-list-check", "id": "nav-automation-templates", "onclick": "window.location.href='/dashboard/automation/templates/'", "active": active == "automation"},
        {"label": "Audit log", "icon": "fas fa-clipboard-list", "id": "nav-audit", "onclick": "window.location.href='/dashboard/audit/'", "active": active == "audit"},
      ]},
    ]
