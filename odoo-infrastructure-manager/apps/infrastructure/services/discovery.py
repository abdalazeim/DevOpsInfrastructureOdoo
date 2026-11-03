from django.utils import timezone

from apps.infrastructure.models import InfrastructureSnapshot, ManagedHost
from infrastructure_engine.adapters.linux.local import collect_local_snapshot


def discover_local_host(host: ManagedHost) -> InfrastructureSnapshot:
    if not host.is_local or host.connection_type != ManagedHost.ConnectionType.LOCAL:
        raise ValueError("Live Linux discovery is supported only for a registered local host.")
    result = collect_local_snapshot()
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
    host.operating_system = result["data"].get("system", {}).get("distribution", "") if result["data"].get("system") else ""
    host.os_version = result["data"].get("system", {}).get("kernel", "") if result["data"].get("system") else ""
    host.architecture = result["data"].get("system", {}).get("architecture", "") if result["data"].get("system") else ""
    host.connection_status = ManagedHost.ConnectionStatus.ONLINE if result["status"] != "failed" else ManagedHost.ConnectionStatus.UNREACHABLE
    host.last_checked_at = captured_at
    if result["status"] != "failed":
        host.last_connection_at = captured_at
    host.save(update_fields=["operating_system", "os_version", "architecture", "connection_status", "last_checked_at", "last_connection_at", "updated_at"])
    return snapshot
