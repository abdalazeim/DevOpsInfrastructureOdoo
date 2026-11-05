import logging
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.accounts.services.permission_service import is_identity_active
from apps.notifications.models import NotificationDelivery

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
CLAIM_LEASE = timedelta(minutes=15)
MAX_BATCH_SIZE = 500


@dataclass(frozen=True)
class DeliveryBatchResult:
    sent: int = 0
    retried: int = 0
    failed: int = 0
    suppressed: int = 0


def _claim_delivery(now):
    with transaction.atomic():
        delivery = (
            NotificationDelivery.objects.select_for_update()
            .filter(
                status__in=[
                    NotificationDelivery.Status.PENDING,
                    NotificationDelivery.Status.SENDING,
                ],
                next_attempt_at__lte=now,
                attempt_count__lt=MAX_ATTEMPTS,
            )
            .select_related("notification__user")
            .order_by("next_attempt_at", "pk")
            .first()
        )
        if delivery is None:
            return None
        delivery.status = NotificationDelivery.Status.SENDING
        delivery.attempt_count += 1
        delivery.last_attempt_at = now
        delivery.next_attempt_at = now + CLAIM_LEASE
        delivery.last_error = ""
        delivery.save(
            update_fields=[
                "status",
                "attempt_count",
                "last_attempt_at",
                "next_attempt_at",
                "last_error",
                "updated_at",
            ]
        )
        return delivery.pk


def _update_source_notification_status(delivery_id):
    delivery = NotificationDelivery.objects.select_related("notification").get(
        pk=delivery_id
    )
    notification = delivery.notification
    if (
        notification.source_app != "monitoring"
        or notification.source_model != "AlertEvent"
        or not notification.source_pk.isdigit()
    ):
        return
    deliveries = NotificationDelivery.objects.filter(
        notification__source_app="monitoring",
        notification__source_model="AlertEvent",
        notification__source_pk=notification.source_pk,
    )
    statuses = set(deliveries.values_list("status", flat=True))
    from apps.monitoring.models import AlertEvent

    try:
        event = AlertEvent.objects.get(pk=int(notification.source_pk))
    except AlertEvent.DoesNotExist:
        return
    if statuses & {
        NotificationDelivery.Status.PENDING,
        NotificationDelivery.Status.SENDING,
    }:
        event.notification_status = AlertEvent.NotificationStatus.PENDING
        event.notification_error = ""
    elif NotificationDelivery.Status.FAILED in statuses:
        event.notification_status = AlertEvent.NotificationStatus.FAILED
        event.notification_error = "Email delivery failed for one or more recipients."
    elif NotificationDelivery.Status.SENT in statuses:
        event.notification_status = AlertEvent.NotificationStatus.SENT
        event.notification_error = ""
    else:
        event.notification_status = AlertEvent.NotificationStatus.NOT_CONFIGURED
        event.notification_error = ""
    event.last_notification_attempt_at = deliveries.exclude(
        last_attempt_at__isnull=True
    ).order_by("-last_attempt_at").values_list("last_attempt_at", flat=True).first()
    event.save(
        update_fields=[
            "notification_status",
            "notification_error",
            "last_notification_attempt_at",
        ]
    )


def dispatch_pending_notifications(*, batch_size=100, now=None):
    if not 1 <= batch_size <= MAX_BATCH_SIZE:
        raise ValueError(f"batch_size must be between 1 and {MAX_BATCH_SIZE}.")
    now = now or timezone.now()
    expired_ids = list(
        NotificationDelivery.objects.filter(
            status=NotificationDelivery.Status.SENDING,
            attempt_count__gte=MAX_ATTEMPTS,
            next_attempt_at__lte=now,
        ).order_by("next_attempt_at", "pk").values_list("pk", flat=True)[:batch_size]
    )
    if expired_ids:
        NotificationDelivery.objects.filter(pk__in=expired_ids).update(
            status=NotificationDelivery.Status.FAILED,
            last_error="Delivery claim expired after the final attempt.",
            updated_at=timezone.now(),
        )
    sent = retried = suppressed = 0
    failed = len(expired_ids)
    for delivery_id in expired_ids:
        _update_source_notification_status(delivery_id)
    for _ in range(batch_size - len(expired_ids)):
        delivery_id = _claim_delivery(now)
        if delivery_id is None:
            break
        delivery = NotificationDelivery.objects.select_related(
            "notification__user"
        ).get(pk=delivery_id)
        preference_enabled = delivery.notification.user.notification_preferences.filter(
            category=delivery.notification.category,
            email_enabled=True,
        ).exists()
        if (
            not is_identity_active(delivery.notification.user)
            or not preference_enabled
        ):
            NotificationDelivery.objects.filter(pk=delivery_id).update(
                status=NotificationDelivery.Status.SUPPRESSED,
                last_error="Email delivery is no longer enabled for the recipient.",
                updated_at=timezone.now(),
            )
            _update_source_notification_status(delivery_id)
            suppressed += 1
            continue
        recipient = delivery.notification.user.email
        error = ""
        try:
            if not recipient:
                raise ValueError("Recipient email address is missing.")
            if not settings.DEFAULT_FROM_EMAIL:
                raise ValueError("Email sender is not configured.")
            sent_count = send_mail(
                delivery.notification.title,
                delivery.notification.message,
                settings.DEFAULT_FROM_EMAIL,
                [recipient],
                fail_silently=False,
            )
            if sent_count != 1:
                raise RuntimeError("Email backend did not confirm delivery.")
        except Exception as exc:
            logger.error(
                "Notification email delivery %s failed (%s)",
                delivery_id,
                type(exc).__name__,
            )
            error = type(exc).__name__[:200]

        completed_at = timezone.now()
        with transaction.atomic():
            delivery = NotificationDelivery.objects.select_for_update().get(
                pk=delivery_id
            )
            if error:
                delivery.last_error = error
                if delivery.attempt_count >= MAX_ATTEMPTS:
                    delivery.status = NotificationDelivery.Status.FAILED
                    delivery.next_attempt_at = completed_at
                    failed += 1
                else:
                    delay_seconds = min(
                        60 * (2 ** (delivery.attempt_count - 1)), 3600
                    )
                    delivery.status = NotificationDelivery.Status.PENDING
                    delivery.next_attempt_at = completed_at + timedelta(
                        seconds=delay_seconds
                    )
                    retried += 1
            else:
                delivery.status = NotificationDelivery.Status.SENT
                delivery.sent_at = completed_at
                delivery.next_attempt_at = completed_at
                delivery.last_error = ""
                sent += 1
            delivery.save(
                update_fields=[
                    "status",
                    "sent_at",
                    "next_attempt_at",
                    "last_error",
                    "updated_at",
                ]
            )
        _update_source_notification_status(delivery_id)

    return DeliveryBatchResult(
        sent=sent, retried=retried, failed=failed, suppressed=suppressed
    )
