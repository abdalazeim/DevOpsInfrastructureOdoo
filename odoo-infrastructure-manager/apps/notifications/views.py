from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.services.publishing import save_preferences


def _preference_rows(user):
    stored = {
        preference.category: preference
        for preference in NotificationPreference.objects.filter(user=user)
    }
    rows = []
    for category, label in Notification.Category.choices:
        preference = stored.get(category)
        in_app = preference.in_app_enabled if preference else True
        email = preference.email_enabled if preference else False
        channel = (
            "both" if in_app and email else
            "in_app" if in_app else
            "email" if email else
            "off"
        )
        rows.append({"category": category, "label": label, "channel": channel})
    return rows


@login_required
@require_GET
def notification_center(request):
    queryset = Notification.objects.filter(user=request.user).select_related(
        "email_delivery"
    )
    paginator = Paginator(queryset, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "dashboard/notifications.html",
        {
            "page": page,
            "unread_count": queryset.filter(read_at__isnull=True).count(),
            "preference_rows": _preference_rows(request.user),
            "email_address_configured": bool(request.user.email),
            "nav_sections": _notification_navigation(),
        },
    )


def _notification_navigation():
    from apps.dashboard.views import _navigation

    return _navigation(active="notifications")


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(
        Notification, pk=notification_id, user=request.user
    )
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])
    return redirect("dashboard:notifications")


@login_required
@require_POST
def mark_all_notifications_read(request):
    Notification.objects.filter(
        user=request.user, read_at__isnull=True
    ).update(read_at=timezone.now())
    return redirect("dashboard:notifications")


@login_required
@require_POST
def update_notification_preferences(request):
    channel_values = {"both", "in_app", "email", "off"}
    expected = {f"channel_{category}" for category, _ in Notification.Category.choices}
    if not expected.issubset(request.POST.keys()):
        messages.error(request, "Choose a delivery preference for every category.")
        return redirect("dashboard:notifications")
    preferences = []
    for category, _ in Notification.Category.choices:
        channel = request.POST.get(f"channel_{category}", "off")
        if channel not in channel_values:
            messages.error(request, "Select a valid notification channel.")
            return redirect("dashboard:notifications")
        preferences.append(
            {
                "category": category,
                "in_app_enabled": channel in {"both", "in_app"},
                "email_enabled": channel in {"both", "email"},
            }
        )
    try:
        save_preferences(request.user, preferences)
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    else:
        messages.success(request, "Notification preferences saved.")
    return redirect("dashboard:notifications")
