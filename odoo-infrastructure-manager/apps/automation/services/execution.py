import json
import re

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.services.permission_service import has_permission, is_identity_active
from apps.automation.models import ApprovedTaskTemplate, AutomationRun
from apps.security.services.credentials import (
    CredentialEncryptionError,
    decrypt_secret,
    encrypt_secret,
)


_VARIABLE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_SENSITIVE_NAME = re.compile(
    r"(?i)(password|passwd|token|secret|private.?key|authorization|api.?key)"
)
_ALLOWED_TYPES = {"string", "integer", "boolean"}
_HOST_LIMIT = re.compile(r"^[A-Za-z0-9_.-]{1,120}$")
_UNSAFE_LIMITS = {"all", "ungrouped"}
_MAX_VARIABLES = 30
_MAX_VARIABLE_PAYLOAD = 8192


class AutomationValidationError(Exception):
    pass


def validate_variables_schema(schema):
    if not isinstance(schema, dict) or len(schema) > _MAX_VARIABLES:
        raise AutomationValidationError("Variable schema must be an object with at most 30 entries.")
    normalized = {}
    for name, definition in schema.items():
        if (
            not isinstance(name, str)
            or not _VARIABLE_NAME.fullmatch(name)
            or _SENSITIVE_NAME.search(name)
            or not isinstance(definition, dict)
            or set(definition) - {"type", "required", "choices"}
        ):
            raise AutomationValidationError("Variable schema contains an invalid or sensitive field.")
        value_type = definition.get("type")
        if not isinstance(value_type, str) or value_type not in _ALLOWED_TYPES:
            raise AutomationValidationError(f"Variable '{name}' must declare string, integer, or boolean type.")
        required = definition.get("required", False)
        if not isinstance(required, bool):
            raise AutomationValidationError(f"Variable '{name}' has an invalid required flag.")
        choices = definition.get("choices", [])
        if not isinstance(choices, list) or len(choices) > 50:
            raise AutomationValidationError(f"Variable '{name}' choices must be a list of at most 50 values.")
        for choice in choices:
            if not _matches_type(choice, value_type):
                raise AutomationValidationError(f"Variable '{name}' has a choice with the wrong type.")
            if isinstance(choice, str) and len(choice) > 200:
                raise AutomationValidationError(f"Variable '{name}' has an oversized choice.")
        normalized[name] = {
            "type": value_type,
            "required": required,
            "choices": choices,
        }
    if len(json.dumps(normalized, ensure_ascii=True).encode("utf-8")) > _MAX_VARIABLE_PAYLOAD:
        raise AutomationValidationError("Automation variable schema exceeds the allowed size.")
    return normalized


def validate_variable_values(template, values):
    schema = validate_variables_schema(template.variables_schema)
    if not isinstance(values, dict) or len(values) > _MAX_VARIABLES:
        raise AutomationValidationError("Automation variables must be a JSON object with at most 30 entries.")
    if set(values) - set(schema):
        raise AutomationValidationError("The request contains variables not declared by this approved template.")
    normalized = {}
    for name, definition in schema.items():
        if name not in values:
            if definition["required"]:
                raise AutomationValidationError(f"Variable '{name}' is required.")
            continue
        value = values[name]
        if not _matches_type(value, definition["type"]):
            raise AutomationValidationError(f"Variable '{name}' has the wrong type.")
        if isinstance(value, str) and (len(value) > 200 or "\x00" in value):
            raise AutomationValidationError(f"Variable '{name}' is too long or contains invalid characters.")
        if definition["choices"] and value not in definition["choices"]:
            raise AutomationValidationError(f"Variable '{name}' is not an allowed choice.")
        normalized[name] = value
    if len(json.dumps(normalized, ensure_ascii=True).encode("utf-8")) > _MAX_VARIABLE_PAYLOAD:
        raise AutomationValidationError("Automation variables exceed the allowed size.")
    return normalized


