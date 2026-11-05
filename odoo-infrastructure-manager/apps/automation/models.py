from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.infrastructure.models import ManagedHost, ManagedService


class ApprovedTaskTemplate(models.Model):
    class Category(models.TextChoices):
        DISCOVERY = "discovery", "Read-only discovery"
        SERVICE = "service", "Service operation"
        BACKUP = "backup", "Backup"
        RESTORE = "restore", "Restore"
        MAINTENANCE = "maintenance", "Maintenance"

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    project_id = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    template_id = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    category = models.CharField(max_length=20, choices=Category.choices)
    enabled = models.BooleanField(default=False)
    read_only = models.BooleanField(default=True)
    requires_confirmation = models.BooleanField(default=True)
    host = models.ForeignKey(ManagedHost, null=True, blank=True, on_delete=models.PROTECT)
    service = models.ForeignKey(ManagedService, null=True, blank=True, on_delete=models.PROTECT)
    variables_schema = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "name"]
        constraints = [models.UniqueConstraint(fields=["project_id", "template_id"], name="uniq_approved_semaphore_template")]

    def __str__(self):
        return f"{self.name} (project {self.project_id}, template {self.template_id})"


class AutomationRun(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        UNKNOWN = "unknown", "Unknown"

    template = models.ForeignKey(ApprovedTaskTemplate, on_delete=models.PROTECT, related_name="runs")
    task = models.ForeignKey(
        "tasks.Task", null=True, blank=True, on_delete=models.SET_NULL, related_name="automation_runs"
    )
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    external_task_id = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    dry_run = models.BooleanField(default=True)
    summary = models.CharField(max_length=500, blank=True)
    output_excerpt = models.TextField(blank=True)
    host_limit = models.CharField(max_length=120, blank=True)
    encrypted_variables = models.TextField(blank=True)
    variable_names = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.template.name} — {self.get_status_display()}"


class AutomationSchedule(models.Model):
    template = models.OneToOneField(
        ApprovedTaskTemplate, on_delete=models.PROTECT, related_name="schedule"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    interval_minutes = models.PositiveSmallIntegerField(
        default=60, validators=[MinValueValidator(15), MaxValueValidator(10080)]
    )
    encrypted_variables = models.TextField(blank=True)
    variable_names = models.JSONField(default=list, blank=True)
    enabled = models.BooleanField(default=False)
    next_run_at = models.DateTimeField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["next_run_at", "template__name"]

    def __str__(self):
        return f"{self.template.name} every {self.interval_minutes} minutes"
