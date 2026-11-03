from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ServerGroup(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ManagedHost(models.Model):
    class Environment(models.TextChoices):
        PRODUCTION = "production", "Production"
        STAGING = "staging", "Staging"
        DEVELOPMENT = "development", "Development"

    class ServerType(models.TextChoices):
        LOCAL = "local", "Local"
        REMOTE = "remote", "Remote"
        VIRTUAL = "virtual", "Virtual"
        PHYSICAL = "physical", "Physical"
        CLOUD = "cloud", "Cloud"

    class ConnectionType(models.TextChoices):
        LOCAL = "local", "Local process"
        SSH = "ssh", "SSH"
        ANSIBLE = "ansible", "Ansible inventory"

    class ConnectionStatus(models.TextChoices):
        UNKNOWN = "unknown", "Not checked"
        ONLINE = "online", "Online"
        OFFLINE = "offline", "Offline"
        UNREACHABLE = "unreachable", "Unreachable"

    name = models.CharField(max_length=120, unique=True)
    hostname = models.CharField(max_length=253, help_text="DNS name or address; no credentials are stored here.")
    server_type = models.CharField(max_length=20, choices=ServerType.choices, default=ServerType.REMOTE)
    connection_type = models.CharField(max_length=20, choices=ConnectionType.choices, default=ConnectionType.SSH)
    ssh_port = models.PositiveIntegerField(default=22, validators=[MinValueValidator(1), MaxValueValidator(65535)])
    credential_reference = models.CharField(max_length=160, blank=True, help_text="Reference to a protected credential record; never enter a secret here.")
    operating_system = models.CharField(max_length=100, blank=True)
    os_version = models.CharField(max_length=100, blank=True)
    architecture = models.CharField(max_length=80, blank=True)
    location = models.CharField(max_length=160, blank=True)
    groups = models.ManyToManyField(ServerGroup, blank=True, related_name="hosts")
    credential = models.ForeignKey(
        "security.Credential", null=True, blank=True, on_delete=models.PROTECT,
        related_name="managed_hosts",
    )
    ansible_limit = models.CharField(max_length=120, blank=True, help_text="Explicit host/group limit configured in Semaphore inventory; wildcards are rejected.")
    prometheus_instance = models.CharField(max_length=160, blank=True, help_text="Exact Prometheus instance label, for example host:9100.")
    environment = models.CharField(max_length=20, choices=Environment.choices, default=Environment.PRODUCTION)
    description = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)
    is_local = models.BooleanField(default=False, help_text="Mark only when this Django process measures this host directly.")
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_connection_at = models.DateTimeField(null=True, blank=True)
    connection_status = models.CharField(max_length=16, choices=ConnectionStatus.choices, default=ConnectionStatus.UNKNOWN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Managed host"
        verbose_name_plural = "Managed hosts"
        constraints = [models.UniqueConstraint(fields=["is_local"], condition=models.Q(is_local=True), name="uniq_local_managed_host")]

    def __str__(self):
        return f"{self.name} ({self.hostname})"
