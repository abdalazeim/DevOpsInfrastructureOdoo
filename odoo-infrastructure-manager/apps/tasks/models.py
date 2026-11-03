import uuid

from django.conf import settings
from django.db import models


class Task(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        TIMEOUT = "timeout", "Timeout"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    operation = models.CharField(max_length=120)
    source_app = models.CharField(max_length=80, blank=True)
    source_model = models.CharField(max_length=100, blank=True)
    source_pk = models.CharField(max_length=100, blank=True)
    target_server = models.ForeignKey(
        "infrastructure.ManagedHost", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="tasks",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="infrastructure_tasks",
    )
    priority = models.CharField(max_length=12, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    result_summary = models.CharField(max_length=1000, blank=True)
    error_category = models.CharField(max_length=80, blank=True)
    error_message = models.CharField(max_length=1000, blank=True)
    safe_metadata = models.JSONField(default=dict, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    queued_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    cancel_requested_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="task_status_created_idx"),
            models.Index(fields=["target_server", "status"], name="task_server_status_idx"),
            models.Index(fields=["source_app", "source_model", "source_pk"], name="task_source_idx"),
        ]

    @property
    def is_terminal(self):
        return self.status in {
            self.Status.COMPLETED, self.Status.FAILED,
            self.Status.CANCELLED, self.Status.TIMEOUT,
        }


class TaskLog(models.Model):
    class Stream(models.TextChoices):
        SYSTEM = "system", "System"
        STDOUT = "stdout", "Standard output"
        STDERR = "stderr", "Standard error"

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="logs")
    sequence = models.PositiveIntegerField()
    stream = models.CharField(max_length=10, choices=Stream.choices, default=Stream.SYSTEM)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sequence"]
        constraints = [models.UniqueConstraint(fields=["task", "sequence"], name="uniq_task_log_sequence")]
        indexes = [models.Index(fields=["task", "created_at"], name="task_log_time_idx")]
