"""
Local HTTP API for the React dashboard.

Uses only the Python standard library so it runs inside the project virtualenv
without extra dependencies (PyYAML is already required by the CLI).

Run:
    ./launch-odoo-infra.sh --action api --api-port 8787

Endpoints (all JSON):
    GET  /api/health
    GET  /api/profiles
    GET  /api/preflight
    GET  /api/traefik/discovery
    GET  /api/traefik/snapshots
    GET  /api/odoo/discovery
    GET  /api/containers
    GET  /api/backups
    GET  /api/snapshots
    POST /api/operations
    GET  /api/operations
    GET  /api/operations/<id>
"""
from __future__ import annotations

import dataclasses
import glob
import json
import os
import threading
import uuid
from datetime import datetime
from enum import Enum
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = os.environ.get("ODOO_DATA_ROOT", "/opt/odoo-infrastructure")

_OPERATIONS: Dict[str, Any] = {}
_OPERATIONS_LOCK = threading.Lock()


# ------------------------------------------------------------------------------
# Serialization helpers
# ------------------------------------------------------------------------------
def to_jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {k: to_jsonable(v) for k, v in dataclasses.asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(v) for v in value]
    return value


def load_profile(path: str):
    import yaml
    from infrastructure_engine.models.profile import InfrastructureProfile

    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return InfrastructureProfile.from_dict(data)


def list_profiles() -> List[Dict[str, Any]]:
    profiles: List[Dict[str, Any]] = []
    for path in sorted(glob.glob(str(PROJECT_ROOT / "profiles" / "*.yaml"))):
        try:
            profiles.append(load_profile(path))
        except Exception:
            continue
    if not profiles:
        from infrastructure_engine.models.profile import InfrastructureProfile
        profiles.append(InfrastructureProfile(profile_name="default"))
    return profiles


# ------------------------------------------------------------------------------
# Read-only discovery endpoints
# ------------------------------------------------------------------------------
def api_health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "odoo-infrastructure-manager",
        "timestamp": datetime.now().isoformat(),
        "data_root": DATA_ROOT,
    }


def api_preflight() -> Any:
    from infrastructure_engine.services.smart_inspector import SmartInspectorService
    return SmartInspectorService.run_full_inspection()


def api_traefik_discovery() -> Any:
    from infrastructure_engine.services.traefik_manager import TraefikDockerManager
    return TraefikDockerManager.discover_environment()


def api_traefik_snapshots() -> List[Dict[str, Any]]:
    from infrastructure_engine.services.traefik_manager import DEFAULT_CONFIG_DIR
    backups_dir = Path(DEFAULT_CONFIG_DIR) / "backups"
    return _snapshot_entries(backups_dir, "traefik")


def api_odoo_discovery() -> Any:
    from infrastructure_engine.services.odoo_manager import OdooDockerManager
    report = OdooDockerManager.discover_odoo_env()
    report["timestamp"] = datetime.now().isoformat()
    return report


def api_containers() -> List[Dict[str, Any]]:
    import subprocess

    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except Exception:
        return []

    containers: List[Dict[str, Any]] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            containers.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return containers


def _snapshot_entries(directory: Path, prefix: str) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    if not directory.exists():
        return entries
    for path in sorted(directory.glob("*.tar.gz"), reverse=True):
        stat = path.stat()
        digest = ""
        try:
            from infrastructure_engine.services.system_backup import SystemBackupService
            digest = SystemBackupService.calculate_sha256(str(path))
        except Exception:
            pass
        entries.append({
            "id": f"{prefix}-{path.stem}",
            "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "filename": path.name,
            "size_bytes": stat.st_size,
            "sha256": digest,
            "status": "verified" if digest else "unverified",
        })
    return entries


def api_backups(version: Optional[str] = None) -> List[Dict[str, Any]]:
    versions = [version] if version else ["17", "18", "19"]
    backups: List[Dict[str, Any]] = []
    for ver in versions:
        directory = Path(DATA_ROOT) / "backups" / f"odoo{ver}"
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.sql.gz"), reverse=True):
            stat = path.stat()
            backups.append({
                "id": f"backup-{ver}-{path.stem}",
                "version": ver,
                "database": path.name.split("_")[0],
                "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "dump_file": str(path),
                "dump_size_bytes": stat.st_size,
                "sha256": "",
                "has_filestore": (directory / f"{path.stem}_filestore.tar.gz").exists(),
                "status": "verified",
            })
    return backups


