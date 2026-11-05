import math

from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.infrastructure.models import ManagedHost


def validate_finite_number(value):
    if not math.isfinite(value):
        raise ValidationError("Enter a finite number.")


class ResourceSample(models.Model):
    host = models.ForeignKey(ManagedHost, on_delete=models.CASCADE, related_name="resource_samples")
    source = models.CharField(max_length=80)
    cpu_percent = models.FloatField(null=True, blank=True)
    memory_percent = models.FloatField(null=True, blank=True)
    memory_total_bytes = models.BigIntegerField(null=True, blank=True)
    memory_used_bytes = models.BigIntegerField(null=True, blank=True)
    disk_percent = models.FloatField(null=True, blank=True)
    network_rx_bytes_per_second = models.FloatField(null=True, blank=True)
    network_tx_bytes_per_second = models.FloatField(null=True, blank=True)
    captured_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-captured_at"]
        indexes = [models.Index(fields=["host", "-captured_at"])]


class MetricCollection(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Succeeded"
        FAILED = "failed", "Failed"

    host = models.ForeignKey(
        ManagedHost, on_delete=models.PROTECT, related_name="metric_collections"
    )
    sample = models.OneToOneField(
        ResourceSample, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="collection",
    )
    source = models.CharField(max_length=80)
    status = models.CharField(max_length=10, choices=Status.choices)
    error_message = models.CharField(max_length=500, blank=True)
    captured_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-captured_at"]
        indexes = [models.Index(fields=["host", "-captured_at"])]


class AlertRule(models.Model):
    class Metric(models.TextChoices):
        CPU = "cpu_percent", "CPU usage (%)"
        MEMORY = "memory_percent", "Memory usage (%)"
        DISK = "disk_percent", "Root disk usage (%)"

    name = models.CharField(max_length=120, unique=True)
    metric = models.CharField(max_length=40, choices=Metric.choices)
    threshold = models.FloatField(
        validators=[
            validate_finite_number,
            MinValueValidator(0),
            MaxValueValidator(100),
        ]
    )
    cooldown_minutes = models.PositiveIntegerField(
        default=30, validators=[MinValueValidator(1), MaxValueValidator(1440)]
    )
    enabled = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class AlertEvent(models.Model):
    class NotificationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        NOT_CONFIGURED = "not_configured", "Not configured"

    rule = models.ForeignKey(AlertRule, null=True, blank=True, on_delete=models.SET_NULL)
    host = models.ForeignKey(ManagedHost, null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(default=timezone.now)
    occurrences = models.PositiveIntegerField(default=1)
    notification_status = models.CharField(
        max_length=20, choices=NotificationStatus.choices,
        default=NotificationStatus.NOT_CONFIGURED,
    )
    last_notification_attempt_at = models.DateTimeField(null=True, blank=True)
    last_notification_queued_at = models.DateTimeField(null=True, blank=True)
    notification_error = models.CharField(max_length=250, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["resolved_at", "acknowledged_at", "created_at"]),
            models.Index(fields=["rule", "host", "resolved_at"]),
        ]
