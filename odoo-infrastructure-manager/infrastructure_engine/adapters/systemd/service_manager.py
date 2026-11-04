"""Allowlisted, bounded systemd service controls for a registered local host."""
import re
import shutil
import subprocess

from django.conf import settings
from django.utils import timezone

from apps.infrastructure.models import InfrastructureSnapshot, ManagedHost


class SystemdOperationError(Exception):
    def __init__(self, message, *, status_code=409):
        self.status_code = status_code
        super().__init__(message)


_SERVICE_UNIT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@:-]{0,250}\.service$")


class SystemdServiceManager:
    @classmethod
    def validate(cls, host: ManagedHost, unit: str):
        if not host.is_local or host.connection_type != ManagedHost.ConnectionType.LOCAL:
            raise SystemdOperationError("Systemd service control is available only for the local host.")
        if not isinstance(unit, str) or not _SERVICE_UNIT.fullmatch(unit):
            raise SystemdOperationError("A valid systemd service unit is required.")
        try:
            snapshot = host.latest_snapshot
        except InfrastructureSnapshot.DoesNotExist as exc:
            raise SystemdOperationError("Refresh local system data before restarting a service.") from exc
        if snapshot.is_stale:
            raise SystemdOperationError("Refresh local system data before restarting a service.")
        services = snapshot.data.get("services") or {}
        if not isinstance(services, dict):
            services = {}
        known_units = {
            item.get("unit") for item in services.get("items", []) if isinstance(item, dict)
            if item.get("active") == "active" and item.get("substate") == "running"
        }
        if services.get("supported") is not True or unit not in known_units:
            raise SystemdOperationError("Only currently running services from the latest discovery can be restarted.")

    @classmethod
    def restart(cls, host: ManagedHost, unit: str):
        cls.validate(host, unit)
        executable = shutil.which("systemctl")
        if not executable:
            raise SystemdOperationError("systemctl is not installed on the local host.", status_code=503)

        timeout = max(1, min(int(settings.INFRA_OPERATION_TIMEOUT_SECONDS), 300))
        environment = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"}
        try:
            subprocess.run(
                [executable, "--no-ask-password", "restart", unit], check=True,
                capture_output=True, stdin=subprocess.DEVNULL, text=True, timeout=timeout,
                env=environment, close_fds=True,
            )
            verified = subprocess.run(
                [executable, "--no-ask-password", "is-active", "--quiet", unit], check=True,
                capture_output=True, stdin=subprocess.DEVNULL, text=True, timeout=min(timeout, 10),
                env=environment, close_fds=True,
            )
        except subprocess.TimeoutExpired as exc:
            raise SystemdOperationError("The service restart exceeded its time limit.", status_code=504) from exc
        except subprocess.CalledProcessError as exc:
            raise SystemdOperationError("The service restart could not be verified as successful.", status_code=502) from exc
        except OSError as exc:
            raise SystemdOperationError("The system service manager could not be reached.", status_code=503) from exc

        return {
            "service_unit": unit,
            "service_state": "active",
            "verified_at": timezone.now().isoformat(),
            "message": f"{unit} restarted and verified active.",
        }
