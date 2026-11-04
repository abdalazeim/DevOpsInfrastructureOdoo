from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .managed_host import ManagedHost


class ManagedService(models.Model):
    class Kind(models.TextChoices):
        ODOO = "odoo", "Odoo"
        DJANGO = "django", "Django project"
        POSTGRESQL = "postgresql", "PostgreSQL"
        REDIS = "redis", "Redis"
        TRAEFIK = "traefik", "Traefik"
        OTHER = "other", "Other"

    host = models.ForeignKey(ManagedHost, on_delete=models.PROTECT, related_name="services")
    key = models.SlugField(max_length=80)
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    version = models.CharField(max_length=40, blank=True)
    container_names = models.JSONField(default=list, blank=True)
    compose_project = models.CharField(max_length=120, blank=True)
    http_url = models.URLField(blank=True, help_text="Optional health URL. Only administrators can configure it.")
    port = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(65535)])
    enabled = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["host__name", "name"]
        constraints = [models.UniqueConstraint(fields=["host", "key"], name="uniq_managed_service_host_key")]

    def __str__(self):
        return f"{self.name} — {self.host.name}"
