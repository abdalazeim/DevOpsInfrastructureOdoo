"""Generic audit logging service shared by all modules.

Business modules and views can call :func:`log_audit` to record important
actions without depending on any business domain.
"""

from apps.core.models import AuditLog


def log_audit(
    request=None,
    *,
    action="other",
    module="",
    object_id="",
    object_repr="",
    old_value=None,
    new_value=None,
    user=None,
):
    """Create an AuditLog entry.

    ``request`` (optional) is used to resolve the current user and client IP.
    Alternatively pass ``user`` directly.
    """
    actor = user
    ip = None
    if request is not None:
        if actor is None:
            actor = getattr(request, "user", None)
        ip = _client_ip(request)

    AuditLog.objects.create(
        user=actor if (actor is not None and actor.is_authenticated) else None,
        action=action,
        module=module,
        object_id=str(object_id or ""),
        object_repr=str(object_repr or "")[:255],
        ip_address=ip,
        old_value=old_value,
        new_value=new_value,
    )


def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or None
