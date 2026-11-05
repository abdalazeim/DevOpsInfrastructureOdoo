from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from apps.accounts.services.permission_service import has_permission, is_identity_active
from apps.notifications.models import Notification, NotificationDelivery, NotificationPreference


_CATEGORY_PERMISSIONS = {
    Notification.Category.ALERT: ("monitoring.view", "infrastructure_view", "server.view"),
    Notification.Category.BACKUP: ("backup.view", "infrastructure_view", "server.view"),
    Notification.Category.AUTOMATION: (
        "automation.playbook.view",
        "automation.playbook.execute",
        "infrastructure_manage",
    ),
    Notification.Category.TASK: ("task.view", "tasks_manage"),
    Notification.Category.SECURITY: (
        "security.credentials.manage",
        "settings.view",
        "settings_manage",
    ),
}


@dataclass(frozen=True)
class NotificationPublishResult:
    created: int = 0
    email_queued: int = 0
    email_failed: int = 0


def _validate_text(value, label, maximum, *, required=False):
    if (
        not isinstance(value, str)
        or len(value) > maximum
        or (required and not value.strip())
        or "\x00" in value
    ):
        raise ValidationError(f"{label} is invalid.")
    return value.strip() if required else value


@transaction.atomic
def publish_notification(
    *,
    category,
    title,
    message="",
    source_app="",
    source_model="",
    source_pk="",
    dedupe_key=None,
):
    if category not in Notification.Category.values:
        raise ValidationError("Unsupported notification category.")
    title = _validate_text(title, "Notification title", 200, required=True)
    message = _validate_text(message, "Notification message", 2000)
    source_app = _validate_text(source_app, "Notification source app", 80)
    source_model = _validate_text(source_model, "Notification source model", 100)
    source_pk = _validate_text(source_pk, "Notification source id", 100)
    if dedupe_key is not None:
        dedupe_key = _validate_text(
            dedupe_key, "Notification deduplication key", 200, required=True
        )

    permissions = _CATEGORY_PERMISSIONS[category]
    users = get_user_model().objects.filter(
        is_active=True, is_active_user=True
    ).order_by("pk")
    created_count = email_count = email_failures = 0
    now = timezone.now()
    for user in users.iterator():
        if not is_identity_active(user) or not has_permission(user, *permissions):
            continue
        preference = NotificationPreference.objects.filter(
            user=user, category=category
        ).first()
        in_app_enabled = preference.in_app_enabled if preference else True
        email_enabled = preference.email_enabled if preference else False
        if not in_app_enabled and not email_enabled:
            continue

        defaults = {
            "title": title,
            "message": message,
            "source_app": source_app,
            "source_model": source_model,
            "source_pk": source_pk,
        }
        if dedupe_key is None:
            notification = Notification.objects.create(
                user=user, category=category, **defaults
            )
            created = True
        else:
            notification, created = Notification.objects.get_or_create(
                user=user,
                category=category,
                dedupe_key=dedupe_key,
                defaults=defaults,
            )

        if not created:
            continue
        created_count += 1
        if not email_enabled:
            continue
        if not user.email:
            NotificationDelivery.objects.create(
                notification=notification,
                status=NotificationDelivery.Status.FAILED,
                next_attempt_at=now,
                last_error="Recipient email address is missing.",
            )
            email_failures += 1
            continue
        NotificationDelivery.objects.create(
            notification=notification,
            status=NotificationDelivery.Status.PENDING,
            next_attempt_at=now,
        )
        email_count += 1

    return NotificationPublishResult(
        created=created_count,
        email_queued=email_count,
        email_failed=email_failures,
    )


@transaction.atomic
def save_preferences(user, preferences):
    if not isinstance(preferences, list):
        raise ValidationError("Notification preferences must be a list.")
    seen = set()
    for item in preferences:
        if not isinstance(item, dict):
            raise ValidationError("Each notification preference must be an object.")
        if set(item) - {"category", "in_app_enabled", "email_enabled"}:
            raise ValidationError("Notification preference contains unsupported fields.")
        category = item.get("category")
        if category not in Notification.Category.values or category in seen:
            raise ValidationError("Notification preference category is invalid or duplicated.")
        seen.add(category)
        values = {
            key: value
            for key, value in item.items()
            if key in {"in_app_enabled", "email_enabled"}
        }
        if not values or any(not isinstance(value, bool) for value in values.values()):
            raise ValidationError("Notification channel preferences must be booleans.")
        current = NotificationPreference.objects.filter(
            user=user, category=category
        ).first()
        resolved_email = values.get(
            "email_enabled", current.email_enabled if current else False
        )
        if resolved_email:
            if not user.email:
                raise ValidationError(
                    "Add an email address to your account before enabling email notifications."
                )
            try:
                validate_email(user.email)
            except ValidationError as exc:
                raise ValidationError(
                    "Your account email address is invalid."
                ) from exc
        NotificationPreference.objects.update_or_create(
            user=user, category=category, defaults=values
        )
        if "email_enabled" in values and not values["email_enabled"]:
            pending_ids = list(
                NotificationDelivery.objects.filter(
                    notification__user=user,
                    notification__category=category,
                    status=NotificationDelivery.Status.PENDING,
                ).values_list("pk", flat=True)
            )
            NotificationDelivery.objects.filter(pk__in=pending_ids).update(
                status=NotificationDelivery.Status.SUPPRESSED,
                last_error="Email delivery disabled by the recipient.",
                updated_at=timezone.now(),
            )
            if pending_ids:
                from apps.notifications.services.delivery import (
                    _update_source_notification_status,
                )

                for delivery_id in pending_ids:
                    _update_source_notification_status(delivery_id)
    return list(
        NotificationPreference.objects.filter(user=user).order_by("category")
    )
