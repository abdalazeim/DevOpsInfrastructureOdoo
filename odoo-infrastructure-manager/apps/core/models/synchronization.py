"""Reusable persistence for idempotent offline synchronization."""

import uuid

from django.conf import settings
from django.db import models


class SyncOperation(models.Model):
    """Durable outcome for one client-generated operation ID."""

    APPLIED = "applied"
    REJECTED = "rejected"
    CONFLICT = "conflict"
    PROCESSING = "processing"
    STATUS_CHOICES = [
        (APPLIED, "Applied"),
        (REJECTED, "Rejected"),
        (CONFLICT, "Conflict"),
        (PROCESSING, "Processing"),
    ]

    operation_id = models.UUIDField(default=uuid.uuid4, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sync_operations",
    )
    kind = models.CharField(max_length=100)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    result = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "core_sync_operation"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "-created_at"], name="sync_user_created_idx"),
            models.Index(fields=["kind", "-created_at"], name="sync_kind_created_idx"),
        ]

    def __str__(self):
        return f"{self.operation_id} {self.kind} {self.status}"


class SyncTombstone(models.Model):
    """Deletion record retained after a hard delete so offline clients can catch up."""

    model_label = models.CharField(max_length=100)
    object_pk = models.CharField(max_length=64)
    scope_key = models.CharField(max_length=100, blank=True, default="")
    deleted_at = models.DateTimeField(auto_now_add=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sync_tombstones",
    )

    class Meta:
        db_table = "core_sync_tombstone"
        ordering = ("-deleted_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["model_label", "object_pk", "scope_key"],
                name="uniq_sync_tombstone_object",
            ),
        ]
        indexes = [
            models.Index(
                fields=["model_label", "scope_key", "-deleted_at"],
                name="sync_model_deleted_idx",
            ),
        ]


class SyncConflict(models.Model):
    """Evidence for an update rejected because its server copy changed meanwhile."""

    OPEN = "open"
    RESOLVED = "resolved"
    STATUS_CHOICES = [(OPEN, "Open"), (RESOLVED, "Resolved")]

    operation_id = models.UUIDField(unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sync_conflicts",
    )
    kind = models.CharField(max_length=100)
    model_label = models.CharField(max_length=100)
    object_pk = models.CharField(max_length=64)
    base_updated_at = models.DateTimeField(null=True, blank=True)
    server_updated_at = models.DateTimeField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    message = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=OPEN)
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_sync_conflicts",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution = models.TextField(blank=True, default="")

    class Meta:
        db_table = "core_sync_conflict"
        ordering = ("-detected_at",)
        indexes = [
            models.Index(fields=["status", "-detected_at"], name="sync_conf_status_idx"),
            models.Index(fields=["model_label", "object_pk"], name="sync_conf_object_idx"),
        ]
