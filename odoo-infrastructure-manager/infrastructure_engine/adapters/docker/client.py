"""Bounded local Docker SDK operations for a registered engine."""

import re
from datetime import datetime

from django.conf import settings


LOCAL_DOCKER_ENDPOINT = "unix:///var/run/docker.sock"
MAX_RESOURCES = 500
MAX_TEXT = 512


class DockerAdapterError(Exception):
    """A Docker SDK call failed without exposing daemon or socket details."""


def create_client(engine):
    if engine.endpoint != LOCAL_DOCKER_ENDPOINT:
        raise DockerAdapterError("Only the configured local Docker socket is supported.")
    try:
        import docker

        return docker.DockerClient(
            base_url=LOCAL_DOCKER_ENDPOINT,
            version="auto",
            timeout=max(1, min(int(settings.INFRA_OPERATION_TIMEOUT_SECONDS), 30)),
        )
    except ImportError as exc:
        raise DockerAdapterError("Docker SDK is not installed.") from exc
    except Exception as exc:
        raise DockerAdapterError(type(exc).__name__) from exc


def collect_inventory(engine):
    client = create_client(engine)
    try:
        info = client.info()
        containers = _collect_containers(client)
        images = _collect_images(client)
        volumes = _collect_volumes(client)
        networks = _collect_networks(client)
        return {
            "engine": _safe_engine_info(info),
            "containers": containers,
            "images": images,
            "volumes": volumes,
            "networks": networks,
            "compose_projects": _compose_projects(containers),
        }
    except DockerAdapterError:
        raise
    except Exception as exc:
        raise DockerAdapterError(type(exc).__name__) from exc
    finally:
        client.close()


def perform_container_action(engine, docker_id, action):
    if action not in {"start", "stop", "restart", "pause", "resume", "remove"}:
        raise DockerAdapterError("Unsupported Docker container action.")
    client = create_client(engine)
    try:
        container = client.containers.get(docker_id)
        if action == "start":
            container.start()
        elif action == "stop":
            container.stop(timeout=10)
        elif action == "restart":
            container.restart(timeout=10)
        elif action == "pause":
            container.pause()
        elif action == "resume":
            container.unpause()
        else:
            container.remove(force=False, v=False)
        return {"action": action, "container_id": docker_id}
    except DockerAdapterError:
        raise
    except Exception as exc:
        raise DockerAdapterError(type(exc).__name__) from exc
    finally:
        client.close()


def read_container_logs(engine, docker_id, tail):
    if not isinstance(tail, int) or not 1 <= tail <= 200:
        raise DockerAdapterError("Log tail must be between 1 and 200.")
    client = create_client(engine)
    try:
        output = client.containers.get(docker_id).logs(
            stdout=True, stderr=True, tail=tail, timestamps=False
        )
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        return str(output)[:40000]
    except DockerAdapterError:
        raise
    except Exception as exc:
        raise DockerAdapterError(type(exc).__name__) from exc
    finally:
        client.close()


def _collect_containers(client):
    rows = []
    for container in client.containers.list(all=True, limit=MAX_RESOURCES + 1):
        attrs = container.attrs or {}
        config = attrs.get("Config") or {}
        state = attrs.get("State") or {}
        networking = attrs.get("NetworkSettings") or {}
        ports = []
        for port, bindings in (networking.get("Ports") or {}).items():
            for binding in bindings or []:
                ports.append({
                    "container_port": _text(port, 64),
                    "host_ip": _text(binding.get("HostIp"), 64),
                    "host_port": _text(binding.get("HostPort"), 16),
                })
        mounts = [
            {
                "type": _text(mount.get("Type"), 32),
                "source": _text(mount.get("Source"), MAX_TEXT),
                "destination": _text(mount.get("Destination"), MAX_TEXT),
                "read_write": bool(mount.get("RW")),
            }
            for mount in (attrs.get("Mounts") or [])[:64]
        ]
        networks = list((networking.get("Networks") or {}).keys())[:64]
        health = (state.get("Health") or {}).get("Status", "")
        labels = config.get("Labels") or {}
        rows.append({
            "docker_id": _text(container.id, 64),
            "name": _text(container.name, 160),
            "image": _text(config.get("Image"), 255),
            "image_id": _text(attrs.get("Image"), 100),
            "state": _text(state.get("Status"), 32),
            "status": _text(container.status, 160),
            "health": _text(health, 24),
            "ports": ports[:64],
            "network_names": networks,
            "mounts": mounts,
            "created_at": _parse_datetime(attrs.get("Created")),
            "started_at": _parse_datetime(state.get("StartedAt")),
            "compose_project": _text(labels.get("com.docker.compose.project"), 160),
            "compose_service": _text(labels.get("com.docker.compose.service"), 160),
        })
        if len(rows) > MAX_RESOURCES:
            break
    return {"items": rows[:MAX_RESOURCES], "truncated": len(rows) > MAX_RESOURCES}


