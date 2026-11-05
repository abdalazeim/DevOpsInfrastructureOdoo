"""Versioned REST endpoints for server inventory and discovery history."""

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q

from apps.accounts.services.permission_service import has_permission
from apps.core.utils.decorators import api_login_required, api_permission_required
from apps.core.services.audit_service import log_audit
from apps.core.utils.http import (
    api_error,
    api_response,
    api_response_paginated,
    paginate_queryset,
    parse_json_body,
)
from apps.tasks.services.dispatcher import TaskDispatchUnavailable
from apps.tasks.services.operation_tasks import queue_infrastructure_operation
from infrastructure_engine.core.engine import OperationRejected

from .models import InfrastructureSyncRecord, ManagedHost, ServerGroup, ServerTag
from .serializers import (
    InfrastructureSyncRecordSerializer,
    ManagedHostSerializer,
    ServerGroupSerializer,
    ServerTagSerializer,
)
from .services.server_inventory import save_server, server_inventory_queryset


@api_login_required
def server_list(request):
    if request.method == "GET":
        if not has_permission(request.user, "server.view", "infrastructure_view"):
            return api_error("Server view permission required.", status=403)
        queryset = server_inventory_queryset()
        term = request.GET.get("q", "").strip()
        if term:
            queryset = queryset.filter(
                Q(name__icontains=term)
                | Q(hostname__icontains=term)
                | Q(location__icontains=term)
                | Q(operating_system__icontains=term)
            )
        for field in ("environment", "connection_status"):
            value = request.GET.get(field, "").strip()
            if value:
                queryset = queryset.filter(**{field: value})
        group = request.GET.get("group", "").strip()
        if group:
            queryset = queryset.filter(groups__name__iexact=group)
        tag = request.GET.get("tag", "").strip()
        if tag:
            queryset = queryset.filter(tags__name__iexact=tag)
        page, meta = paginate_queryset(queryset.distinct(), request)
        return api_response_paginated(
            ManagedHostSerializer(page, many=True).data,
            meta,
            message="Servers loaded.",
        )
    if request.method == "POST":
        if not _has_permission(request, "server.create", "infrastructure_manage"):
            return api_error("Server creation permission required.", status=403)
        payload, error = parse_json_body(request)
        if error:
            return error
        serializer = ManagedHostSerializer(data=payload)
        if not serializer.is_valid():
            return api_error("Invalid server data.", status=400, errors=serializer.errors)
        host = save_server(serializer, request=request, action="create")
        return api_response(
            ManagedHostSerializer(host).data,
            message="Server registered.",
            status=201,
        )
    return api_error("Method not allowed.", status=405)


@api_login_required
def server_detail(request, host_id):
    if request.method == "GET":
        if not _has_permission(request, "server.view", "infrastructure_view"):
            return api_error("Server view permission required.", status=403)
        host = _get_host(host_id)
        if host is None:
            return api_error("Server not found.", status=404)
        return api_response(ManagedHostSerializer(host).data, message="Server loaded.")

    if request.method in {"PATCH", "PUT"}:
        if not _has_permission(request, "server.update", "infrastructure_manage"):
            return api_error("Server update permission required.", status=403)
        host = _get_host(host_id)
        if host is None:
            return api_error("Server not found.", status=404)
        payload, error = parse_json_body(request)
        if error:
            return error
        serializer = ManagedHostSerializer(
            host, data=payload, partial=request.method == "PATCH"
        )
        if not serializer.is_valid():
            return api_error("Invalid server data.", status=400, errors=serializer.errors)
        host = save_server(serializer, request=request, action="update")
        return api_response(ManagedHostSerializer(host).data, message="Server updated.")

    return api_error("Method not allowed.", status=405)


