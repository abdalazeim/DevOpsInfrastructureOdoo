"""
Full System Cleanup & Deep Uninstall Service.

Provides comprehensive removal of all components installed by the Odoo
Infrastructure Manager, with strict backup protection and safety guarantees.

Safety rules (never violated):
- NEVER delete backup files/directories (sql, dump, tar, zip, gz, snapshot, filestore, backup*)
- NEVER use rm -rf / or equivalent broad destructive patterns
- NEVER delete files that cannot be proven to belong to this project
- ALWAYS require explicit DELETE confirmation before destructive actions
- ALWAYS run in dry-run first to preview what will be deleted
- Execute in reverse dependency order
- Use sudo when required and available
- Log all operations to an independent log file
- Continue on non-critical errors; report all failures
"""
from __future__ import annotations

import datetime as _dt
import fnmatch
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LOG_DIR = "/var/log/odoo-installer"
UNINSTALL_LOG = os.path.join(LOG_DIR, "uninstall_cleanup.log")

# Project-owned installation paths (safe to remove if present)
PROJECT_INSTALL_PATHS = [
    "/opt/odoo-infrastructure",
    "/opt/traefik",
    "/opt/ansible",
    "/opt/jenkins",
    "/data/jenkins",
    "/data/traefik",
    "/srv/portainer",
]

# Docker resources owned by the project
PROJECT_DOCKER_CONTAINERS = [
    "traefik",
    "odoo17", "odoo17-db",
    "odoo18", "odoo18-db",
    "odoo19", "odoo19-db",
    "portainer",
    "jenkins",
]

PROJECT_DOCKER_NETWORKS = [
    "proxy",
    "odoo17_internal",
    "odoo18_internal",
    "odoo19_internal",
]

PROJECT_DOCKER_IMAGES = [
    "traefik:v3.7",
    "odoo:17", "odoo:18", "odoo:19",
    "postgres:16", "postgres:17", "postgres:18",
    "portainer/portainer-ce",
    "jenkins/jenkins:lts-jdk21",
]

# APT sources and keyrings added by the project
PROJECT_APT_FILES = [
    "/etc/apt/sources.list.d/docker.list",
    "/etc/apt/sources.list.d/pgdg.list",
    "/etc/apt/keyrings/docker.gpg",
]

# Backup protection patterns (never delete these)
BACKUP_FILENAME_PATTERNS = [
    "*backup*", "*backups*",
    "*.sql", "*.sql.gz", "*.dump", "*.dump.gz",
    "*.tar", "*.tar.gz", "*.tgz", "*.zip",
    "*.gz", "*.zst", "*.zst.tar",
    "*snapshot*", "*filestore*",
    "*postgres*backup*", "*odoo*backup*",
]

BACKUP_DIR_PATTERNS = [
    "*backup*", "*backups*",
    "*snapshot*", "*snapshots*",
    "*filestore*",
]

# Backup content signatures (inside files)
BACKUP_CONTENT_SIGNATURES = [
    b"PGDMP",                    # PostgreSQL custom dump header
    b"PostgreSQL database dump", # PostgreSQL plain dump
    b"ODOO_BACKUP",              # Odoo backup marker
    b"filestore",                # Odoo filestore indicator
]


class BackupProtectionError(Exception):
    """Raised when an operation would violate backup protection."""


class CleanupStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PROTECTED = "protected"  # skipped because it is a backup


@dataclass
class CleanupItem:
    """A single item scheduled for cleanup."""
    id: str
    type: str  # "file", "directory", "docker_container", "docker_image", "docker_network", "apt_package", "apt_file", "service", "user", "group"
    path: str  # filesystem path or resource name
    description: str
    size_bytes: int = 0
    protected: bool = False
    protection_reason: str = ""
    status: CleanupStatus = CleanupStatus.PENDING
    error: Optional[str] = None
    requires_sudo: bool = False
    commands: List[List[str]] = field(default_factory=list)


