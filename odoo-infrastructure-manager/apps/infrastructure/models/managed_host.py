from django.db import models


class ManagedHost(models.Model):
    class Environment(models.TextChoices):
        PRODUCTION = "production", "Production"
        STAGING = "staging", "Staging"
        DEVELOPMENT = "development", "Development"

    name = models.CharField(max_length=120, unique=True)
    hostname = models.CharField(max_length=253, help_text="DNS name or address; no credentials are stored here.")
    environment = models.CharField(max_length=20, choices=Environment.choices, default=Environment.PRODUCTION)
    description = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Managed host"
        verbose_name_plural = "Managed hosts"

    def __str__(self):
        return f"{self.name} ({self.hostname})"
