from django.utils import timezone

from apps.infrastructure.models import InfrastructureSnapshot, ManagedHost
from infrastructure_engine.adapters.linux.local import collect_local_snapshot
from infrastructure_engine.adapters.ssh.connection import (
    SSHConnectionConfigurationError, SSHConnectionError,
)
from infrastructure_engine.adapters.ssh.discovery import collect_ssh_snapshot


def discover_host(host: ManagedHost) -> InfrastructureSnapshot:
    if host.is_local and host.connection_type == ManagedHost.ConnectionType.LOCAL:
        result = collect_local_snapshot()
    elif not host.is_local and host.connection_type == ManagedHost.ConnectionType.SSH:
        try:
            result = collect_ssh_snapshot(host)
        except SSHConnectionConfigurationError as exc:
            result = _failed_remote_result("ssh", "configuration", str(exc))
        except SSHConnectionError as exc:
            result = _failed_remote_result("ssh", "connection", str(exc))
    else:
        raise ValueError("System discovery supports local process connections and SSH servers.")
    return _store_snapshot(host, result)


def discover_local_host(host: ManagedHost) -> InfrastructureSnapshot:
    if not host.is_local or host.connection_type != ManagedHost.ConnectionType.LOCAL:
        raise ValueError("Live Linux discovery is supported only for a registered local host.")
    return discover_host(host)


def _failed_remote_result(source, reason, message):
    return {
        "source": f"remote-{source}-linux", "status": "failed", "data": {},
        "availability": {"connection": {"status": "unavailable", "reason": reason}},
        "duration_ms": 0, "error_details": message,
    }


def _store_snapshot(host, result):
    captured_at = timezone.now()
    snapshot, _ = InfrastructureSnapshot.objects.update_or_create(
        host=host,
        defaults={
            "source": result["source"], "status": result["status"],
            "data": result["data"], "availability": result["availability"],
            "captured_at": captured_at, "collection_duration_ms": result["duration_ms"],
            "error_details": result["error_details"],
        },
    )
    system = result["data"].get("system") or {}
    host.operating_system = system.get("distribution", system.get("operating_system", ""))
    host.os_version = system.get("kernel", "")
    host.architecture = system.get("architecture", "")
    host.connection_status = ManagedHost.ConnectionStatus.ONLINE if result["status"] != "failed" else ManagedHost.ConnectionStatus.UNREACHABLE
    host.last_checked_at = captured_at
    if result["status"] != "failed":
        host.last_connection_at = captured_at
    host.save(update_fields=["operating_system", "os_version", "architecture", "connection_status", "last_checked_at", "last_connection_at", "updated_at"])
    return snapshot
