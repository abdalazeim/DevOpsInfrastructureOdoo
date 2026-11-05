from django.db import transaction
from django.utils import timezone

from apps.infrastructure.models import (
    InfrastructureSnapshot,
    InfrastructureSyncRecord,
    ManagedHost,
)
from infrastructure_engine.adapters.linux.local import collect_local_snapshot
from infrastructure_engine.adapters.ssh.connection import (
    SSHConnectionConfigurationError, SSHConnectionError,
)
from infrastructure_engine.adapters.ssh.discovery import collect_ssh_snapshot


def discover_host(host: ManagedHost) -> InfrastructureSnapshot:
    started_at = timezone.now()
    try:
        if host.is_local and host.connection_type == ManagedHost.ConnectionType.LOCAL:
            result = collect_local_snapshot()
        elif not host.is_local and host.connection_type == ManagedHost.ConnectionType.SSH:
            result = collect_ssh_snapshot(host)
        else:
            raise ValueError("System discovery supports local process connections and SSH servers.")
    except SSHConnectionConfigurationError as exc:
        result = _failed_remote_result("ssh", "configuration", str(exc))
    except SSHConnectionError as exc:
        result = _failed_remote_result("ssh", "connection", str(exc))
    except Exception as exc:
        _record_failed_sync(host, started_at, type(exc).__name__)
        raise
    return _store_snapshot(host, result, started_at=started_at)


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


def _store_snapshot(host, result, *, started_at):
    captured_at = timezone.now()
    system = result["data"].get("system") or {}
    with transaction.atomic():
        snapshot, _ = InfrastructureSnapshot.objects.update_or_create(
            host=host,
            defaults={
                "source": result["source"], "status": result["status"],
                "data": result["data"], "availability": result["availability"],
                "captured_at": captured_at, "collection_duration_ms": result["duration_ms"],
                "error_details": result["error_details"][:2000],
            },
        )
        InfrastructureSyncRecord.objects.create(
            host=host,
            source=result["source"],
            status=result["status"],
            updated_sections=[
                name for name, state in result["availability"].items()
                if state.get("status") == "available"
            ],
            error_details=result["error_details"][:2000],
            collection_duration_ms=result["duration_ms"],
            started_at=started_at,
            completed_at=captured_at,
        )

        changed_fields = []
        for field, value in (
            ("operating_system", system.get("distribution") or system.get("operating_system")),
            ("os_version", system.get("kernel")),
            ("architecture", system.get("architecture")),
        ):
            if isinstance(value, str) and value and getattr(host, field) != value:
                setattr(host, field, value[: ManagedHost._meta.get_field(field).max_length])
                changed_fields.append(field)
        host.connection_status = (
            ManagedHost.ConnectionStatus.ONLINE
            if result["status"] != "failed"
            else ManagedHost.ConnectionStatus.UNREACHABLE
        )
        host.last_checked_at = captured_at
        if result["status"] != "failed":
            host.last_connection_at = captured_at
        changed_fields.extend(
            ["connection_status", "last_checked_at", "last_connection_at", "updated_at"]
        )
        host.save(update_fields=changed_fields)
    return snapshot


def _record_failed_sync(host, started_at, error_name):
    completed_at = timezone.now()
    with transaction.atomic():
        InfrastructureSyncRecord.objects.create(
            host=host,
            source="unknown",
            status=InfrastructureSyncRecord.Status.FAILED,
            updated_sections=[],
            error_details=f"Discovery failed unexpectedly ({error_name}).",
            collection_duration_ms=max(
                0, int((completed_at - started_at).total_seconds() * 1000)
            ),
            started_at=started_at,
            completed_at=completed_at,
        )
        host.connection_status = ManagedHost.ConnectionStatus.UNREACHABLE
        host.last_checked_at = completed_at
        host.save(update_fields=["connection_status", "last_checked_at", "updated_at"])
