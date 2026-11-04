"""
Odoo Infrastructure Manager Module
Provides discovery, lifecycle management, and diagnostics for Odoo 17, 18 & 19
environments.

Container names and data paths follow the dedicated instance folders created by
automation/scripts/install-odoo.sh (Odoo-MultiVersion-Deployment layout):
  - containers: odoo17 / odoo17-db, odoo18 / odoo18-db, odoo19 / odoo19-db
  - data:       /opt/odoo-infrastructure/odoo{17,18,19}
"""
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]

VERSIONS = ("17", "18", "19")
DEFAULT_DATA_ROOT = os.environ.get("ODOO_DATA_ROOT", "/opt/odoo-infrastructure")


def instance_dir(version: str) -> str:
    """Returns the dedicated instance folder for a version."""
    return os.environ.get(f"ODOO{version}_DIR", f"{DEFAULT_DATA_ROOT}/odoo{version}")


class OdooDockerManager:
    CONFIG = {
        version: {
            "dir": instance_dir(version),
            "docker_compose": f"{instance_dir(version)}/docker-compose.yml",
            "container_name": f"odoo{version}",
            "db_container": f"odoo{version}-db",
            "database": os.environ.get(f"ODOO{version}_DB_NAME", f"odoo{version}_prod"),
            "pg_version": {"17": "16", "18": "17", "19": "18"}[version],
        }
        for version in VERSIONS
    }

    @classmethod
    def discover_odoo_env(cls) -> Dict[str, Any]:
        """Audits all Odoo environments."""
        report: Dict[str, Any] = {
            f"odoo{version}": cls._inspect_instance(version) for version in VERSIONS
        }
        report["proxy_network_exists"] = cls._check_network("proxy")
        report["warnings"] = []
        if not report["proxy_network_exists"]:
            report["warnings"].append("Docker network 'proxy' does not exist yet.")
        return report

    @classmethod
    def _docker_exec(cls, container: str, command: list, timeout: int = 5) -> bool:
        try:
            return subprocess.run(
                ["docker", "exec", container, *command],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
                check=False,
            ).returncode == 0
        except Exception:
            return False

    @classmethod
    def _check_network(cls, network: str) -> bool:
        try:
            return subprocess.run(
                ["docker", "network", "inspect", network],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                check=False,
            ).returncode == 0
        except Exception:
            return False

    @classmethod
    def _inspect_instance(cls, version: str) -> Dict[str, Any]:
        """Audits actual Docker state (no hardcoded readiness mocks)."""
        cfg = cls.CONFIG.get(version)
        if not cfg:
            return {"container_status": "not_found", "image": "N/A", "version": version}

        default = {
            "container_status": "not_found",
            "image": "N/A",
            "uptime": "N/A",
            "db_ready": False,
            "http_ready": False,
            "version": version,
            "pg_version": cfg["pg_version"],
        }

        try:
            res = subprocess.run(
                ["docker", "inspect", cfg["container_name"]],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
                check=False,
            )
        except Exception:
            return default

        if res.returncode != 0 or not res.stdout.strip():
            return default

        try:
            data = json.loads(res.stdout)[0]
        except (json.JSONDecodeError, IndexError):
            return default

        state = data.get("State", {}) or {}
        running = bool(state.get("Running"))
        db_user = os.environ.get(f"ODOO{version}_DB_USER", "odoo")

        db_ready = running and cls._docker_exec(
            cfg["db_container"], ["pg_isready", "-U", db_user, "-d", cfg["database"]]
        )
        http_ready = running and cls._docker_exec(
            cfg["container_name"],
            [
                "python3",
                "-c",
                "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8069/web/health', timeout=3)",
            ],
        )

        return {
            "container_status": "running" if running else "stopped",
            "image": (data.get("Config", {}) or {}).get("Image", "unknown"),
            "uptime": state.get("StartedAt", "N/A"),
            "db_ready": db_ready,
            "http_ready": http_ready,
            "version": version,
            "pg_version": cfg["pg_version"],
        }

    @classmethod
    def lifecycle_action(cls, version: str, action: str) -> bool:
        """Executes start/stop/restart/logs via the deployment script."""
        if version not in cls.CONFIG:
            return False
        if action not in {"start", "stop", "restart", "logs", "check"}:
            return False

        script = PROJECT_ROOT / "automation" / "scripts" / "deploy-odoo.sh"
        return subprocess.run(["bash", str(script), version, action], check=False).returncode == 0
