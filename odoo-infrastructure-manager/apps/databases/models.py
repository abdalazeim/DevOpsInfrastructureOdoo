from django.db import models

from apps.infrastructure.models import ManagedHost


class DatabaseInstance(models.Model):
    host = models.ForeignKey(ManagedHost, on_delete=models.PROTECT, related_name="databases")
    name = models.CharField(max_length=120)
    engine = models.CharField(max_length=40, default="postgresql")
    version = models.CharField(max_length=40, blank=True)
    service_name = models.CharField(max_length=120, blank=True, help_text="Registered service/container identifier; no credentials.")
    port = models.PositiveIntegerField(null=True, blank=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["host__name", "name"]

    def __str__(self):
        return f"{self.name} ({self.engine} {self.version})"