def api_snapshots() -> List[Dict[str, Any]]:
    directory = Path(DATA_ROOT) / "backups" / "system_snapshots"
    entries = _snapshot_entries(directory, "full")
    for entry in entries:
        entry["type"] = "full_infrastructure"
        entry["items_count"] = 0
        entry["included"] = []
        entry["verified"] = bool(entry.get("sha256"))
    return entries


# ------------------------------------------------------------------------------
# Operations
# ------------------------------------------------------------------------------
def build_operation(category: str, profile, payload: Dict[str, Any]):
    from infrastructure_engine.workflows.server_prep import ServerPrepWorkflow
    from infrastructure_engine.workflows.deploy_traefik import DeployTraefikWorkflow
    from infrastructure_engine.workflows.deploy_odoo17 import DeployOdoo17Workflow
    from infrastructure_engine.workflows.deploy_odoo18 import DeployOdoo18Workflow
    from infrastructure_engine.workflows.deploy_odoo19 import DeployOdoo19Workflow
    from infrastructure_engine.workflows.database_ops import DatabaseOpsWorkflow
    from infrastructure_engine.workflows.full_deploy import FullDeployWorkflow
    from infrastructure_engine.models.operation import OperationRecord
    from infrastructure_engine.services.health_service import HealthService

    dry_run = bool(payload.get("dryRun", True))
    version = str(payload.get("version", "17"))
    db_name = payload.get("dbName") or f"odoo{version}_prod"

    if category == "prep":
        return ServerPrepWorkflow.create_operation(profile, dry_run=dry_run)
    if category == "traefik":
        return DeployTraefikWorkflow.create_operation(profile, dry_run=dry_run)
    if category == "odoo17":
        return DeployOdoo17Workflow.create_operation(profile, dry_run=dry_run)
    if category == "odoo18":
        return DeployOdoo18Workflow.create_operation(profile, dry_run=dry_run)
    if category == "odoo19":
        return DeployOdoo19Workflow.create_operation(profile, dry_run=dry_run)
    if category == "full":
        return FullDeployWorkflow.create_operation(profile, dry_run=dry_run)
    if category == "backup":
        return DatabaseOpsWorkflow.create_backup_operation(
            version, db_name, retention_count=int(payload.get("retentionCount", 7)), dry_run=dry_run
        )
    if category == "restore":
        return DatabaseOpsWorkflow.create_restore_operation(
            version,
            payload.get("dumpFile", ""),
            payload.get("dbName", db_name),
            force=bool(payload.get("force", False)),
            dry_run=dry_run,
        )
    if category == "health":
        step = HealthService.build_health_check_step()
        return OperationRecord(
            "op-health", "Health Diagnostic Check", "health", profile.profile_name,
            steps=[step], dry_run=dry_run,
        )
    raise ValueError(f"Unsupported operation category: {category}")


def create_operation(payload: Dict[str, Any], profile_path: str) -> Dict[str, Any]:
    category = str(payload.get("category", "")).strip()
    if not category:
        raise ValueError("'category' is required")

    profile = load_profile(profile_path)
    operation = build_operation(category, profile, payload)
    record = {
        "id": f"op-{uuid.uuid4().hex[:12]}",
        "operation": operation,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "finished_at": None,
    }
    with _OPERATIONS_LOCK:
        _OPERATIONS[record["id"]] = record

    if payload.get("execute"):
        thread = threading.Thread(
            target=_execute_operation,
            args=(record, payload.get("dryRun", True)),
            daemon=True,
        )
        thread.start()

    return record


