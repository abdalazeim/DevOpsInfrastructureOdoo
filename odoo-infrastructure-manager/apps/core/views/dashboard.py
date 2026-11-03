"""Generic dashboard statistics (domain-agnostic).

Business modules can contribute their own stats by registering a callback
via ``register_dashboard_stats_provider``. This keeps Core completely free
of any business domain knowledge.
"""

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.models import AuditLog
from apps.core.utils.decorators import api_login_required
from apps.core.utils.http import api_response

User = get_user_model()


_stats_providers = []


def register_stats_provider(callback):
    """Register a callable that returns a dict of extra stats for the dashboard."""
    _stats_providers.append(callback)


def _system_stats():
    return {
        "total_users": User.objects.count(),
        "active_users": User.objects.filter(is_active=True).count(),
        "total_audit_events": AuditLog.objects.count(),
        "audit_events_today": AuditLog.objects.filter(
            created_at__date=timezone.localdate()
        ).count(),
    }


def _latest_audit():
    return [
        {
            "id": entry.id,
            "action": entry.action,
            "action_label": entry.get_action_display(),
            "module": entry.module,
            "user_name": (
                entry.user.get_full_name() or entry.user.username
                if entry.user_id
                else ""
            ),
            "object_repr": entry.object_repr,
            "ip_address": entry.ip_address or "",
            "created_at": entry.created_at.isoformat(),
        }
        for entry in AuditLog.objects.select_related("user")[:10]
    ]


@api_login_required
def dashboard_stats(request):
    stats = _system_stats()
    stats["latest_audit"] = _latest_audit()
    for provider in _stats_providers:
        try:
            stats.update(provider(request))
        except Exception:
            pass
    return api_response(stats, message="تم تحميل الإحصائيات")
