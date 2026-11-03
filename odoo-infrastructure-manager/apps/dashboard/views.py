import re
import shutil
import subprocess
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.core.paginator import Paginator
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.utils import timezone

from apps.automation.models import ApprovedTaskTemplate, AutomationRun
from apps.automation.services import SemaphoreClient, SemaphoreError
from apps.backup.models import BackupArtifact, BackupPolicy
from apps.core.services.audit_service import log_audit
from apps.core.models import AuditLog
from apps.accounts.services.permission_service import has_permission
from apps.databases.models import DatabaseInstance
from apps.django_projects.models import DjangoProject
from apps.infrastructure.models import ManagedHost, ManagedService
from apps.security.models import Credential
from apps.security.services.credentials import CredentialEncryptionError, is_credential_encryption_ready
from infrastructure_engine.core.engine import InfrastructureEngine, OperationRejected
from apps.monitoring.models import AlertEvent, AlertRule

from .forms import (AlertRuleForm, ApprovedTaskTemplateForm, BackupPolicyForm, CredentialCreateForm, GlobalSettingsForm,
                    ManagedHostForm, ManagedServiceForm)
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


@infrastructure_view_required
@require_GET
def index(request):
    overview = DashboardOverviewService.build()
    templates = ApprovedTaskTemplate.objects.filter(enabled=True).select_related("host", "service")
    runs = AutomationRun.objects.select_related("template", "requested_by")[:8]
    recent_alerts = AlertEvent.objects.select_related("rule", "host")[:6]
    return render(request, "dashboard/index.html", {
        "overview": overview,
        "approved_templates": templates,
        "recent_runs": runs,
        "recent_alerts": recent_alerts,
        "can_manage_infrastructure": _can_manage(request.user),
        "nav_sections": _navigation(active="dashboard"),
    })


@infrastructure_view_required
@require_GET
def containers(request):
    result = ContainerDiscoveryService.list_containers()
    return render(request, "dashboard/containers.html", {
        "discovery": result,
        "containers": result["containers"],
        "nav_sections": _navigation(active="containers"),
    })


@infrastructure_view_required
@require_GET
def inventory(request):
    hosts = list(ManagedHost.objects.prefetch_related("groups").all())
    services = list(ManagedService.objects.select_related("host").all())
    for host in hosts:
        host.edit_form = ManagedHostForm(instance=host, prefix=f"h{host.pk}")
    for service in services:
        service.edit_form = ManagedServiceForm(instance=service, prefix=f"s{service.pk}")
    return render(request, "dashboard/inventory.html", {
        "hosts": hosts,
        "services": services,
        "host_form": ManagedHostForm(),
        "service_form": ManagedServiceForm(),
        "credential_form": CredentialCreateForm() if has_permission(request.user, "security.credentials.manage") else None,
        "credentials": Credential.objects.only("id", "name", "kind", "username", "is_active").order_by("name")
            if has_permission(request.user, "security.credentials.manage") else [],
        "credential_encryption_ready": is_credential_encryption_ready(),
        "can_manage_infrastructure": _can_manage(request.user),
        "can_create_servers": has_permission(request.user, "server.create", "infrastructure_manage"),
        "can_update_servers": has_permission(request.user, "server.update", "infrastructure_manage"),
        "can_test_server_connection": has_permission(request.user, "server.connect", "infrastructure_manage"),
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
        "nav_sections": _navigation(active="settings"),
    })


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
        "templates": ApprovedTaskTemplate.objects.select_related("host", "service"),
        "template_form": ApprovedTaskTemplateForm(),
        "can_manage_infrastructure": _can_manage(request.user),
        "nav_sections": _navigation(active="automation"),
    })


@login_required
@require_POST
def create_automation_template(request):
    if not _can_manage(request.user):
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
    if not _can_manage(request.user):
        return JsonResponse({"error": "Permission denied."}, status=403)
    template = get_object_or_404(ApprovedTaskTemplate, pk=template_id)
    enabling = request.POST.get("enabled") == "yes"
    if enabling and template.category != ApprovedTaskTemplate.Category.DISCOVERY:
        limit = template.host.ansible_limit if template.host_id else ""
        if not template.host_id or not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", limit) or limit.lower() in {"all", "*", "ungrouped"}:
            messages.error(request, "This template needs a host and a specific inventory limit before approval.")
            return redirect("dashboard:automation_templates")
    if enabling and template.category == ApprovedTaskTemplate.Category.DISCOVERY:
        template.read_only = True
    template.enabled = enabling
    template.save(update_fields=["enabled", "read_only"])
    log_audit(request, action="approve" if enabling else "update", module="automation.template",
              object_id=template.pk, object_repr=template.name, new_value={"enabled": enabling})
    messages.success(request, "Template approved." if enabling else "Template disabled.")
    return redirect("dashboard:automation_templates")


