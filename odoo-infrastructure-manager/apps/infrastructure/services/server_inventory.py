"""Application services for canonical server inventory records."""

from django.db import transaction

from apps.core.services.audit_service import log_audit
from apps.infrastructure.models import ManagedHost


_AUDIT_FIELDS = (
    "name",
    "hostname",
    "server_type",
    "connection_type",
    "ssh_port",
    "environment",
    "location",
    "enabled",
    "is_local",
)


def save_server(serializer, *, request, action):
    old_value = _audit_value(serializer.instance) if serializer.instance else None
    with transaction.atomic():
        host = serializer.save()
        log_audit(
            request,
            action=action,
            module="infrastructure.host",
            object_id=host.pk,
            object_repr=str(host),
            old_value=old_value,
            new_value=_audit_value(host),
        )
    return host


def server_inventory_queryset():
    return (
        ManagedHost.objects.select_related("credential", "latest_snapshot")
        .prefetch_related("groups", "tags")
        .order_by("name")
    )


def _audit_value(host):
    value = {field: getattr(host, field) for field in _AUDIT_FIELDS}
    value["groups"] = list(host.groups.values_list("name", flat=True))
    value["tags"] = list(host.tags.values_list("name", flat=True))
    value["credential_configured"] = bool(host.credential_id)
    return value
