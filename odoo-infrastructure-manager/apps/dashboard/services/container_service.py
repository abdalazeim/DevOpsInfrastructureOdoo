from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.containers.models import (
    ComposeProject,
    DockerContainer,
    DockerEngine,
    DockerImage,
    DockerNetwork,
    DockerVolume,
)


class ContainerDiscoveryService:
    """Read-only projections of the canonical, persisted Docker inventory."""

    @classmethod
    def list_containers(cls, engine=None):
        engine, reason = cls._available_engine(engine)
        if engine is None:
            return {"available": False, "reason": reason, "containers": [], "stale": False}

        stale = timezone.now() - engine.last_checked_at > timedelta(minutes=5)
        containers = [
            {
                "id": item.docker_id,
                "name": item.name,
                "image": item.image,
                "state": item.state,
                "status": item.status,
                "health": item.health or "unknown",
                "ports": ", ".join(
                    f"{port.get('host_ip') or '0.0.0.0'}:{port.get('host_port')}->{port.get('container_port')}"
                    for port in item.ports
                ),
                "created": item.created_at.isoformat() if item.created_at else "",
                "observed_at": item.observed_at.isoformat(),
            }
            for item in DockerContainer.objects.filter(engine=engine).order_by("name")[:500]
        ]
        return {
            "available": not stale,
            "reason": "The saved Docker inventory is stale; refresh it before relying on its state." if stale else "",
            "containers": containers,
            "stale": stale,
            "engine": engine,
        }

    @classmethod
    def list_resources(cls, resource_type, engine=None):
        model_fields = {
            "images": (DockerImage, ("docker_id", "repositories", "size_bytes", "created_at", "observed_at")),
            "networks": (DockerNetwork, ("docker_id", "name", "driver", "scope", "subnets", "observed_at")),
            "volumes": (DockerVolume, ("name", "driver", "mountpoint", "observed_at")),
            "compose": (ComposeProject, ("name", "status", "services", "observed_at")),
        }
        if resource_type not in model_fields:
            return {"available": False, "reason": "Unknown Docker resource type.", "items": [], "stale": False}

        engine, reason = cls._available_engine(engine)
        if engine is None:
            return {"available": False, "reason": reason, "items": [], "stale": False}

        stale = timezone.now() - engine.last_checked_at > timedelta(minutes=5)
        model, fields = model_fields[resource_type]
        items = list(model.objects.filter(engine=engine).values(*fields)[:500])
        return {
            "available": not stale,
            "reason": "The saved Docker inventory is stale; refresh it before relying on its state." if stale else "",
            "items": items,
            "stale": stale,
            "engine": engine,
        }

    @staticmethod
    def _available_engine(engine=None):
        if not settings.INFRA_DOCKER_READ_ENABLED:
            return None, "Docker discovery is not configured."
        if engine is None:
            engine = (
                DockerEngine.objects.filter(
                    enabled=True, host__enabled=True, host__is_local=True
                )
                .select_related("host")
                .first()
            )
        elif not (
            engine.enabled
            and engine.host.enabled
            and engine.host.is_local
        ):
            return None, "The Docker engine is disabled or not local."
        if engine is None:
            return None, "Register a Docker engine for an enabled local managed server."
        if engine.status != DockerEngine.Status.AVAILABLE or engine.last_checked_at is None:
            return None, "The Docker engine has not completed a successful discovery."
        return engine, ""