@infrastructure_view_required
@require_GET
def docker_resources(request, resource_type):
    if resource_type not in {"images", "networks", "volumes", "compose"}:
        return JsonResponse({"error": "Unsupported Docker resource type."}, status=404)
    result = ContainerDiscoveryService.list_resources(resource_type)
    return render(request, "dashboard/docker_resources.html", {
        "resource_type": resource_type, "discovery": result, "items": result["items"],
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


@infrastructure_view_required
@require_GET
def backups(request):
    return render(request, "dashboard/backups.html", {
        "policies": BackupPolicy.objects.select_related("service")[:100],
        "artifacts": BackupArtifact.objects.select_related("host", "service", "policy", "created_by")[:100],
        "templates": ApprovedTaskTemplate.objects.filter(enabled=True, category=ApprovedTaskTemplate.Category.BACKUP),
        "restore_templates": ApprovedTaskTemplate.objects.filter(enabled=True, category=ApprovedTaskTemplate.Category.RESTORE),
        "policy_form": BackupPolicyForm(),
        "can_manage_infrastructure": _can_manage(request.user),
        "nav_sections": _navigation(active="backups"),
    })


@infrastructure_view_required
@require_GET
def alerts(request):
    return render(request, "dashboard/alerts.html", {
        "events": AlertEvent.objects.select_related("rule", "host")[:100],
        "rules": AlertRule.objects.all(),
        "rule_form": AlertRuleForm(),
        "can_manage_infrastructure": _can_manage(request.user),
        "nav_sections": _navigation(active="alerts"),
    })


@login_required
@require_POST
def save_alert_rule(request):
    if not _can_manage(request.user):
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
    if not _can_manage(request.user):
        return JsonResponse({"error": "Permission denied."}, status=403)
    form = BackupPolicyForm(request.POST)
    if form.is_valid():
        policy = form.save()
        log_audit(request, action="create", module="backup.policy", object_id=policy.pk,
                  object_repr=policy.name)
        messages.success(request, "Backup policy saved.")
    else:
        for field, errors in form.errors.items():
            messages.error(request, f"{field}: {', '.join(errors)}")
    return redirect("dashboard:backups")


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
    if not _can_manage(request.user):
        return JsonResponse({"error": "Permission denied."}, status=403)
    from django.utils import timezone
    event = get_object_or_404(AlertEvent, pk=event_id)
    if event.acknowledged_at is None:
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


@login_required
@require_GET
def container_logs(request, container_name):
    if not _can_view(request.user):
        return JsonResponse({"error": "Permission denied."}, status=403)
    if not ContainerDiscoveryService.list_containers()["available"]:
        return JsonResponse({"error": "Docker read access is not configured."}, status=503)
    result = ContainerDiscoveryService.list_containers()
    item = next((entry for entry in result["containers"] if entry["name"] == container_name), None)
    if item is None:
        return JsonResponse({"error": "Container is not in the current managed Docker listing."}, status=404)
    tail = request.GET.get("tail", "100")
    if not tail.isdigit() or not 1 <= int(tail) <= 200:
        return JsonResponse({"error": "tail must be between 1 and 200."}, status=400)
    docker = shutil.which("docker")
    try:
        output = subprocess.run([docker, "logs", "--tail", str(int(tail)), item["id"]],
                                capture_output=True, text=True, timeout=8, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return JsonResponse({"error": "Container logs could not be read."}, status=503)
    logs = _redact(output.stdout + output.stderr)[:40000]
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
    if not _can_manage(request.user):
        return JsonResponse({"error": "Permission denied."}, status=403)
    template = get_object_or_404(ApprovedTaskTemplate, pk=template_id, enabled=True)
    if template.category == ApprovedTaskTemplate.Category.RESTORE and not has_permission(request.user, "backup_restore"):
        return JsonResponse({"error": "Backup restore permission required."}, status=403)
    live = request.POST.get("mode") == "live"
    confirmed = request.POST.get("confirm") == "yes"
    if live and template.read_only:
        return JsonResponse({"error": "Read-only templates cannot be launched in live mode."}, status=400)
    if live and template.category == ApprovedTaskTemplate.Category.DISCOVERY:
        return JsonResponse({"error": "Discovery templates are limited to dry-run mode."}, status=400)
    if live and template.category == ApprovedTaskTemplate.Category.RESTORE and request.POST.get("confirm_restore") != "RESTORE":
        return JsonResponse({"error": "Type RESTORE to confirm this operation."}, status=400)
    if live and not confirmed:
        messages.error(request, "Confirm the operation before starting it.")
        return redirect(reverse("dashboard:index"))
    if template.category != ApprovedTaskTemplate.Category.DISCOVERY:
        if template.host_id is None or not template.host.ansible_limit:
            messages.error(request, "Link the template to a host and set an explicit inventory limit before running it.")
            return redirect(reverse("dashboard:index"))
    limit = template.host.ansible_limit if template.host_id else ""
    if limit and (not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", limit) or limit.lower() in {"all", "*", "ungrouped"}):
        messages.error(request, "The inventory limit is not valid.")
        return redirect(reverse("dashboard:index"))
    run = AutomationRun.objects.create(template=template, requested_by=request.user, dry_run=not live)
    try:
        response = SemaphoreClient().start_task(template.project_id, template.template_id,
                                               dry_run=not live, limit=limit)
        if not isinstance(response, dict) or not response.get("id"):
            raise SemaphoreError("Semaphore response did not include a task identifier.")
        run.external_task_id = int(response["id"])
        run.status = AutomationRun.Status.QUEUED
        run.summary = "Task queued in Semaphore."
        run.save(update_fields=["external_task_id", "status", "summary"])
        log_audit(request, action="create", module="automation", object_id=run.pk,
                  object_repr=f"Queued approved template {template.name}",
                  new_value={"external_task_id": run.external_task_id, "dry_run": run.dry_run})
        messages.success(request, f"Task sent to Semaphore. Task ID: {run.external_task_id}")
    except (SemaphoreError, ValueError, TypeError) as exc:
        run.status = AutomationRun.Status.FAILED
        run.summary = str(exc)[:500]
        run.save(update_fields=["status", "summary"])
        log_audit(request, action="other", module="automation", object_id=run.pk,
                  object_repr=f"Failed to queue approved template {template.name}",
                  new_value={"status": run.status})
        messages.error(request, f"Could not start the task: {run.summary}")
    return redirect(reverse("dashboard:index"))


@login_required
@require_POST
def refresh_run(request, run_id):
    if not _can_view(request.user):
        return JsonResponse({"error": "Permission denied."}, status=403)
    run = get_object_or_404(AutomationRun.objects.select_related("template"), pk=run_id)
    if run.external_task_id is None:
        return JsonResponse({"status": run.status, "summary": run.summary}, status=409)
    try:
        task = SemaphoreClient().get_task(run.template.project_id, run.external_task_id)
    except SemaphoreError as exc:
        return JsonResponse({"status": run.status, "message": str(exc)}, status=503)
    if isinstance(task, dict):
        status = str(task.get("status", "")).lower()
        mapping = {"running": AutomationRun.Status.RUNNING, "waiting": AutomationRun.Status.QUEUED,
                   "success": AutomationRun.Status.SUCCESS, "failed": AutomationRun.Status.FAILED,
                   "stopped": AutomationRun.Status.FAILED}
        if status in mapping:
            run.status = mapping[status]
            if run.status in {AutomationRun.Status.SUCCESS, AutomationRun.Status.FAILED}:
                from django.utils import timezone
                run.finished_at = timezone.now()
            run.summary = _redact(str(task.get("error", "") or task.get("status", "")))[:500]
            updates = ["status", "summary"]
            if run.finished_at:
                updates.append("finished_at")
        else:
            updates = []
        try:
            output = SemaphoreClient().task_output(run.template.project_id, run.external_task_id)
            run.output_excerpt = _redact(_format_output(output))[:30000]
            updates.append("output_excerpt")
        except SemaphoreError:
            pass
        if updates:
            run.save(update_fields=updates)
    return JsonResponse({"status": run.status, "summary": run.summary})


@login_required
@require_GET
def run_detail(request, run_id):
    if not _can_view(request.user):
        return JsonResponse({"error": "Permission denied."}, status=403)
    run = get_object_or_404(AutomationRun.objects.select_related("template", "requested_by"), pk=run_id)
    if run.external_task_id and run.status in {AutomationRun.Status.QUEUED, AutomationRun.Status.RUNNING}:
        try:
            task = SemaphoreClient().get_task(run.template.project_id, run.external_task_id)
            if isinstance(task, dict):
                status = str(task.get("status", "")).lower()
                mapping = {"running": AutomationRun.Status.RUNNING, "waiting": AutomationRun.Status.QUEUED,
                           "success": AutomationRun.Status.SUCCESS, "failed": AutomationRun.Status.FAILED,
                           "stopped": AutomationRun.Status.FAILED}
                if status in mapping:
                    run.status = mapping[status]
                    if run.status in {AutomationRun.Status.SUCCESS, AutomationRun.Status.FAILED}:
                        from django.utils import timezone
                        run.finished_at = timezone.now()
                output = SemaphoreClient().task_output(run.template.project_id, run.external_task_id)
                run.output_excerpt = _redact(_format_output(output))[:30000]
                run.save(update_fields=["status", "finished_at", "output_excerpt"])
        except SemaphoreError:
            pass
    return render(request, "dashboard/run_detail.html", {
        "run": run, "nav_sections": _navigation(active="dashboard"),
    })


def _can_view(user):
    return bool(user.is_authenticated and has_permission(user, "infrastructure_view", "nav_infrastructure", "server.view"))


def _can_manage(user):
    return bool(user.is_authenticated and has_permission(user, "infrastructure_manage"))


def _redact(value):
    value = re.sub(r'''(?i)(["']?authorization["']?\s*[=:]\s*["']?)bearer\s+[^\s,"';}]+''', r"\1[redacted]", value)
    value = re.sub(r'''(?i)(["']?(?:password|token|secret|authorization|api[_-]?key)["']?\s*[=:]\s*["']?)[^\s,"';}]+''', r"\1[redacted]", value)
    value = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/-]+=*", "Bearer [redacted]", value)
    value = re.sub(r"(?i)(https?://)[^/@\s]+:[^/@\s]+@", r"\1[redacted]@", value)
    return value


def _format_output(output):
    if isinstance(output, (dict, list)):
        import json
        return json.dumps(output, ensure_ascii=False, indent=2)
    return str(output or "")


def _navigation(active):
    return [
      {"title": "Operations", "items": [
        {"label": "Dashboard", "icon": "fas fa-gauge-high", "id": "nav-dashboard", "onclick": "window.location.href='/dashboard/'", "active": active == "dashboard"},
        {"label": "Docker containers", "icon": "fab fa-docker", "id": "nav-containers", "onclick": "window.location.href='/dashboard/containers/'", "active": active == "containers"},
        {"label": "Odoo", "icon": "fas fa-cubes", "id": "nav-odoo", "onclick": "window.location.href='/dashboard/services/odoo/'", "active": active == "odoo"},
        {"label": "Django projects", "icon": "fas fa-code", "id": "nav-django", "onclick": "window.location.href='/dashboard/services/django/'", "active": active == "django"},
        {"label": "Databases & Redis", "icon": "fas fa-database", "id": "nav-databases", "onclick": "window.location.href='/dashboard/databases/'", "active": active == "databases"},
        {"label": "Backups", "icon": "fas fa-box-archive", "id": "nav-backups", "onclick": "window.location.href='/dashboard/backups/'", "active": active == "backups"},
        {"label": "Alerts", "icon": "fas fa-bell", "id": "nav-alerts", "onclick": "window.location.href='/dashboard/alerts/'", "active": active == "alerts"},
        {"label": "Traefik", "icon": "fas fa-route", "id": "nav-traefik", "onclick": "window.location.href='/dashboard/traefik/'", "active": active == "traefik"},
      ]},
      {"title": "Settings", "items": [
        {"label": "Hosts & services", "icon": "fas fa-server", "id": "nav-hosts", "onclick": "window.location.href='/dashboard/inventory/'", "active": active == "inventory"},
        {"label": "Global settings", "icon": "fas fa-sliders", "id": "nav-settings", "onclick": "window.location.href='/dashboard/settings/'", "active": active == "settings"},
        {"label": "Automation templates", "icon": "fas fa-list-check", "id": "nav-automation-templates", "onclick": "window.location.href='/dashboard/automation/templates/'", "active": active == "automation"},
        {"label": "Audit log", "icon": "fas fa-clipboard-list", "id": "nav-audit", "onclick": "window.location.href='/dashboard/audit/'", "active": active == "audit"},
      ]},
    ]
