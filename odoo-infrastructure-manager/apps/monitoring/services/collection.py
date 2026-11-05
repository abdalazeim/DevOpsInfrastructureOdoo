import logging
import math
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.dashboard.services.metrics_service import MetricsService
from apps.infrastructure.models import ManagedHost
from apps.monitoring.models import AlertEvent, AlertRule, MetricCollection, ResourceSample
from apps.notifications.models import Notification
from apps.notifications.services import publish_notification

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CollectionResult:
    status: str
    source: str
    reason: str = ""
    alerts_created: int = 0


def _metric_values(sample):
    return {
        AlertRule.Metric.CPU: sample.cpu_percent,
        AlertRule.Metric.MEMORY: sample.memory_percent,
        AlertRule.Metric.DISK: sample.disk_percent,
    }


def _bounded_percentage(value):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) and 0 <= numeric <= 100 else None


def _nonnegative_number(value):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) and numeric >= 0 else None


def _evaluate_rules(host, sample, captured_at):
    values = _metric_values(sample)
    alerts_created = 0
    for rule in AlertRule.objects.select_for_update().all():
        event = AlertEvent.objects.select_for_update().filter(
            rule=rule, host=host, resolved_at__isnull=True
        ).first()
        value = values.get(rule.metric)
        if not rule.enabled:
            if event:
                event.resolved_at = captured_at
                event.save(update_fields=["resolved_at"])
            continue
        if value is None:
            continue
        if value < rule.threshold:
            if event:
                event.resolved_at = captured_at
                event.save(update_fields=["resolved_at"])
            continue

        message = (
            f"{rule.get_metric_display()} is {value:.1f}% "
            f"(threshold {rule.threshold:.1f}%)."
        )
        if event is None:
            event = AlertEvent.objects.create(
                rule=rule,
                host=host,
                title=f"{rule.get_metric_display()} threshold exceeded",
                message=message,
                last_seen_at=captured_at,
            )
            alerts_created += 1
        else:
            event.message = message
            event.last_seen_at = captured_at
            event.occurrences += 1
            event.save(update_fields=["message", "last_seen_at", "occurrences"])

        notification_due = (
            event.last_notification_queued_at is None
            or captured_at - event.last_notification_queued_at
            >= timedelta(minutes=rule.cooldown_minutes)
        )
        if notification_due:
            result = publish_notification(
                category=Notification.Category.ALERT,
                title=event.title,
                message=f"{host}: {event.message}" if host else event.message,
                source_app="monitoring",
                source_model="AlertEvent",
                source_pk=str(event.pk),
                dedupe_key=f"monitoring.alert.{event.pk}.{event.occurrences}",
            )
            event.last_notification_queued_at = captured_at
            event.notification_status = (
                AlertEvent.NotificationStatus.PENDING
                if result.email_queued
                else AlertEvent.NotificationStatus.FAILED
                if result.email_failed
                else AlertEvent.NotificationStatus.NOT_CONFIGURED
            )
            event.notification_error = (
                "Email recipient configuration is incomplete."
                if result.email_failed
                else ""
            )
            event.save(
                update_fields=[
                    "last_notification_queued_at",
                    "notification_status",
                    "notification_error",
                ]
            )
    return alerts_created


def collect_host(host, interval_seconds):
    with transaction.atomic():
        locked_host = ManagedHost.objects.select_for_update().get(pk=host.pk)
        now = timezone.now()
        previous = MetricCollection.objects.filter(host=locked_host).first()
        if previous and (now - previous.captured_at).total_seconds() < interval_seconds:
            return CollectionResult(
                status="skipped", source=previous.source,
                reason="Collection interval has not elapsed.",
            )

        try:
            data = MetricsService.collect(locked_host)
        except Exception as exc:
            logger.error(
                "Metric provider raised an error for host %s (%s)",
                locked_host.pk,
                type(exc).__name__,
            )
            data = {
                "available": False,
                "source": "unknown",
                "reason": f"Metrics provider failed ({type(exc).__name__}).",
            }

        source = str(data.get("source") or "unknown")[:80]
        if not data.get("available"):
            reason = str(data.get("reason") or "Metrics provider returned no data.")[:500]
            MetricCollection.objects.create(
                host=locked_host, source=source,
                status=MetricCollection.Status.FAILED,
                error_message=reason, captured_at=timezone.now(),
            )
            return CollectionResult(status="failed", source=source, reason=reason)

        memory = data.get("memory") or {}
        disk = data.get("disk") or {}
        sample = ResourceSample.objects.create(
            host=locked_host,
            source=source,
            cpu_percent=_bounded_percentage(data.get("cpu_percent")),
            memory_percent=_bounded_percentage(memory.get("percent")),
            memory_total_bytes=_nonnegative_number(memory.get("total_bytes")),
            memory_used_bytes=_nonnegative_number(memory.get("used_bytes")),
            disk_percent=_bounded_percentage(disk.get("percent")),
            network_rx_bytes_per_second=_nonnegative_number(
                data.get("network_rx_bytes_per_second")
            ),
            network_tx_bytes_per_second=_nonnegative_number(
                data.get("network_tx_bytes_per_second")
            ),
        )
        MetricCollection.objects.create(
            host=locked_host,
            sample=sample,
            source=source,
            status=MetricCollection.Status.SUCCESS,
            captured_at=sample.captured_at,
        )
        alerts_created = _evaluate_rules(
            locked_host, sample, sample.captured_at
        )

    return CollectionResult(
        status="success", source=source, alerts_created=alerts_created,
    )


def prune_metrics(retention_days):
    cutoff = timezone.now() - timedelta(days=retention_days)
    deleted_samples, _ = ResourceSample.objects.filter(captured_at__lt=cutoff).delete()
    deleted_collections, _ = MetricCollection.objects.filter(captured_at__lt=cutoff).delete()
    return deleted_samples, deleted_collections
