from django.core.validators import RegexValidator
from django.db import models


class DockerEngine(models.Model):
    class Status(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        AVAILABLE = "available", "Available"
        UNAVAILABLE = "unavailable", "Unavailable"

    host = models.OneToOneField(
        "infrastructure.ManagedHost",
        on_delete=models.PROTECT,
        related_name="docker_engine",
    )
    endpoint = models.CharField(
        max_length=160,
        default="unix:///var/run/docker.sock",
        validators=[RegexValidator(r"^unix:///var/run/docker\.sock$")],
    )
    enabled = models.BooleanField(default=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.UNKNOWN
    )
    engine_version = models.CharField(max_length=80, blank=True)
    api_version = models.CharField(max_length=80, blank=True)
    info = models.JSONField(default=dict, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["host__name"]

    def __str__(self):
        return f"Docker on {self.host.name}"


class DockerContainer(models.Model):
    engine = models.ForeignKey(
        DockerEngine, on_delete=models.CASCADE, related_name="containers"
    )
    docker_id = models.CharField(max_length=64)
    name = models.CharField(max_length=160)
    image = models.CharField(max_length=255, blank=True)
    image_record = models.ForeignKey(
        "DockerImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="containers",
    )
    state = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=160, blank=True)
    health = models.CharField(max_length=24, blank=True)
    ports = models.JSONField(default=list, blank=True)
    networks = models.ManyToManyField(
        "DockerNetwork", blank=True, related_name="containers"
    )
    volumes = models.ManyToManyField(
        "DockerVolume", blank=True, related_name="containers"
    )
    mounts = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    observed_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["engine", "docker_id"], name="uniq_docker_container_engine_id"
            )
        ]
        indexes = [models.Index(fields=["engine", "state"], name="docker_cont_engine_state_idx")]

    def __str__(self):
        return self.name


class DockerImage(models.Model):
    engine = models.ForeignKey(
        DockerEngine, on_delete=models.CASCADE, related_name="images"
    )
    docker_id = models.CharField(max_length=100)
    repositories = models.JSONField(default=list, blank=True)
    size_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    observed_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["docker_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["engine", "docker_id"], name="uniq_docker_image_engine_id"
            )
        ]


class DockerVolume(models.Model):
    engine = models.ForeignKey(
        DockerEngine, on_delete=models.CASCADE, related_name="volumes"
    )
    name = models.CharField(max_length=255)
    driver = models.CharField(max_length=80, blank=True)
    mountpoint = models.CharField(max_length=512, blank=True)
    observed_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["engine", "name"], name="uniq_docker_volume_engine_name"
            )
        ]


class DockerNetwork(models.Model):
    engine = models.ForeignKey(
        DockerEngine, on_delete=models.CASCADE, related_name="networks"
    )
    docker_id = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    driver = models.CharField(max_length=80, blank=True)
    scope = models.CharField(max_length=80, blank=True)
    subnets = models.JSONField(default=list, blank=True)
    observed_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["engine", "docker_id"], name="uniq_docker_network_engine_id"
            )
        ]


class ComposeProject(models.Model):
    engine = models.ForeignKey(
        DockerEngine, on_delete=models.CASCADE, related_name="compose_projects"
    )
    name = models.CharField(max_length=160)
    status = models.CharField(max_length=80, blank=True)
    services = models.JSONField(default=list, blank=True)
    observed_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["engine", "name"], name="uniq_compose_project_engine_name"
            )
        ]
