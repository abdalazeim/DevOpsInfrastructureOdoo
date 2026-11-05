from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.core.utils.decorators import api_login_required
from apps.core.utils.http import (
    api_error,
    api_response,
    api_response_paginated,
    paginate_queryset,
    parse_json_body,
)
from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.serializers import (
    NotificationPreferenceInputSerializer,
    NotificationSerializer,
)
from apps.notifications.services.publishing import save_preferences


def _preference_data(user):
    stored = {
        preference.category: preference
        for preference in NotificationPreference.objects.filter(user=user)
    }
    return [
        {
            "category": category,
            "in_app_enabled": (
                stored[category].in_app_enabled if category in stored else True
            ),
            "email_enabled": (
                stored[category].email_enabled if category in stored else False
            ),
        }
        for category, _ in Notification.Category.choices
    ]


@api_login_required
def notifications(request):
    if request.method != "GET":
        return api_error("Method not allowed.", status=405)
    unread_parameter = request.GET.get("unread")
    if unread_parameter not in {None, "true", "false"}:
        return api_error("The unread parameter must be true or false.", status=400)
    queryset = Notification.objects.filter(user=request.user).select_related(
        "email_delivery"
    )
    if unread_parameter == "true":
        queryset = queryset.filter(read_at__isnull=True)
    elif unread_parameter == "false":
        queryset = queryset.filter(read_at__isnull=False)
    unread_count = Notification.objects.filter(
        user=request.user, read_at__isnull=True
    ).count()
    page, meta = paginate_queryset(queryset, request)
    meta["unread_count"] = unread_count
    return api_response_paginated(
        NotificationSerializer(page.object_list, many=True).data,
        meta,
        message="Notifications loaded.",
    )


@api_login_required
def mark_notification_read(request, notification_id):
    if request.method != "POST":
        return api_error("Method not allowed.", status=405)
    try:
        notification = Notification.objects.get(
            pk=notification_id, user=request.user
        )
    except Notification.DoesNotExist:
        return api_error("Notification not found.", status=404)
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])
    return api_response(
        NotificationSerializer(notification).data,
        message="Notification marked as read.",
    )


@api_login_required
def mark_all_notifications_read(request):
    if request.method != "POST":
        return api_error("Method not allowed.", status=405)
    updated = Notification.objects.filter(
        user=request.user, read_at__isnull=True
    ).update(read_at=timezone.now())
    return api_response({"updated": updated}, message="Unread notifications marked as read.")


@api_login_required
def preferences(request):
    if request.method == "GET":
        return api_response(
            {
                "items": _preference_data(request.user),
                "email_address_configured": bool(request.user.email),
            },
            message="Notification preferences loaded.",
        )
    if request.method != "PATCH":
        return api_error("Method not allowed.", status=405)
    payload, error = parse_json_body(request)
    if error:
        return error
    if not isinstance(payload, dict) or set(payload) != {"preferences"}:
        return api_error(
            "Preferences must contain only a preferences list.", status=400
        )
    serializer = NotificationPreferenceInputSerializer(
        data=payload["preferences"], many=True
    )
    if not serializer.is_valid():
        return api_error(
            "Invalid notification preferences.",
            status=400,
            errors=serializer.errors,
        )
    try:
        save_preferences(request.user, serializer.validated_data)
    except ValidationError as exc:
        return api_error("Invalid notification preferences.", status=400, errors=exc.messages)
    return api_response(
        {
            "items": _preference_data(request.user),
            "updated": len(serializer.validated_data),
        },
        message="Notification preferences saved.",
    )
