from django.db import models

from apps.infrastructure.models import ManagedHost


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


class AlertRule(models.Model):
    class Metric(models.TextChoices):
        CPU = "cpu_percent", "CPU usage (%)"
        MEMORY = "memory_percent", "Memory usage (%)"
        DISK = "disk_percent", "Root disk usage (%)"

    name = models.CharField(max_length=120, unique=True)
    metric = models.CharField(max_length=40, choices=Metric.choices)
    threshold = models.FloatField()
    cooldown_minutes = models.PositiveIntegerField(default=30)
    enabled = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class AlertEvent(models.Model):
    rule = models.ForeignKey(AlertRule, null=True, blank=True, on_delete=models.SET_NULL)
    host = models.ForeignKey(ManagedHost, null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
