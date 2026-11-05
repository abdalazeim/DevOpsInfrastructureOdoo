"""Persistence and live discovery for Docker resources."""

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.containers.models import (
    ComposeProject,
    DockerContainer,
    DockerEngine,
    DockerImage,
    DockerNetwork,
    DockerVolume,
)
from apps.infrastructure.models import ManagedHost
from infrastructure_engine.adapters.docker.client import (
    DockerAdapterError,
    collect_inventory,
)


class DockerInventoryService:
    @classmethod
    def register_local_engine(cls, host_id):
        host = ManagedHost.objects.get(pk=host_id, enabled=True, is_local=True)
        engine, _ = DockerEngine.objects.get_or_create(host=host)
        return engine

    @classmethod
    def discover(cls, engine):
        if not settings.INFRA_DOCKER_READ_ENABLED:
            return {"available": False, "reason": "Docker discovery is not configured."}
        if not engine.enabled or not engine.host.enabled or not engine.host.is_local:
            return {"available": False, "reason": "The Docker engine is disabled or not local."}

        try:
            inventory = collect_inventory(engine)
        except DockerAdapterError as exc:
            engine.status = DockerEngine.Status.UNAVAILABLE
            engine.last_checked_at = timezone.now()
            engine.save(update_fields=["status", "last_checked_at", "updated_at"])
            return {"available": False, "reason": str(exc)}

        observed_at = timezone.now()
        with transaction.atomic():
            engine.status = DockerEngine.Status.AVAILABLE
            engine.engine_version = str(inventory["engine"].get("ServerVersion") or "")[:80]
            engine.api_version = str(inventory["engine"].get("ApiVersion") or "")[:80]
            engine.info = inventory["engine"]
            engine.last_checked_at = observed_at
            engine.save(update_fields=[
                "status", "engine_version", "api_version", "info",
                "last_checked_at", "updated_at",
            ])

            networks = cls._sync_networks(engine, inventory["networks"], observed_at)
            volumes = cls._sync_volumes(engine, inventory["volumes"], observed_at)
            images = cls._sync_images(engine, inventory["images"], observed_at)
            containers = cls._sync_containers(
                engine, inventory["containers"], networks, volumes, images, observed_at
            )
            compose_projects = cls._sync_compose(engine, inventory["compose_projects"], observed_at)

            for kind, result, model in (
                ("network", inventory["networks"], DockerNetwork),
                ("volume", inventory["volumes"], DockerVolume),
                ("image", inventory["images"], DockerImage),
                ("container", inventory["containers"], DockerContainer),
                ("compose", inventory["compose_projects"], ComposeProject),
            ):
                if not result["truncated"]:
                    model.objects.filter(engine=engine).exclude(
                        pk__in=[item.pk for item in {
                            "network": networks,
                            "volume": volumes,
                            "image": images,
                            "container": containers,
                            "compose": compose_projects,
                        }[kind]]
                    ).delete()

        return {
            "available": True,
            "engine_id": engine.pk,
            "observed_at": observed_at.isoformat(),
            "counts": {
                "containers": len(containers),
                "images": len(images),
                "volumes": len(volumes),
                "networks": len(networks),
                "compose_projects": len(compose_projects),
            },
            "truncated": any(
                result["truncated"] for result in inventory.values()
                if isinstance(result, dict) and "truncated" in result
            ),
        }

    @staticmethod
    def _sync_networks(engine, result, observed_at):
        rows = []
        for item in result["items"]:
            row, _ = DockerNetwork.objects.update_or_create(
                engine=engine,
                docker_id=item["docker_id"],
                defaults={
                    "name": item["name"],
                    "driver": item["driver"],
                    "scope": item["scope"],
                    "subnets": item["subnets"],
                    "observed_at": observed_at,
                },
            )
            rows.append(row)
        return rows

    @staticmethod
    def _sync_volumes(engine, result, observed_at):
        rows = []
        for item in result["items"]:
            row, _ = DockerVolume.objects.update_or_create(
                engine=engine,
                name=item["name"],
                defaults={
                    "driver": item["driver"],
                    "mountpoint": item["mountpoint"],
                    "observed_at": observed_at,
                },
            )
            rows.append(row)
        return rows

    @staticmethod
    def _sync_images(engine, result, observed_at):
        rows = []
        for item in result["items"]:
            row, _ = DockerImage.objects.update_or_create(
                engine=engine,
                docker_id=item["docker_id"],
                defaults={
                    "repositories": item["repositories"],
                    "size_bytes": item["size_bytes"],
                    "created_at": item["created_at"],
                    "observed_at": observed_at,
                },
            )
            rows.append(row)
        return rows

    @staticmethod
    def _sync_containers(engine, result, networks, volumes, images, observed_at):
        network_by_name = {item.name: item for item in networks}
        volume_by_name = {item.name: item for item in volumes}
        image_by_id = {item.docker_id: item for item in images}
        rows = []
        for item in result["items"]:
            row, _ = DockerContainer.objects.update_or_create(
                engine=engine,
                docker_id=item["docker_id"],
                defaults={
                    "name": item["name"],
                    "image": item["image"],
                    "image_record": image_by_id.get(item["image_id"]),
                    "state": item["state"],
                    "status": item["status"],
                    "health": item["health"],
                    "ports": item["ports"],
                    "mounts": item["mounts"],
                    "created_at": item["created_at"],
                    "started_at": item["started_at"],
                    "observed_at": observed_at,
                },
            )
            row.networks.set([
                network_by_name[name]
                for name in item["network_names"]
                if name in network_by_name
            ])
            row.volumes.set([
                volume_by_name[mount["source"]]
                for mount in item["mounts"]
                if mount["type"] == "volume" and mount["source"] in volume_by_name
            ])
            rows.append(row)
        return rows

    @staticmethod
    def _sync_compose(engine, result, observed_at):
        rows = []
        for item in result["items"]:
            row, _ = ComposeProject.objects.update_or_create(
                engine=engine,
                name=item["name"],
                defaults={
                    "status": item["status"],
                    "services": item["services"],
                    "observed_at": observed_at,
                },
            )
            rows.append(row)
        return rows