def _collect_images(client):
    rows = []
    for image in client.images.list():
        attrs = image.attrs or {}
        rows.append({
            "docker_id": _text(image.id, 100),
            "repositories": [_text(tag, 255) for tag in (image.tags or [])[:32]],
            "size_bytes": _nonnegative_int(attrs.get("Size")),
            "created_at": _parse_datetime(attrs.get("Created")),
        })
        if len(rows) > MAX_RESOURCES:
            break
    return {"items": rows[:MAX_RESOURCES], "truncated": len(rows) > MAX_RESOURCES}


def _collect_volumes(client):
    rows = []
    for volume in client.volumes.list():
        attrs = volume.attrs or {}
        rows.append({
            "name": _text(volume.name, 255),
            "driver": _text(attrs.get("Driver"), 80),
            "mountpoint": _text(attrs.get("Mountpoint"), MAX_TEXT),
        })
        if len(rows) > MAX_RESOURCES:
            break
    return {"items": rows[:MAX_RESOURCES], "truncated": len(rows) > MAX_RESOURCES}


def _collect_networks(client):
    rows = []
    for network in client.networks.list():
        attrs = network.attrs or {}
        config = ((attrs.get("IPAM") or {}).get("Config") or [])[:32]
        rows.append({
            "docker_id": _text(network.id, 64),
            "name": _text(network.name, 255),
            "driver": _text(attrs.get("Driver"), 80),
            "scope": _text(attrs.get("Scope"), 80),
            "subnets": [
                {
                    "subnet": _text(item.get("Subnet"), 64),
                    "gateway": _text(item.get("Gateway"), 64),
                }
                for item in config
            ],
        })
        if len(rows) > MAX_RESOURCES:
            break
    return {"items": rows[:MAX_RESOURCES], "truncated": len(rows) > MAX_RESOURCES}


def _compose_projects(containers):
    projects = {}
    for item in containers["items"]:
        project = item["compose_project"]
        service = item["compose_service"]
        if project:
            projects.setdefault(project, {"name": project, "services": set(), "states": []})
            if service:
                projects[project]["services"].add(service)
            projects[project]["states"].append(item["state"])
    return {
        "items": [
            {
                "name": name,
                "services": sorted(item["services"])[:128],
                "status": "running" if item["states"] and all(
                    state == "running" for state in item["states"]
                ) else "partial",
            }
            for name, item in sorted(projects.items())[:MAX_RESOURCES]
        ],
        "truncated": len(projects) > MAX_RESOURCES or containers["truncated"],
    }


def _safe_engine_info(info):
    allowed = {
        "ID", "Name", "ServerVersion", "ApiVersion", "OperatingSystem",
        "Architecture", "KernelVersion", "NCPU", "MemTotal", "Containers",
        "ContainersRunning", "ContainersPaused", "ContainersStopped", "Images",
        "Driver",
    }
    return {
        key: value
        for key, value in info.items()
        if key in allowed and isinstance(value, (str, int, float, bool, type(None)))
    }


def _text(value, limit):
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"[\x00-\x1f\x7f]", "", text)
    return text[:limit]


def _nonnegative_int(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
