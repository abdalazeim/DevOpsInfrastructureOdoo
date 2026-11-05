from django.conf import settings
from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.accounts.services.permission_service import has_permission
from apps.core.services.audit_service import log_audit
from apps.core.utils.decorators import api_login_required
from apps.core.utils.http import (
    api_error,
    api_response,
    api_response_paginated,
    paginate_queryset,
    parse_json_body,
)
from apps.infrastructure.models import ManagedHost
from apps.monitoring.models import AlertEvent, AlertRule, MetricCollection, ResourceSample
from apps.monitoring.serializers import (
    AlertEventSerializer,
    AlertRuleSerializer,
    MetricCollectionSerializer,
    ResourceSampleSerializer,
)


def _allowed(user, *permissions):
    return has_permission(user, *permissions)


def _has_monitoring_access(user):
    return _allowed(user, "monitoring.view", "infrastructure_view", "server.view")


def _has_rule_management(user):
    return _allowed(user, "monitoring.alert.manage", "infrastructure_manage")


def _target_provider(host):
    if host.is_local:
        return (
            "prometheus_or_local"
            if host.prometheus_instance and settings.PROMETHEUS_URL
            else "local"
        )
    if host.prometheus_instance:
        return "prometheus" if settings.PROMETHEUS_URL else "prometheus_not_configured"
    return "not_configured"


@api_login_required
def targets(request):
    if request.method != "GET":
        return api_error("Method not allowed.", status=405)
    if not _has_monitoring_access(request.user):
        return api_error("Monitoring view permission required.", status=403)

    latest = MetricCollection.objects.filter(host_id=OuterRef("pk")).order_by("-captured_at")
    queryset = ManagedHost.objects.filter(enabled=True).annotate(
        last_collection_status=Subquery(latest.values("status")[:1]),
        last_collection_source=Subquery(latest.values("source")[:1]),
        last_collection_error=Subquery(latest.values("error_message")[:1]),
        last_collection_at=Subquery(latest.values("captured_at")[:1]),
    )
    page, meta = paginate_queryset(queryset, request)
    items = [
        {
            "id": host.pk,
            "name": host.name,
            "hostname": host.hostname,
            "environment": host.environment,
            "provider": _target_provider(host),
            "last_collection": (
                {
                    "status": host.last_collection_status,
                    "source": host.last_collection_source,
                    "error_message": host.last_collection_error,
                    "captured_at": host.last_collection_at,
                }
                if host.last_collection_at
                else None
            ),
        }
        for host in page.object_list
    ]
    return api_response_paginated(items, meta, message="Monitoring targets loaded.")


@api_login_required
def samples(request):
    if request.method != "GET":
        return api_error("Method not allowed.", status=405)
    if not _has_monitoring_access(request.user):
        return api_error("Monitoring view permission required.", status=403)

    queryset = ResourceSample.objects.select_related("host").all()
    host_id = request.GET.get("host")
    if host_id:
        try:
            host_id = int(host_id)
        except (TypeError, ValueError):
            return api_error("The host parameter must be a positive integer.", status=400)
        if host_id < 1:
            return api_error("The host parameter must be a positive integer.", status=400)
        queryset = queryset.filter(host_id=host_id)
    since = request.GET.get("since")
    if since:
        parsed_since = parse_datetime(since)
        if parsed_since is None:
            return api_error("The since parameter must be an ISO-8601 datetime.", status=400)
        if timezone.is_naive(parsed_since):
            parsed_since = timezone.make_aware(parsed_since, timezone.get_current_timezone())
        queryset = queryset.filter(captured_at__gte=parsed_since)

    page, meta = paginate_queryset(queryset, request)
    return api_response_paginated(
        ResourceSampleSerializer(page.object_list, many=True).data,
        meta,
        message="Metric samples loaded.",
    )


@api_login_required
def collections(request):
    if request.method != "GET":
        return api_error("Method not allowed.", status=405)
    if not _has_monitoring_access(request.user):
        return api_error("Monitoring view permission required.", status=403)
    queryset = MetricCollection.objects.select_related("host", "sample")
    status_filter = request.GET.get("status", "").strip()
    if status_filter:
        if status_filter not in MetricCollection.Status.values:
            return api_error("Unsupported collection status.", status=400)
        queryset = queryset.filter(status=status_filter)
    host_id = request.GET.get("host")
    if host_id:
        try:
            host_id = int(host_id)
        except (TypeError, ValueError):
            return api_error("The host parameter must be a positive integer.", status=400)
        if host_id < 1:
            return api_error("The host parameter must be a positive integer.", status=400)
        queryset = queryset.filter(host_id=host_id)
    page, meta = paginate_queryset(queryset, request)
    return api_response_paginated(
        MetricCollectionSerializer(page.object_list, many=True).data,
        meta,
        message="Metric collection history loaded.",
    )