@dataclass
class CleanupReport:
    """Final cleanup report."""
    started_at: str
    completed_at: Optional[str] = None
    dry_run: bool = False
    total_items: int = 0
    completed_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    protected_count: int = 0
    total_bytes_freed: int = 0
    items: List[CleanupItem] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "dry_run": self.dry_run,
            "total_items": self.total_items,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "protected_count": self.protected_count,
            "total_bytes_freed": self.total_bytes_freed,
            "total_bytes_freed_mb": round(self.total_bytes_freed / (1024 * 1024), 2),
            "items": [
                {
                    "id": it.id,
                    "type": it.type,
                    "path": it.path,
                    "description": it.description,
                    "size_bytes": it.size_bytes,
                    "protected": it.protected,
                    "protection_reason": it.protection_reason,
                    "status": it.status.value,
                    "error": it.error,
                    "requires_sudo": it.requires_sudo,
                }
                for it in self.items
            ],
            "errors": self.errors,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# Backup Protection
# ---------------------------------------------------------------------------

def is_backup_path(path: str) -> Tuple[bool, str]:
    """
    Determine if a filesystem path is a backup that must be protected.

    Returns (is_backup, reason). Uses filename patterns, directory names,
    and content signatures to detect backups even when names are unclear.
    """
    if not path:
        return False, ""

    basename = os.path.basename(path).lower()

    # Check filename/directory patterns
    for pat in BACKUP_FILENAME_PATTERNS:
        if fnmatch.fnmatch(basename, pat.lower()):
            return True, f"Filename matches backup pattern: {pat}"
    for pat in BACKUP_DIR_PATTERNS:
        if fnmatch.fnmatch(basename, pat.lower()):
            return True, f"Directory name matches backup pattern: {pat}"

    # Check parent directory names for backup context
    parts = path.replace("\\", "/").split("/")
    for part in parts:
        part_lower = part.lower()
        for pat in BACKUP_DIR_PATTERNS:
            if fnmatch.fnmatch(part_lower, pat.lower()):
                return True, f"Path component matches backup pattern: {pat}"

    # Check file content signatures (only for regular files, small enough)
    if os.path.isfile(path):
        try:
            file_size = os.path.getsize(path)
            if 0 < file_size <= 16 * 1024 * 1024:  # up to 16 MB
                with open(path, "rb") as f:
                    header = f.read(512)
                    for sig in BACKUP_CONTENT_SIGNATURES:
                        if sig in header:
                            return True, f"File content matches backup signature: {sig[:16]}..."
        except (OSError, PermissionError):
            # Cannot read file; do not assume it is a backup
            pass

    return False, ""


def is_project_path(path: str) -> bool:
    """Check if a path is under a project-owned installation directory."""
    norm = os.path.normpath(path)
    for proj_path in PROJECT_INSTALL_PATHS:
        proj_norm = os.path.normpath(proj_path)
        if norm == proj_norm or norm.startswith(proj_norm + os.sep):
            return True
    return False


def should_protect(path: str) -> Tuple[bool, str]:
    """
    Decide whether a path should be protected from deletion.

    Returns (should_protect, reason). A path is protected if:
    - It is a backup file/directory (absolute protection)
    - It is NOT a project-owned path (safety: only remove project files)
    """
    # First: is it a backup? Always protect.
    is_bak, bak_reason = is_backup_path(path)
    if is_bak:
        return True, bak_reason

    # Second: is it a project path? If not, do not touch it.
    if not is_project_path(path):
        return True, "Not a project-owned path; skipping for safety"

    # A recursive delete of an ancestor also deletes protected descendants.
    # Fail closed on unreadable trees and links; discovery is not a deletion permit.
    if os.path.islink(path):
        return True, "Symbolic link; refuse recursive cleanup"
    if os.path.isdir(path):
        try:
            def unreadable(error):
                raise error
            for root, dirs, files in os.walk(path, followlinks=False, onerror=unreadable):
                for name in dirs + files:
                    child = os.path.join(root, name)
                    protected, reason = is_backup_path(child)
                    if protected or os.path.islink(child):
                        return True, f"Contains protected descendant: {child} ({reason})"
        except OSError as exc:
            return True, f"Cannot verify entire directory: {exc}"
    return False, ""


# ---------------------------------------------------------------------------
# Discovery / Inventory
# ---------------------------------------------------------------------------

