import json
import shutil
import subprocess

from django.conf import settings


class ContainerDiscoveryService:
    """Read-only local Docker discovery. Disabled until explicitly enabled."""

    @classmethod
    def list_containers(cls):
        if not settings.INFRA_DOCKER_READ_ENABLED:
            return {"available": False, "reason": "Docker discovery is not configured.", "containers": []}
        if not cls._local_host_registered():
            return {"available": False, "reason": "No enabled managed host is marked as local.", "containers": []}
        docker = shutil.which("docker")
        if not docker:
            return {"available": False, "reason": "Docker CLI was not found.", "containers": []}
        try:
            result = subprocess.run(
                [docker, "ps", "-a", "--format", "{{json .}}"],
                capture_output=True, text=True, timeout=8, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return {"available": False, "reason": "Docker discovery timed out or could not start.", "containers": []}
        if result.returncode:
            return {"available": False, "reason": "Docker daemon is unavailable to the configured reader.", "containers": []}

        containers = []
        for line in result.stdout.splitlines()[:500]:
            try:
                item = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            status = str(item.get("State", "unknown")).lower()
            status_text = str(item.get("Status", ""))
            health = "unhealthy" if "unhealthy" in status_text.lower() else (
                "healthy" if "healthy" in status_text.lower() else "unknown"
            )
            containers.append({
                "id": str(item.get("ID", ""))[:12],
                "name": str(item.get("Names", ""))[:160],
                "image": str(item.get("Image", ""))[:200],
                "state": status,
                "status": status_text[:200],
                "ports": str(item.get("Ports", ""))[:300],
                "created": str(item.get("CreatedAt", ""))[:80],
                "health": health,
            })
        return {"available": True, "reason": "", "containers": containers}

    @classmethod
    def list_resources(cls, resource_type):
        commands = {
            "images": ["image", "ls", "--format", "{{json .}}"],
            "networks": ["network", "ls", "--format", "{{json .}}"],
            "volumes": ["volume", "ls", "--format", "{{json .}}"],
            "compose": ["compose", "ls", "--format", "json"],
        }
        if resource_type not in commands:
            return {"available": False, "reason": "Unknown read-only resource type.", "items": []}
        if not settings.INFRA_DOCKER_READ_ENABLED:
            return {"available": False, "reason": "Docker discovery is not configured.", "items": []}
        if not cls._local_host_registered():
            return {"available": False, "reason": "No enabled managed host is marked as local.", "items": []}
        docker = shutil.which("docker")
        if not docker:
            return {"available": False, "reason": "Docker CLI was not found.", "items": []}
        try:
            result = subprocess.run([docker, *commands[resource_type]], capture_output=True,
                                    text=True, timeout=8, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return {"available": False, "reason": "Docker discovery timed out or could not start.", "items": []}
        if result.returncode:
            return {"available": False, "reason": "Docker daemon is unavailable to the configured reader.", "items": []}
        items = []
        for line in result.stdout.splitlines()[:500]:
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                if resource_type == "compose":
                    continue
        return {"available": True, "reason": "", "items": items}

    @staticmethod
    def _local_host_registered():
        from apps.infrastructure.models import ManagedHost
        return ManagedHost.objects.filter(enabled=True, is_local=True).exists()
