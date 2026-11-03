"""Security & audit-oriented logging helpers.

Business/domain code can call :func:`log_security_event` to record
authentication, authorization and other security-relevant events without
coupling to a specific logging stream. Events land in ``logs/security.log``
plus the console.
"""

import logging

security_logger = logging.getLogger("apps.security")


def log_security_event(
    event,
    *,
    user=None,
    request=None,
    level=logging.WARNING,
    extra=None,
):
    """Log a security-relevant event.

    ``event`` is a short machine-readable tag (e.g. ``login_failed``,
    ``permission_denied``) and ``extra`` may carry a human-readable message
    plus arbitrary context keys that get appended to the log line.
    """
    parts = [event]
    if user is not None and getattr(user, "is_authenticated", False):
        parts.append(f"user={user.username}@{user.pk}")
    if request is not None:
        ip = request.META.get("HTTP_X_FORWARDED_FOR")
        ip = ip.split(",")[0].strip() if ip else request.META.get("REMOTE_ADDR")
        if ip:
            parts.append(f"ip={ip}")
        parts.append(f"path={request.path}")
    if extra:
        for key, value in extra.items():
            parts.append(f"{key}={value}")
    security_logger.log(level, " | ".join(parts))