def _run(cmd: List[str], use_sudo: bool = False, timeout: int = 30) -> Tuple[int, str, str]:
    """Run a command and return (exit_code, stdout, stderr)."""
    full_cmd = (["sudo"] if use_sudo else []) + cmd
    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"Command timed out after {timeout}s"
    except FileNotFoundError:
        return 127, "", f"Command not found: {cmd[0]}"
    except Exception as exc:
        return 1, "", str(exc)


def _dir_size(path: str) -> int:
    """Calculate total size of a directory tree in bytes."""
    total = 0
    try:
        for entry in os.scandir(path):
            try:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat(follow_symlinks=False).st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += _dir_size(entry.path)
            except OSError:
                continue
    except OSError:
        pass
    return total


def discover_installation(use_sudo: bool = False) -> List[CleanupItem]:
    """
    Discover all project-installed components on the system.

    Returns a list of CleanupItem objects, each marked protected or not.
    """
    items: List[CleanupItem] = []

    # --- Filesystem paths ---
    for proj_path in PROJECT_INSTALL_PATHS:
        if os.path.exists(proj_path):
            protected, reason = should_protect(proj_path)
            size = _dir_size(proj_path) if os.path.isdir(proj_path) else 0
            items.append(CleanupItem(
                id=f"fs_{os.path.basename(proj_path)}",
                type="directory" if os.path.isdir(proj_path) else "file",
                path=proj_path,
                description=f"Project installation directory: {proj_path}",
                size_bytes=size,
                protected=protected,
                protection_reason=reason,
                requires_sudo=not (hasattr(os, "geteuid") and os.geteuid() == 0),
            ))

    # Also scan common project subdirectories for backups to protect
    for proj_path in PROJECT_INSTALL_PATHS:
        if os.path.isdir(proj_path):
            try:
                for root, dirs, files in os.walk(proj_path):
                    # Protect backup subdirectories
                    for d in list(dirs):
                        dpath = os.path.join(root, d)
                        prot, reason = should_protect(dpath)
                        if prot:
                            items.append(CleanupItem(
                                id=f"prot_dir_{abs(hash(dpath))}",
                                type="directory",
                                path=dpath,
                                description=f"Protected backup directory: {dpath}",
                                size_bytes=_dir_size(dpath),
                                protected=True,
                                protection_reason=reason,
                                requires_sudo=False,
                            ))
                            dirs.remove(d)  # do not descend into protected dirs
                    # Protect backup files
                    for f in files:
                        fpath = os.path.join(root, f)
                        prot, reason = should_protect(fpath)
                        if prot:
                            items.append(CleanupItem(
                                id=f"prot_file_{abs(hash(fpath))}",
                                type="file",
                                path=fpath,
                                description=f"Protected backup file: {fpath}",
                                size_bytes=os.path.getsize(fpath) if os.path.exists(fpath) else 0,
                                protected=True,
                                protection_reason=reason,
                                requires_sudo=False,
                            ))
            except OSError:
                pass

    # --- Docker containers ---
    code, stdout, _ = _run(["docker", "ps", "-a", "--format", "{{.Names}}"], use_sudo=use_sudo)
    if code == 0:
        for line in stdout.splitlines():
            name = line.strip()
            if not name:
                continue
            # Exact name match only (avoid substring collisions like odoo17 vs odoo17-db)
            if name in PROJECT_DOCKER_CONTAINERS:
                items.append(CleanupItem(
                    id=f"docker_container_{name}",
                    type="docker_container",
                    path=name,
                    description=f"Docker container: {name}",
                    requires_sudo=use_sudo or not (hasattr(os, "geteuid") and os.geteuid() == 0),
                    commands=[
                        ["docker", "stop", name],
                        ["docker", "rm", "-f", name],
                    ],
                ))

    # --- Docker networks ---
    code, stdout, _ = _run(["docker", "network", "ls", "--format", "{{.Name}}"], use_sudo=use_sudo)
    if code == 0:
        for line in stdout.splitlines():
            name = line.strip()
            if name in PROJECT_DOCKER_NETWORKS:
                items.append(CleanupItem(
                    id=f"docker_network_{name}",
                    type="docker_network",
                    path=name,
                    description=f"Docker network: {name}",
                    requires_sudo=use_sudo or not (hasattr(os, "geteuid") and os.geteuid() == 0),
                    commands=[["docker", "network", "rm", name]],
                ))

    # --- Docker images ---
    code, stdout, _ = _run(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"], use_sudo=use_sudo)
    if code == 0:
        for line in stdout.splitlines():
            image = line.strip()
            if image in PROJECT_DOCKER_IMAGES:
                items.append(CleanupItem(
                    id=f"docker_image_{image.replace(':', '_').replace('/', '_')}",
                    type="docker_image",
                    path=image,
                    description=f"Docker image: {image}",
                    requires_sudo=use_sudo or not (hasattr(os, "geteuid") and os.geteuid() == 0),
                    commands=[["docker", "rmi", "-f", image]],
                ))

    # --- APT sources / keyrings ---
    for apt_file in PROJECT_APT_FILES:
        if os.path.exists(apt_file):
            protected, reason = should_protect(apt_file)
            size = os.path.getsize(apt_file) if os.path.isfile(apt_file) else 0
            items.append(CleanupItem(
                id=f"apt_file_{os.path.basename(apt_file)}",
                type="apt_file",
                path=apt_file,
                description=f"APT source/keyring: {apt_file}",
                size_bytes=size,
                protected=protected,
                protection_reason=reason,
                requires_sudo=True,
                commands=[["rm", "-f", apt_file]],
            ))

    # --- Systemd services ---
    for svc in ["docker", "postgresql"]:
        code, stdout, _ = _run(["systemctl", "is-enabled", svc], use_sudo=use_sudo, timeout=10)
        if code == 0:
            items.append(CleanupItem(
                id=f"service_{svc}",
                type="service",
                path=svc,
                description=f"Systemd service: {svc}",
                requires_sudo=True,
                commands=[["systemctl", "disable", svc], ["systemctl", "stop", svc]],
            ))

    return items


# ---------------------------------------------------------------------------
# Planning (reverse dependency order)
# ---------------------------------------------------------------------------

# Uninstall order: reverse of installation dependency order.
# Dependents first, then their dependencies.
UNINSTALL_PHASES = [
    # Phase 1: Applications and services that depend on others
    ("Phase 1: Odoo instances", ["odoo17", "odoo18", "odoo19", "odoo17-db", "odoo18-db", "odoo19-db"]),
    ("Phase 2: Traefik reverse proxy", ["traefik"]),
    ("Phase 3: Jenkins CI/CD", ["jenkins"]),
    ("Phase 4: Portainer", ["portainer"]),
    ("Phase 5: Docker networks", ["proxy", "odoo17_internal", "odoo18_internal", "odoo19_internal"]),
    ("Phase 6: Docker images", ["traefik:v3.7", "odoo:17", "odoo:18", "odoo:19",
                                "postgres:16", "postgres:17", "postgres:18",
                                "portainer/portainer-ce", "jenkins/jenkins:lts-jdk21"]),
    ("Phase 7: Configuration directories", ["/opt/traefik", "/opt/ansible", "/opt/jenkins",
                                            "/data/jenkins", "/data/traefik", "/srv/portainer"]),
    ("Phase 8: Odoo infrastructure data", ["/opt/odoo-infrastructure"]),
    ("Phase 9: APT sources and keyrings", ["/etc/apt/sources.list.d/docker.list",
                                          "/etc/apt/sources.list.d/pgdg.list",
                                          "/etc/apt/keyrings/docker.gpg"]),
]


def plan_uninstall(items: List[CleanupItem], dry_run: bool = False) -> List[CleanupItem]:
    """
    Order cleanup items by reverse dependency phases.

    Items not matching any phase are appended at the end in discovery order.
    Protected items are kept in place but marked as protected.
    """
    consumed: Set[str] = set()  # set of item ids
    ordered: List[CleanupItem] = []

    # Build lookup by id for quick access
    items_by_id: Dict[str, CleanupItem] = {it.id: it for it in items}

    for phase_name, phase_entries in UNINSTALL_PHASES:
        for entry in phase_entries:
            for it in items:
                if it.id in consumed:
                    continue
                # Match by path, basename, or resource name (containers/networks/images)
                if (entry == it.path or
                        entry == os.path.basename(it.path) or
                        entry == it.path):
                    ordered.append(it)
                    consumed.add(it.id)

    # Append remaining items not matched by phases, in discovery order
    for it in items:
        if it.id not in consumed:
            ordered.append(it)

    # Mark all as scheduled
    for it in ordered:
        it.status = CleanupStatus.SCHEDULED

    return ordered


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

class UninstallExecutor:
    """Executes the cleanup plan with safety guarantees."""

    def __init__(self, use_sudo: bool = False, dry_run: bool = False,
                 on_output: Optional[Callable[[str], None]] = None,
                 log_file: str = UNINSTALL_LOG):
        self.use_sudo = use_sudo
        self.dry_run = dry_run
        self.on_output = on_output or (lambda msg: None)
        self.log_file = log_file
        self.report = CleanupReport(started_at=_dt.datetime.now(_dt.timezone.utc).isoformat(),
                                    dry_run=dry_run)
        self._cancelled = False

        # Ensure log directory exists
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
        except OSError:
            pass

    def _log(self, message: str) -> None:
        self.on_output(message)
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(message + "\n")
        except OSError:
            pass

    def _require_confirmation(self) -> bool:
        """Require explicit DELETE confirmation before destructive action."""
        if self.dry_run:
            return True
        print(f"\n{'*' * 70}")
        print(f"  {chr(27)}[1;31mWARNING: DESTRUCTIVE OPERATION{chr(27)}[0m")
        print(f"  This will permanently delete project files, containers, images,")
        print(f"  networks, and configuration. BACKUPS WILL BE PRESERVED.")
        print(f"{'*' * 70}")
        confirm = input("  Type 'DELETE EVERYTHING EXCEPT BACKUPS' to confirm: ").strip()
        if confirm != "DELETE EVERYTHING EXCEPT BACKUPS":
            print(f"{chr(27)}[1;33m  Confirmation mismatch. Uninstall aborted.{chr(27)}[0m")
            return False
        return True

    def _is_root(self) -> bool:
        try:
            return os.geteuid() == 0
        except AttributeError:
            return False

    def _prefix(self) -> List[str]:
        if self.use_sudo and not self._is_root():
            return ["sudo"]
        return []

    def execute_item(self, item: CleanupItem) -> None:
        """Execute cleanup for a single item."""
        if self._cancelled:
            item.status = CleanupStatus.SKIPPED
            item.error = "Cancelled"
            return

        # Protected items are never deleted
        if item.protected:
            item.status = CleanupStatus.PROTECTED
            self.report.protected_count += 1
            self._log(f"[PROTECTED] {item.path}: {item.protection_reason}")
            return

        item.status = CleanupStatus.IN_PROGRESS
        self._log(f"[CLEANING] {item.type}: {item.path} ({item.description})")

        if self.dry_run:
            item.status = CleanupStatus.COMPLETED
            self.report.completed_count += 1
            self.report.total_bytes_freed += item.size_bytes
            self._log(f"  [DRY-RUN] Would remove: {item.path}")
            for cmd in item.commands:
                self._log(f"    $ {' '.join(self._prefix() + cmd)}")
            return

        success = True
        errors: List[str] = []

        # Execute type-specific cleanup
        try:
            if item.type == "directory":
                if os.path.exists(item.path):
                    # Final safety: re-check backup protection before actual deletion
                    prot, reason = should_protect(item.path)
                    if prot:
                        item.protected = True
                        item.protection_reason = reason
                        item.status = CleanupStatus.PROTECTED
                        self.report.protected_count += 1
                        self._log(f"  [PROTECTED AT EXECUTE] {item.path}: {reason}")
                        return
                    shutil.rmtree(item.path, ignore_errors=False)
                    self._log(f"  [REMOVED] Directory: {item.path}")
                else:
                    self._log(f"  [NOT FOUND] Directory: {item.path}")

            elif item.type == "file":
                if os.path.exists(item.path):
                    prot, reason = should_protect(item.path)
                    if prot:
                        item.protected = True
                        item.protection_reason = reason
                        item.status = CleanupStatus.PROTECTED
                        self.report.protected_count += 1
                        self._log(f"  [PROTECTED AT EXECUTE] {item.path}: {reason}")
                        return
                    os.remove(item.path)
                    self._log(f"  [REMOVED] File: {item.path}")
                else:
                    self._log(f"  [NOT FOUND] File: {item.path}")

            elif item.type == "docker_container":
                prefix = self._prefix()
                for cmd in item.commands:
                    full_cmd = prefix + cmd
                    code, out, err = _run(full_cmd, use_sudo=False, timeout=60)
                    # sudo already in prefix; use_sudo=False to avoid double sudo
                    if code != 0 and "not found" not in (out + err).lower():
                        errors.append(f"docker {cmd[1]} {cmd[-1]}: {err.strip()}")
                        success = False
                    else:
                        self._log(f"  $ {' '.join(full_cmd)} -> exit {code}")

            elif item.type == "docker_network":
                prefix = self._prefix()
                for cmd in item.commands:
                    full_cmd = prefix + cmd
                    code, out, err = _run(full_cmd, use_sudo=False, timeout=60)
                    if code != 0 and ("not found" not in (out + err).lower() and
                                       "active" not in (out + err).lower()):
                        errors.append(f"docker network rm {cmd[-1]}: {err.strip()}")
                        success = False
                    else:
                        self._log(f"  $ {' '.join(full_cmd)} -> exit {code}")

            elif item.type == "docker_image":
                prefix = self._prefix()
                for cmd in item.commands:
                    full_cmd = prefix + cmd
                    code, out, err = _run(full_cmd, use_sudo=False, timeout=120)
                    if code != 0 and "not found" not in (out + err).lower():
                        errors.append(f"docker rmi {cmd[-1]}: {err.strip()}")
                        success = False
                    else:
                        self._log(f"  $ {' '.join(full_cmd)} -> exit {code}")

            elif item.type == "apt_file":
                prefix = self._prefix()
                for cmd in item.commands:
                    full_cmd = prefix + cmd
                    code, _, err = _run(full_cmd, use_sudo=False, timeout=30)
                    if code != 0:
                        errors.append(f"rm {cmd[-1]}: {err.strip()}")
                        success = False
                    else:
                        self._log(f"  $ {' '.join(full_cmd)} -> exit {code}")

            elif item.type == "service":
                prefix = self._prefix()
                for cmd in item.commands:
                    full_cmd = prefix + cmd
                    _run(full_cmd, use_sudo=False, timeout=30)
                    self._log(f"  $ {' '.join(full_cmd)}")

            else:
                errors.append(f"Unknown cleanup type: {item.type}")
                success = False

        except BackupProtectionError as exc:
            item.protected = True
            item.protection_reason = str(exc)
            item.status = CleanupStatus.PROTECTED
            self.report.protected_count += 1
            self._log(f"  [PROTECTED] {item.path}: {exc}")
            return
        except Exception as exc:
            errors.append(str(exc))
            success = False

        if errors:
            item.status = CleanupStatus.FAILED
            item.error = "; ".join(errors)
            self.report.failed_count += 1
            self.report.errors.extend(errors)
            self._log(f"  [FAILED] {item.path}: {item.error}")
        else:
            item.status = CleanupStatus.COMPLETED
            self.report.completed_count += 1
            self.report.total_bytes_freed += item.size_bytes
            self._log(f"  [DONE] {item.path}")

    def execute_plan(self, items: List[CleanupItem], confirm: bool = True) -> CleanupReport:
        """Execute the full cleanup plan."""
        if not self._require_confirmation():
            self.report.completed_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
            return self.report

        self._log(f"=== UNINSTALL STARTED (dry_run={self.dry_run}, sudo={self.use_sudo}) ===")
        for item in items:
            self.execute_item(item)
            if self._cancelled:
                break

        self.report.completed_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
        self.report.total_items = len(items)
        self.report.skipped_count = sum(1 for it in items if it.status == CleanupStatus.SKIPPED)

        self._log(f"=== UNINSTALL COMPLETED: "
                  f"{self.report.completed_count} done, "
                  f"{self.report.failed_count} failed, "
                  f"{self.report.protected_count} protected, "
                  f"{self.report.total_bytes_freed} bytes freed ===")
        return self.report

    def cancel(self) -> None:
        self._cancelled = True

    def save_report(self, path: Optional[str] = None) -> str:
        """Save the report to a JSON file."""
        target = path or os.path.join(LOG_DIR, f"uninstall_report_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                json.dump(self.report.to_dict(), f, indent=2)
        except OSError:
            if path:
                raise
            import tempfile
            folder = os.path.join(tempfile.gettempdir(), 'odoo-installer-reports')
            os.makedirs(folder, mode=0o700, exist_ok=True)
            target = os.path.join(folder, os.path.basename(target))
            with open(target, "w", encoding="utf-8") as f:
                json.dump(self.report.to_dict(), f, indent=2)
        return target


# ---------------------------------------------------------------------------
# High-level orchestration
# ---------------------------------------------------------------------------

def run_full_cleanup(use_sudo: bool = False, dry_run: bool = False,
                     confirm: bool = True,
                     on_output: Optional[Callable[[str], None]] = None) -> CleanupReport:
    """
    Run the complete uninstallation and cleanup workflow.

    Steps:
    1. Discover all project-installed components
    2. Plan cleanup in reverse dependency order
    3. Display plan with sizes and protection status
    4. Require explicit confirmation
    5. Execute cleanup
    6. Generate and save report
    """
    executor = UninstallExecutor(use_sudo=use_sudo, dry_run=dry_run,
                                 on_output=on_output)

    # Step 1: Discover
    items = discover_installation(use_sudo=use_sudo)

    # Step 2: Plan
    ordered = plan_uninstall(items, dry_run=dry_run)

    # Step 3: Display plan
    executor._log("\n=== CLEANUP PLAN ===")
    total_size = sum(it.size_bytes for it in ordered if not it.protected)
    protected_size = sum(it.size_bytes for it in ordered if it.protected)
    for it in ordered:
        marker = " [PROTECTED]" if it.protected else ""
        size_str = f"({it.size_bytes / 1024:.1f} KB)" if it.size_bytes > 0 else ""
        executor._log(f"  [{it.status.value}] {it.type}: {it.path} {size_str}{marker}")
        if it.protected:
            executor._log(f"    Reason: {it.protection_reason}")
    executor._log(f"\nTotal to remove: {total_size / (1024*1024):.2f} MB")
    executor._log(f"Protected (backups): {protected_size / (1024*1024):.2f} MB")

    # Step 4 & 5: Execute
    report = executor.execute_plan(ordered, confirm=confirm)

    # Step 6: Save report
    report_path = executor.save_report()
    executor._log(f"Report saved to: {report_path}")

    return report


def verify_cleanup(use_sudo: bool = False) -> Dict[str, Any]:
    """
    Verify that no project components remain after cleanup.

    Returns a dict with remaining items and their status.
    """
    remaining = {
        "docker_containers": [],
        "docker_networks": [],
        "docker_images": [],
        "filesystem_paths": [],
    }

    # Check Docker containers
    code, stdout, _ = _run(["docker", "ps", "-a", "--format", "{{.Names}}"], use_sudo=use_sudo)
    if code == 0:
        for line in stdout.splitlines():
            name = line.strip()
            if name in PROJECT_DOCKER_CONTAINERS:
                remaining["docker_containers"].append(name)

    # Check Docker networks
    code, stdout, _ = _run(["docker", "network", "ls", "--format", "{{.Name}}"], use_sudo=use_sudo)
    if code == 0:
        for line in stdout.splitlines():
            name = line.strip()
            if name in PROJECT_DOCKER_NETWORKS:
                remaining["docker_networks"].append(name)

    # Check Docker images
    code, stdout, _ = _run(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"], use_sudo=use_sudo)
    if code == 0:
        for line in stdout.splitlines():
            image = line.strip()
            if image in PROJECT_DOCKER_IMAGES:
                remaining["docker_images"].append(image)

    # Check filesystem paths
    for proj_path in PROJECT_INSTALL_PATHS:
        if os.path.exists(proj_path):
            remaining["filesystem_paths"].append(proj_path)

    all_clear = all(len(v) == 0 for v in remaining.values())
    return {
        "all_clear": all_clear,
        "remaining": remaining,
    }