@api_login_required
def server_groups(request):
    if request.method == "GET":
        if not _has_permission(request, "server.view", "infrastructure_view"):
            return api_error("Server view permission required.", status=403)
        page, meta = paginate_queryset(ServerGroup.objects.all(), request)
        return api_response_paginated(
            ServerGroupSerializer(page, many=True).data, meta, message="Server groups loaded."
        )
    if request.method == "POST":
        if not _has_permission(request, "infrastructure_manage"):
            return api_error("Infrastructure management permission required.", status=403)
        payload, error = parse_json_body(request)
        if error:
            return error
        serializer = ServerGroupSerializer(data=payload)
        if not serializer.is_valid():
            return api_error("Invalid server group.", status=400, errors=serializer.errors)
        with transaction.atomic():
            group = serializer.save()
            log_audit(
                request, action="create", module="infrastructure.server_group",
                object_id=group.pk, object_repr=group.name,
            )
        return api_response(ServerGroupSerializer(group).data, message="Server group created.", status=201)
    return api_error("Method not allowed.", status=405)


@api_login_required
def server_tags(request):
    if request.method == "GET":
        if not _has_permission(request, "server.view", "infrastructure_view"):
            return api_error("Server view permission required.", status=403)
        page, meta = paginate_queryset(ServerTag.objects.all(), request)
        return api_response_paginated(
            ServerTagSerializer(page, many=True).data, meta, message="Server tags loaded."
        )
    if request.method == "POST":
        if not _has_permission(request, "infrastructure_manage"):
            return api_error("Infrastructure management permission required.", status=403)
        payload, error = parse_json_body(request)
        if error:
            return error
        serializer = ServerTagSerializer(data=payload)
        if not serializer.is_valid():
            return api_error("Invalid server tag.", status=400, errors=serializer.errors)
        with transaction.atomic():
            tag = serializer.save()
            log_audit(
                request, action="create", module="infrastructure.server_tag",
                object_id=tag.pk, object_repr=tag.name,
            )
        return api_response(ServerTagSerializer(tag).data, message="Server tag created.", status=201)
    return api_error("Method not allowed.", status=405)


@api_login_required
@api_permission_required("server.view", "infrastructure_view")
def sync_history(request, host_id):
    if request.method != "GET":
        return api_error("Method not allowed.", status=405)
    host = _get_host(host_id)
    if host is None:
        return api_error("Server not found.", status=404)
    queryset = InfrastructureSyncRecord.objects.filter(host=host)
    page, meta = paginate_queryset(queryset, request)
    return api_response_paginated(
        InfrastructureSyncRecordSerializer(page, many=True).data,
        meta,
        message="Server sync history loaded.",
    )


@api_login_required
def test_connection(request, host_id):
    return _queue_operation(
        request,
        host_id,
        "server.test_connection",
        "server.connect",
        fallback_permissions=("infrastructure_manage",),
    )


@api_login_required
def discover(request, host_id):
    return _queue_operation(
        request,
        host_id,
        "server.discover",
        "server.discover",
        fallback_permissions=("server.view", "infrastructure_view"),
    )


def _queue_operation(request, host_id, operation, permission, *, fallback_permissions=()):
    if request.method != "POST":
        return api_error("Method not allowed.", status=405)
    if not _has_permission(request, permission, *fallback_permissions):
        return api_error("Operation permission required.", status=403)
    try:
        task = queue_infrastructure_operation(
            operation=operation,
            target_id=host_id,
            actor=request.user,
            parameters={},
            request=request,
        )
    except TaskDispatchUnavailable as exc:
        return api_error(str(exc), status=503)
    except PermissionDenied as exc:
        return api_error(str(exc), status=403)
    except OperationRejected as exc:
        return api_error(str(exc), status=exc.status_code)
    return api_response(
        {"task_id": str(task.pk), "status": task.status, "operation": task.operation},
        message="Server operation submitted.",
        status=202,
    )


def _has_permission(request, *permissions):
    return has_permission(request.user, *permissions)


def _get_host(host_id):
    try:
        return server_inventory_queryset().get(pk=host_id)
    except ManagedHost.DoesNotExist:
        return None