@api_login_required
def rules(request):
    if request.method == "GET":
        if not _has_monitoring_access(request.user):
            return api_error("Monitoring view permission required.", status=403)
        page, meta = paginate_queryset(AlertRule.objects.all(), request)
        return api_response_paginated(
            AlertRuleSerializer(page.object_list, many=True).data,
            meta,
            message="Alert rules loaded.",
        )
    if request.method == "POST":
        if not _has_rule_management(request.user):
            return api_error("Alert rule management permission required.", status=403)
        payload, error = parse_json_body(request)
        if error:
            return error
        serializer = AlertRuleSerializer(data=payload)
        if not serializer.is_valid():
            return api_error("Invalid alert rule.", status=400, errors=serializer.errors)
        with transaction.atomic():
            rule = serializer.save()
            log_audit(
                request, action="create", module="monitoring.alert_rule",
                object_id=rule.pk, object_repr=rule.name,
            )
        return api_response(
            AlertRuleSerializer(rule).data, message="Alert rule created.", status=201
        )
    return api_error("Method not allowed.", status=405)


@api_login_required
def rule_detail(request, rule_id):
    if request.method not in {"GET", "PATCH", "PUT"}:
        return api_error("Method not allowed.", status=405)
    if request.method == "GET":
        if not _has_monitoring_access(request.user):
            return api_error("Monitoring view permission required.", status=403)
    elif not _has_rule_management(request.user):
        return api_error("Alert rule management permission required.", status=403)
    try:
        rule = AlertRule.objects.get(pk=rule_id)
    except AlertRule.DoesNotExist:
        return api_error("Alert rule not found.", status=404)
    if request.method == "GET":
        return api_response(AlertRuleSerializer(rule).data, message="Alert rule loaded.")

    payload, error = parse_json_body(request)
    if error:
        return error
    serializer = AlertRuleSerializer(
        rule, data=payload, partial=request.method == "PATCH"
    )
    if not serializer.is_valid():
        return api_error("Invalid alert rule.", status=400, errors=serializer.errors)
    with transaction.atomic():
        rule = serializer.save()
        log_audit(
            request, action="update", module="monitoring.alert_rule",
            object_id=rule.pk, object_repr=rule.name,
        )
    return api_response(AlertRuleSerializer(rule).data, message="Alert rule updated.")


@api_login_required
def alerts(request):
    if request.method != "GET":
        return api_error("Method not allowed.", status=405)
    if not _has_monitoring_access(request.user):
        return api_error("Monitoring view permission required.", status=403)
    queryset = AlertEvent.objects.select_related("host", "rule")
    state = request.GET.get("state", "all").strip()
    if state == "open":
        queryset = queryset.filter(resolved_at__isnull=True, acknowledged_at__isnull=True)
    elif state == "acknowledged":
        queryset = queryset.filter(resolved_at__isnull=True, acknowledged_at__isnull=False)
    elif state == "resolved":
        queryset = queryset.filter(resolved_at__isnull=False)
    elif state != "all":
        return api_error("Unsupported alert state.", status=400)
    host_id = request.GET.get("host")
    if host_id:
        try:
            host_id = int(host_id)
        except (TypeError, ValueError):
            return api_error("The host parameter must be a positive integer.", status=400)
        if host_id < 1:
            return api_error("The host parameter must be a positive integer.", status=400)
        queryset = queryset.filter(host_id=host_id)
    page, meta = paginate_queryset(queryset, request)
    return api_response_paginated(
        AlertEventSerializer(page.object_list, many=True).data,
        meta,
        message="Alert events loaded.",
    )


@api_login_required
def acknowledge_alert(request, event_id):
    if request.method != "POST":
        return api_error("Method not allowed.", status=405)
    if not _allowed(
        request.user, "monitoring.alert.acknowledge",
        "monitoring.alert.manage", "infrastructure_manage",
    ):
        return api_error("Alert acknowledgement permission required.", status=403)
    with transaction.atomic():
        try:
            event = AlertEvent.objects.select_for_update().get(pk=event_id)
        except AlertEvent.DoesNotExist:
            return api_error("Alert event not found.", status=404)
        if event.resolved_at:
            return api_error("Resolved alerts cannot be acknowledged.", status=409)
        if event.acknowledged_at is None:
            event.acknowledged_at = timezone.now()
            event.save(update_fields=["acknowledged_at"])
            log_audit(
                request, action="update", module="monitoring.alert",
                object_id=event.pk, object_repr=f"Acknowledged alert {event.title}",
            )
    return api_response(
        AlertEventSerializer(event).data, message="Alert acknowledged."
    )