def queue_automation_run(*, template, actor, dry_run=True, confirmed=False,
                         confirm_restore="", variables=None, request=None,
                         before_dispatch=None):
    if not is_identity_active(actor):
        raise PermissionDenied("An active account is required to run automation.")
    if not has_permission(actor, "automation.playbook.execute", "infrastructure_manage"):
        raise PermissionDenied("Automation execution permission is required.")
    if not has_permission(actor, "task.view", "tasks_manage"):
        raise PermissionDenied("Task view permission is required to queue automation.")
    if not template.enabled:
        raise AutomationValidationError("Only an approved, enabled template can be run.")
    if not template.host_id or not template.host.enabled:
        raise AutomationValidationError("The approved template needs an enabled managed host.")
    if template.service_id and template.service.host_id != template.host_id:
        raise AutomationValidationError("The selected service does not belong to the approved managed host.")
    limit = template.host.ansible_limit or ""
    if not _HOST_LIMIT.fullmatch(limit) or limit.lower() in _UNSAFE_LIMITS:
        raise AutomationValidationError("The template needs an exact, safe managed-host inventory limit.")
    if not dry_run:
        if template.read_only or template.category == ApprovedTaskTemplate.Category.DISCOVERY:
            raise AutomationValidationError("This approved template is limited to dry-run mode.")
        if not confirmed:
            raise AutomationValidationError("Explicit confirmation is required for a live automation run.")
    if template.category == ApprovedTaskTemplate.Category.RESTORE:
        if not has_permission(actor, "backup.restore", "backup_restore"):
            raise PermissionDenied("Backup restore permission is required.")
        if not dry_run and confirm_restore != "RESTORE":
            raise AutomationValidationError("Type RESTORE to confirm this operation.")
    safe_variables = validate_variable_values(template, variables or {})
    if (
        template.category == ApprovedTaskTemplate.Category.RESTORE
        and not safe_variables.get("backup_artifact_ref")
    ):
        raise AutomationValidationError(
            "Restore runs must reference a registered backup artifact."
        )
    encrypted_variables = ""
    if safe_variables:
        try:
            encrypted_variables = encrypt_secret(
                json.dumps(safe_variables, ensure_ascii=True, separators=(",", ":"))
            )
        except CredentialEncryptionError as exc:
            raise AutomationValidationError(
                "Secure variable storage is not configured for automation."
            ) from exc

    with transaction.atomic():
        run = AutomationRun.objects.create(
            template=template,
            requested_by=actor,
            status=AutomationRun.Status.QUEUED,
            dry_run=dry_run,
            host_limit=limit,
            encrypted_variables=encrypted_variables,
            variable_names=sorted(safe_variables),
            summary="Waiting for task dispatch.",
        )
        if before_dispatch:
            before_dispatch(run)
    try:
        from apps.tasks.services.operation_tasks import queue_infrastructure_operation
        from apps.tasks.services.dispatcher import TaskDispatchUnavailable
        from infrastructure_engine.core.engine import OperationRejected

        task = queue_infrastructure_operation(
            operation="automation.template.execute",
            target_id=template.host_id,
            actor=actor,
            parameters={"run_id": run.pk},
            confirmation=True,
            request=request,
            source={"app": "automation", "model": "AutomationRun", "pk": run.pk},
        )
    except (TaskDispatchUnavailable, OperationRejected) as exc:
        run.status = AutomationRun.Status.FAILED
        run.finished_at = timezone.now()
        run.summary = str(exc)[:500]
        run.save(update_fields=["status", "finished_at", "summary"])
        return run
    except (PermissionDenied, ValidationError):
        if before_dispatch:
            run.status = AutomationRun.Status.FAILED
            run.finished_at = timezone.now()
            run.summary = "Task dispatch failed before the external workflow started."
            run.save(update_fields=["status", "finished_at", "summary"])
        else:
            run.delete()
        raise

    run.task = task
    if task.status == task.Status.FAILED:
        run.status = AutomationRun.Status.FAILED
        run.finished_at = timezone.now()
        run.summary = "Task dispatch failed; see the linked task for details."
        run.save(update_fields=["task", "status", "finished_at", "summary"])
    else:
        run.summary = "Task queued; awaiting the Semaphore execution request."
        run.save(update_fields=["task", "summary"])
    return run


