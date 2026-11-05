import uuid

from django.db import models


class InfrastructureSnapshot(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Collected"
        PARTIAL = "partial", "Partially collected"
        FAILED = "failed", "Collection failed"

    host = models.OneToOneField(
        "infrastructure.ManagedHost", on_delete=models.CASCADE,
        related_name="latest_snapshot",
    )
    source = models.CharField(max_length=80)
    status = models.CharField(max_length=16, choices=Status.choices)
    data = models.JSONField(default=dict, blank=True)
    availability = models.JSONField(default=dict, blank=True)
    captured_at = models.DateTimeField(auto_now_add=True, db_index=True)
    collection_duration_ms = models.PositiveIntegerField(default=0)
    error_details = models.TextField(blank=True)

    class Meta:
        ordering = ["-captured_at"]
        indexes = [models.Index(fields=["status", "-captured_at"], name="snapshot_status_time_idx")]

    @property
    def is_stale(self):
        from datetime import timedelta

        from django.utils import timezone

        return self.captured_at < timezone.now() - timedelta(minutes=5)


class InfrastructureSyncRecord(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Collected"
        PARTIAL = "partial", "Partially collected"
        FAILED = "failed", "Collection failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    host = models.ForeignKey(
        "infrastructure.ManagedHost",
        on_delete=models.PROTECT,
        related_name="sync_records",
    )
    source = models.CharField(max_length=80)
    status = models.CharField(max_length=16, choices=Status.choices)
    updated_sections = models.JSONField(default=list, blank=True)
    error_details = models.TextField(blank=True)
    collection_duration_ms = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["-completed_at"]
        indexes = [
            models.Index(
                fields=["host", "-completed_at"],
                name="infra_sync_host_time_idx",
            ),
            models.Index(
                fields=["status", "-completed_at"],
                name="infra_sync_status_time_idx",
            ),
        ]