def _execute_operation(record: Dict[str, Any], dry_run: bool) -> None:
    from infrastructure_engine.services.execution_service import ExecutionService
    from infrastructure_engine.models.operation import OperationStatus

    operation = record["operation"]
    record["status"] = "running"
    try:
        for step in operation.steps:
            result = ExecutionService.execute_step(step, dry_run=dry_run)
            if result.status == OperationStatus.FAILED:
                record["status"] = "failed"
                record["finished_at"] = datetime.now().isoformat()
                return
        record["status"] = "success"
    except Exception as exc:  # pragma: no cover - defensive
        record["status"] = "failed"
        record["error"] = str(exc)
    finally:
        record["finished_at"] = datetime.now().isoformat()


def list_operations() -> List[Dict[str, Any]]:
    with _OPERATIONS_LOCK:
        return sorted(_OPERATIONS.values(), key=lambda item: item["created_at"], reverse=True)


# ------------------------------------------------------------------------------
# HTTP handler
# ------------------------------------------------------------------------------
class ApiHandler(BaseHTTPRequestHandler):
    server_version = "OdooInfraAPI/1.0"
    profile_path = "profiles/example.yaml"

    def log_message(self, fmt: str, *args: Any) -> None:
        # Keep the terminal readable: one line per request.
        print(f"[api] {self.address_string()} - {fmt % args}")

    def _send(self, status: int, payload: Any) -> None:
        body = json.dumps(to_jsonable(payload), ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, message: str) -> None:
        self._send(status, {"error": message})

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send(HTTPStatus.NO_CONTENT, {})

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)
        try:
            if route == "/api/health":
                return self._send(HTTPStatus.OK, api_health())
            if route == "/api/profiles":
                return self._send(HTTPStatus.OK, list_profiles())
            if route == "/api/preflight":
                return self._send(HTTPStatus.OK, api_preflight())
            if route == "/api/traefik/discovery":
                return self._send(HTTPStatus.OK, api_traefik_discovery())
            if route == "/api/traefik/snapshots":
                return self._send(HTTPStatus.OK, api_traefik_snapshots())
            if route == "/api/odoo/discovery":
                return self._send(HTTPStatus.OK, api_odoo_discovery())
            if route == "/api/containers":
                return self._send(HTTPStatus.OK, api_containers())
            if route == "/api/backups":
                version = (query.get("version") or [None])[0]
                return self._send(HTTPStatus.OK, api_backups(version))
            if route == "/api/snapshots":
                return self._send(HTTPStatus.OK, api_snapshots())
            if route == "/api/operations":
                return self._send(HTTPStatus.OK, list_operations())
            if route.startswith("/api/operations/"):
                op_id = route.rsplit("/", 1)[-1]
                with _OPERATIONS_LOCK:
                    record = _OPERATIONS.get(op_id)
                if not record:
                    return self._error(HTTPStatus.NOT_FOUND, "Operation not found")
                return self._send(HTTPStatus.OK, record)
            if route == "/":
                return self._send(HTTPStatus.OK, api_health())
            return self._error(HTTPStatus.NOT_FOUND, f"Unknown endpoint: {route}")
        except Exception as exc:
            return self._error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path.rstrip("/") != "/api/operations":
            return self._error(HTTPStatus.NOT_FOUND, "Unknown endpoint")

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            record = create_operation(payload, self.profile_path)
            return self._send(HTTPStatus.CREATED, record)
        except ValueError as exc:
            return self._error(HTTPStatus.BAD_REQUEST, str(exc))
        except Exception as exc:
            return self._error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))


def run_api_server(
    host: str = "127.0.0.1",
    port: int = 8787,
    profile_path: str = "profiles/example.yaml",
    dry_run: bool = False,
) -> None:
    ApiHandler.profile_path = profile_path
    server = ThreadingHTTPServer((host, port), ApiHandler)
    print("=" * 72)
    print(f" Odoo Infrastructure Manager API")
    print(f" Listening on http://{host}:{port}")
    print(f" Profile    : {profile_path} (dry-run={dry_run})")
    print(" Endpoints  : /api/health, /api/profiles, /api/preflight,")
    print("              /api/traefik/discovery, /api/odoo/discovery,")
    print("              /api/containers, /api/backups, /api/operations")
    print("=" * 72)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[api] Shutting down.")
    finally:
        server.server_close()
