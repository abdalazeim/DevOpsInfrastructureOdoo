from django.db import models

from apps.infrastructure.models import ManagedHost


class DjangoProject(models.Model):
    class RunMethod(models.TextChoices):
        DOCKER = "docker", "Docker"
        SYSTEMD = "systemd", "systemd"
        UNKNOWN = "unknown", "Not configured"

    host = models.ForeignKey(ManagedHost, on_delete=models.PROTECT, related_name="django_projects")
    name = models.CharField(max_length=120)
    project_path = models.CharField(max_length=500, blank=True)
    run_method = models.CharField(max_length=20, choices=RunMethod.choices, default=RunMethod.UNKNOWN)
    container_names = models.JSONField(default=list, blank=True)
    domain = models.CharField(max_length=253, blank=True)
    port = models.PositiveIntegerField(null=True, blank=True)
    health_url = models.URLField(blank=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["host__name", "name"]

    def __str__(self):
        return f"{self.name} — {self.host.name}"
