"""Audit log listing API (domain-agnostic).

Exposes the system audit trail with search / filter / pagination so the
reports page can render a generic "سجل التدقيق" view without any business
domain knowledge.
"""

from django.db.models import Q

from apps.core.constants import PermissionCode
from apps.core.models import AuditLog
from apps.core.utils.decorators import api_login_required, api_permission_required
from apps.core.utils.http import api_response_paginated, paginate_queryset


def _to_dict(entry):
    return {
        "id": entry.id,
        "action": entry.action,
        "action_label": entry.get_action_display(),
        "module": entry.module,
        "user_id": entry.user_id,
        "user_name": (
            entry.user.get_full_name() or entry.user.username
            if entry.user_id
            else ""
        ),
        "object_id": entry.object_id,
        "object_repr": entry.object_repr,
        "ip_address": entry.ip_address or "",
        "created_at": entry.created_at.isoformat(),
    }


@api_login_required
@api_permission_required(PermissionCode.AUDIT_VIEW)
def list_audit_logs(request):
    qs = AuditLog.objects.select_related("user").all()

    search = (request.GET.get("search") or "").strip()
    if search:
        qs = qs.filter(
            Q(object_repr__icontains=search)
            | Q(module__icontains=search)
            | Q(user__username__icontains=search)
            | Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
        )

    action = (request.GET.get("action") or "").strip()
    if action:
        qs = qs.filter(action=action)

    user_id = request.GET.get("user_id")
    if user_id:
        qs = qs.filter(user_id=user_id)

    date_from = request.GET.get("date_from")
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)

    date_to = request.GET.get("date_to")
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    page_obj, meta = paginate_queryset(qs, request, page_size=25)
    data = [_to_dict(e) for e in page_obj.object_list]
    return api_response_paginated(data, meta)