def execute_automation_run(host, run_id, actor):
    try:
        run = AutomationRun.objects.select_related("template", "template__host").get(pk=run_id)
    except AutomationRun.DoesNotExist as exc:
        from infrastructure_engine.core.engine import OperationRejected

        raise OperationRejected("The approved automation run was not found.", status_code=404) from exc
    template = run.template
    if (
        not template.enabled
        or not template.host_id
        or template.host_id != host.pk
        or not template.host.enabled
        or (template.service_id and template.service.host_id != host.pk)
        or template.host.ansible_limit != run.host_limit
        or run.status != AutomationRun.Status.QUEUED
        or (not run.dry_run and (
            template.read_only or template.category == ApprovedTaskTemplate.Category.DISCOVERY
        ))
    ):
        _reject_automation_run(run, "The approved template or its managed-host scope has changed.")
    if (
        template.category == ApprovedTaskTemplate.Category.RESTORE
        and not has_permission(actor, "backup.restore", "backup_restore")
    ):
        _reject_automation_run(run, "Backup restore permission is no longer available.")
    if template.category == ApprovedTaskTemplate.Category.RESTORE:
        from apps.backup.models import BackupArtifact, BackupRestoreRequest

        restore_request = (
            BackupRestoreRequest.objects.select_related("artifact")
            .filter(automation_run=run)
            .first()
        )
        if (
            restore_request is None
            or restore_request.artifact.status != BackupArtifact.Status.SUCCESS
            or restore_request.artifact.host_id != host.pk
            or restore_request.artifact.service_id != template.service_id
        ):
            _reject_automation_run(
                run, "The source backup artifact is no longer eligible for restore."
            )
    try:
        variables_json = decrypt_secret(run.encrypted_variables) if run.encrypted_variables else "{}"
        variables = json.loads(variables_json)
        variables = validate_variable_values(template, variables)
    except (CredentialEncryptionError, json.JSONDecodeError, AutomationValidationError) as exc:
        _reject_automation_run(
            run, "The saved automation variables could not be validated securely."
        )
    if (
        template.category == ApprovedTaskTemplate.Category.RESTORE
        and variables.get("backup_artifact_ref") != restore_request.artifact.artifact_ref
    ):
        _reject_automation_run(
            run, "The restore artifact reference does not match the approved source."
        )
    try:
        from apps.automation.services import SemaphoreClient, SemaphoreError

        response = SemaphoreClient().start_task(
            template.project_id,
            template.template_id,
            dry_run=run.dry_run,
            limit=run.host_limit,
            extra_vars=variables,
        )
        raw_external_id = response.get("id") if isinstance(response, dict) else None
        if isinstance(raw_external_id, bool) or not isinstance(raw_external_id, (int, str)):
            raise SemaphoreError("Semaphore response did not include a valid task identifier.")
        external_id = int(raw_external_id)
        if external_id < 1:
            raise SemaphoreError("Semaphore response did not include a valid task identifier.")
    except (SemaphoreError, KeyError, TypeError, ValueError) as exc:
        run.status = AutomationRun.Status.FAILED
        run.finished_at = timezone.now()
        run.summary = str(exc)[:500]
        run.save(update_fields=["status", "finished_at", "summary"])
        from infrastructure_engine.core.engine import OperationRejected

        raise OperationRejected(run.summary, status_code=503) from exc
    run.external_task_id = external_id
    run.status = AutomationRun.Status.QUEUED
    run.summary = "Semaphore accepted the task; its execution state is not yet confirmed."
    run.save(update_fields=["external_task_id", "status", "summary"])
    return {
        "message": "Semaphore accepted the approved automation task.",
        "external_task_id": external_id,
        "dry_run": run.dry_run,
        "host_limit": run.host_limit,
    }


def load_schedule_variables(schedule):
    if not schedule.encrypted_variables:
        return validate_variable_values(schedule.template, {})
    try:
        raw = decrypt_secret(schedule.encrypted_variables)
        variables = json.loads(raw)
    except (CredentialEncryptionError, json.JSONDecodeError) as exc:
        raise AutomationValidationError(
            "The schedule variables could not be decrypted securely."
        ) from exc
    return validate_variable_values(schedule.template, variables)


def _matches_type(value, value_type):
    if value_type == "string":
        return isinstance(value, str)
    if value_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if value_type == "boolean":
        return isinstance(value, bool)
    return False


def _reject_automation_run(run, message):
    from infrastructure_engine.core.engine import OperationRejected

    run.status = AutomationRun.Status.FAILED
    run.finished_at = timezone.now()
    run.summary = message[:500]
    run.save(update_fields=["status", "finished_at", "summary"])
    raise OperationRejected(run.summary, status_code=409)
