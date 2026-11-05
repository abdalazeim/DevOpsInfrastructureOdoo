"""
Command Notebook Module - Interactive terminal-based command library.

Provides viewing, editing, saving, searching, and copying commands ONLY.
Never executes commands through Shell, subprocess, Ansible, Docker, or Jenkins.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Repository root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
NOTEBOOK_DIR = os.path.join(PROJECT_ROOT, "data", "command_notebook")
LIBRARY_FILE = os.path.join(NOTEBOOK_DIR, "library.json")

# 18 command categories (stable keys for backward-compatible storage)
CATEGORIES: Dict[str, str] = {
    "ubuntu_system": "01. Ubuntu & System Preparation",
    "python_deps": "02. Python & Dependencies",
    "git_github": "03. Git & GitHub",
    "docker_engine": "04. Docker Engine",
    "docker_compose": "05. Docker Compose",
    "docker_networks": "06. Docker Networks",
    "traefik": "07. Traefik",
    "ansible": "08. Ansible",
    "jenkins": "09. Jenkins CI/CD",
    "postgresql": "10. PostgreSQL",
    "odoo17": "11. Odoo 17 Docker Commands",
    "odoo18": "12. Odoo 18 Docker Commands",
    "odoo19": "13. Odoo 19 Docker Commands",
    "django": "14. Django",
    "portainer": "15. Portainer",
    "backup_restore": "16. Backup & Restore",
    "ssl_security": "17. SSL & Security",
    "monitoring": "18. Monitoring & Troubleshooting",
}

# Risk taxonomy (user-facing classification) + backward-compatible legacy levels
RISK_LEVELS = ("safe", "moderate", "high", "destructive", "low", "medium", "critical")
RISK_CLASSIFICATIONS = ("SAFE", "MODERATE", "HIGH", "DESTRUCTIVE")
RISK_TO_LEGACY = {
    "SAFE": "low",
    "MODERATE": "medium",
    "HIGH": "high",
    "DESTRUCTIVE": "critical",
}
LEGACY_TO_RISK = {
    "low": "SAFE",
    "medium": "MODERATE",
    "high": "HIGH",
    "critical": "DESTRUCTIVE",
}

SOURCE_BUILTIN = "builtin"
SOURCE_USER = "user"
SOURCE_GENERATED = "generated"
SOURCE_IMPORTED = "imported"
PROTECTED_SOURCES = {SOURCE_BUILTIN, SOURCE_USER, SOURCE_IMPORTED}

ODOO_PG_DEFAULTS = {"17": "16", "18": "17", "19": "18"}
ODOO_PORT_DEFAULTS = {"17": 10017, "18": 10018, "19": 10019}
ODOO_LP_DEFAULTS = {"17": 20017, "18": 20018, "19": 20019}
SUPPORTED_RESTART_POLICIES = ("no", "on-failure", "on-failure:5", "always", "unless-stopped")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dir() -> None:
    os.makedirs(NOTEBOOK_DIR, exist_ok=True)


def _normalize_risk(value: Optional[str]) -> str:
    v = (value or "safe").strip().lower()
    if v in RISK_CLASSIFICATIONS:
        return v
    if v in LEGACY_TO_RISK:
        return LEGACY_TO_RISK[v]
    if v in RISK_LEVELS:
        return v
    return "SAFE"


def _legacy_risk(value: Optional[str]) -> str:
    v = _normalize_risk(value)
    return RISK_TO_LEGACY.get(v, "low")


def _command_fingerprint(cmd: Dict[str, Any]) -> str:
    payload = {
        "category": cmd.get("category", ""),
        "group": cmd.get("group", ""),
        "name": cmd.get("name", ""),
        "command": cmd.get("command", ""),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def _normalize_command(cmd: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a command record for backward compatibility and new metadata."""
    out = dict(cmd or {})
    now = _now_iso()
    out.setdefault("id", out.get("id") or f"cmd_{uuid.uuid4().hex[:12]}")
    out.setdefault("name", "Untitled command")
    out["title"] = out.get("title") or out["name"]
    out.setdefault("command", "")
    out.setdefault("description", "")
    cat = out.get("category") or "ubuntu_system"
    if cat not in CATEGORIES:
        cat = "ubuntu_system"
    out["category"] = cat
    risk = _normalize_risk(out.get("risk_classification") or out.get("risk_level"))
    out["risk_classification"] = risk
    out["risk_level"] = _legacy_risk(risk)
    source = (out.get("source") or SOURCE_USER).lower()
    if source not in {SOURCE_BUILTIN, SOURCE_USER, SOURCE_GENERATED, SOURCE_IMPORTED}:
        source = SOURCE_IMPORTED
    out["source"] = source
    out.setdefault("created_at", now)
    out.setdefault("modified_at", now)
    out.setdefault("odoo_version", None)
    out.setdefault("required_parameters", [])
    out.setdefault("group", "")
    out.setdefault("group_number", None)
    out.setdefault("generated_config", None)
    out.setdefault("generator", None)
    out.setdefault("user_modified", False)
    out.setdefault("original_command", None)
    out.setdefault("original_name", None)
    out.setdefault("original_description", None)
    out.setdefault("generated_key", out.get("generated_key") or "")
    return out


def _migrate_library(lib: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate/normalize library structure in memory."""
    if not isinstance(lib, dict):
        lib = _default_commands()
    lib.setdefault("version", "1.1")
    lib.setdefault("categories", {})
    lib.setdefault("commands", {})
    lib.setdefault("generated_configs", {})
    # Ensure category entries exist
    for cat_key, cat_name in CATEGORIES.items():
        cat = lib["categories"].setdefault(cat_key, {"name": cat_name, "commands": []})
        if "commands" not in cat or not isinstance(cat["commands"], list):
            cat["commands"] = []
        cat["name"] = cat_name
    # Normalize commands and rebuild category indexes deterministically
    normalized: Dict[str, Any] = {}
    for cmd_id, cmd in lib.get("commands", {}).items():
        if not isinstance(cmd, dict):
            continue
        cmd = _normalize_command(cmd)
        cid = str(cmd.get("id") or cmd_id)
        cmd["id"] = cid
        normalized[cid] = cmd
    lib["commands"] = normalized
    for cat in lib["categories"].values():
        cat["commands"] = []
    for cid, cmd in normalized.items():
        lib["categories"].setdefault(cmd["category"], {"name": CATEGORIES.get(cmd["category"], cmd["category"]), "commands": []})
        if cid not in lib["categories"][cmd["category"]]["commands"]:
            lib["categories"][cmd["category"]]["commands"].append(cid)
    return lib


def _default_commands() -> Dict[str, Any]:
    """Return the built-in default command library."""
    return _migrate_library({
        "version": "1.1",
        "categories": {
            cat_key: {"name": cat_name, "commands": []}
            for cat_key, cat_name in CATEGORIES.items()
        },
        "commands": {},
        "generated_configs": {},
    })


def load_library() -> Dict[str, Any]:
    """Load the command library from JSON. Creates default if missing."""
    _ensure_dir()
    if not os.path.exists(LIBRARY_FILE):
        lib = _default_commands()
        _seed_builtin_commands(lib)
        save_library(lib)
        return lib
    try:
        with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
            lib = json.load(f)
        if "version" not in lib or "categories" not in lib or "commands" not in lib:
            raise ValueError("Invalid library structure")
        lib = _migrate_library(lib)
        # If library has no commands (corrupt/partial), reseed builtins but keep generated/user where present.
        if not lib.get("commands"):
            _seed_builtin_commands(lib)
        return lib
    except (json.JSONDecodeError, ValueError, OSError):
        backup = _find_latest_backup()
        if backup:
            with open(backup, "r", encoding="utf-8") as f:
                return _migrate_library(json.load(f))
        lib = _default_commands()
        _seed_builtin_commands(lib)
        save_library(lib)
        return lib


def save_library(lib: Dict[str, Any]) -> None:
    """Save the command library to JSON with automatic backup."""
    _ensure_dir()
    # Create backup before overwriting
    if os.path.exists(LIBRARY_FILE):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(NOTEBOOK_DIR, f"library.backup_{ts}.json")
        shutil.copy2(LIBRARY_FILE, backup_file)
        # Keep only last 10 backups
        backups = sorted(
            [
                os.path.join(NOTEBOOK_DIR, f)
                for f in os.listdir(NOTEBOOK_DIR)
                if f.startswith("library.backup_") and f.endswith(".json")
            ]
        )
        for old in backups[:-10]:
            try:
                os.remove(old)
            except OSError:
                pass
    # Validate JSON serializable before writing
    json.dumps(lib)
    with open(LIBRARY_FILE, "w", encoding="utf-8") as f:
        json.dump(lib, f, indent=2, ensure_ascii=False)


def _find_latest_backup() -> Optional[str]:
    """Find the most recent backup file."""
    if not os.path.exists(NOTEBOOK_DIR):
        return None
    backups = [
        os.path.join(NOTEBOOK_DIR, f)
        for f in os.listdir(NOTEBOOK_DIR)
        if f.startswith("library.backup_") and f.endswith(".json")
    ]
    if not backups:
        return None
    return max(backups, key=os.path.getmtime)


def _seed_builtin_commands(lib: Dict[str, Any]) -> None:
    """Populate the library with built-in default commands."""
    builtins: Dict[str, List[Dict[str, Any]]] = {
        "ubuntu_system": [
            {
                "name": "Update system packages",
                "command": "sudo apt-get update && sudo apt-get upgrade -y",
                "description": "Update package list and upgrade all installed packages",
                "risk_level": "medium",
            },
            {
                "name": "Check system info",
                "command": "uname -a && cat /etc/os-release",
                "description": "Display kernel and OS release information",
                "risk_level": "low",
            },
            {
                "name": "Check disk usage",
                "command": "df -h",
                "description": "Show disk space usage for all mounted filesystems",
                "risk_level": "low",
            },
        ],
        "python_deps": [
            {
                "name": "Install Python pip package",
                "command": "pip3 install <package_name>",
                "description": "Install a Python package using pip",
                "risk_level": "low",
            },
            {
                "name": "List installed Python packages",
                "command": "pip3 list",
                "description": "List all installed Python packages",
                "risk_level": "low",
            },
            {
                "name": "Create Python virtual environment",
                "command": "python3 -m venv /path/to/venv",
                "description": "Create an isolated Python virtual environment",
                "risk_level": "low",
            },
        ],
        "git_github": [
            {
                "name": "Clone a Git repository",
                "command": "git clone https://github.com/user/repo.git",
                "description": "Clone a remote Git repository to local",
                "risk_level": "low",
            },
            {
                "name": "Check Git status",
                "command": "git status",
                "description": "Show the working tree status",
                "risk_level": "low",
            },
            {
                "name": "Commit changes",
                "command": "git add . && git commit -m 'commit message'",
                "description": "Stage all changes and create a commit",
                "risk_level": "medium",
            },
        ],
        "docker_engine": [
            {
                "name": "Check Docker version",
                "command": "docker --version",
                "description": "Show Docker engine version",
                "risk_level": "low",
            },
            {
                "name": "List running containers",
                "command": "docker ps",
                "description": "List currently running Docker containers",
                "risk_level": "low",
            },
            {
                "name": "List all containers",
                "command": "docker ps -a",
                "description": "List all Docker containers including stopped ones",
                "risk_level": "low",
            },
            {
                "name": "List Docker images",
                "command": "docker images",
                "description": "List all Docker images",
                "risk_level": "low",
            },
            {
                "name": "Stop a container",
                "command": "docker stop <container_id_or_name>",
                "description": "Stop a running Docker container",
                "risk_level": "high",
            },
            {
                "name": "Remove a container",
                "command": "docker rm <container_id_or_name>",
                "description": "Remove a stopped Docker container",
                "risk_level": "high",
            },
        ],
        "docker_compose": [
            {
                "name": "Start services with Compose",
                "command": "docker compose up -d",
                "description": "Start and run Docker containers in detached mode",
                "risk_level": "medium",
            },
            {
                "name": "Stop Compose services",
                "command": "docker compose down",
                "description": "Stop and remove containers, networks, and volumes",
                "risk_level": "high",
            },
            {
                "name": "View Compose logs",
                "command": "docker compose logs -f",
                "description": "Follow log output from Compose services",
                "risk_level": "low",
            },
            {
                "name": "Check Compose config",
                "command": "docker compose config",
                "description": "Validate and view the Compose configuration",
                "risk_level": "low",
            },
        ],
        "docker_networks": [
            {
                "name": "List Docker networks",
                "command": "docker network ls",
                "description": "List all Docker networks",
                "risk_level": "low",
            },
            {
                "name": "Inspect a network",
                "command": "docker network inspect <network_name>",
                "description": "Display detailed information about a network",
                "risk_level": "low",
            },
            {
                "name": "Create a bridge network",
                "command": "docker network create --driver bridge <network_name>",
                "description": "Create a new bridge network",
                "risk_level": "medium",
            },
            {
                "name": "Connect container to network",
                "command": "docker network connect <network_name> <container_name>",
                "description": "Connect a running container to a network",
                "risk_level": "medium",
            },
        ],
        "traefik": [
            {
                "name": "Check Traefik container status",
                "command": "docker ps --filter name=traefik",
                "description": "Check if Traefik container is running",
                "risk_level": "low",
            },
            {
                "name": "View Traefik logs",
                "command": "docker logs --tail 50 traefik",
                "description": "View recent Traefik container logs",
                "risk_level": "low",
            },
            {
                "name": "Restart Traefik",
                "command": "docker restart traefik",
                "description": "Restart the Traefik reverse proxy container",
                "risk_level": "high",
            },
        ],
        "ansible": [
            {
                "name": "Check Ansible version",
                "command": "ansible --version",
                "description": "Show Ansible version and configuration",
                "risk_level": "low",
            },
            {
                "name": "Run Ansible playbook",
                "command": "ansible-playbook -i inventory.ini playbook.yml",
                "description": "Execute an Ansible playbook",
                "risk_level": "high",
            },
            {
                "name": "Ansible syntax check",
                "command": "ansible-playbook --syntax-check playbook.yml",
                "description": "Validate playbook syntax without executing",
                "risk_level": "low",
            },
            {
                "name": "Ping all hosts",
                "command": "ansible all -m ping",
                "description": "Test connectivity to all managed hosts",
                "risk_level": "low",
            },
        ],
        "jenkins": [
            {
                "name": "Check Jenkins container status",
                "command": "docker ps --filter name=jenkins",
                "description": "Check if Jenkins container is running",
                "risk_level": "low",
            },
            {
                "name": "View Jenkins logs",
                "command": "docker logs --tail 50 jenkins",
                "description": "View recent Jenkins container logs",
                "risk_level": "low",
            },
            {
                "name": "Restart Jenkins",
                "command": "docker restart jenkins",
                "description": "Restart the Jenkins CI/CD container",
                "risk_level": "high",
            },
        ],
        "postgresql": [
            {
                "name": "Check PostgreSQL status",
                "command": "docker exec odoo17-db pg_isready -U odoo",
                "description": "Check if PostgreSQL is ready to accept connections",
                "risk_level": "low",
            },
            {
                "name": "List databases",
                "command": "docker exec -i odoo17-db psql -U odoo -c '\\l'",
                "description": "List all PostgreSQL databases",
                "risk_level": "low",
            },
            {
                "name": "Connect to database",
                "command": "docker exec -it odoo17-db psql -U odoo -d odoo17_prod",
                "description": "Open an interactive PostgreSQL session",
                "risk_level": "medium",
            },
            {
                "name": "Create database backup",
                "command": "docker exec -t odoo17-db pg_dumpall -U odoo > backup.sql",
                "description": "Create a full PostgreSQL database backup",
                "risk_level": "medium",
            },
        ],
        "odoo17": [
            {
                "name": "Check Odoo 17 container",
                "command": "docker ps --filter name=odoo17",
                "description": "Check Odoo 17 container status",
                "risk_level": "low",
            },
            {
                "name": "View Odoo 17 logs",
                "command": "docker logs --tail 50 odoo17-instance1",
                "description": "View recent Odoo 17 container logs",
                "risk_level": "low",
            },
            {
                "name": "Restart Odoo 17",
                "command": "docker restart odoo17-instance1",
                "description": "Restart the Odoo 17 container",
                "risk_level": "high",
            },
        ],
        "odoo18": [
            {
                "name": "Check Odoo 18 container",
                "command": "docker ps --filter name=odoo18",
                "description": "Check Odoo 18 container status",
                "risk_level": "low",
            },
            {
                "name": "View Odoo 18 logs",
                "command": "docker logs --tail 50 odoo18-instance1",
                "description": "View recent Odoo 18 container logs",
                "risk_level": "low",
            },
            {
                "name": "Restart Odoo 18",
                "command": "docker restart odoo18-instance1",
                "description": "Restart the Odoo 18 container",
                "risk_level": "high",
            },
        ],
        "odoo19": [
            {
                "name": "Check Odoo 19 container",
                "command": "docker ps --filter name=odoo19",
                "description": "Check Odoo 19 container status",
                "risk_level": "low",
            },
            {
                "name": "View Odoo 19 logs",
                "command": "docker logs --tail 50 odoo19-instance1",
                "description": "View recent Odoo 19 container logs",
                "risk_level": "low",
            },
            {
                "name": "Restart Odoo 19",
                "command": "docker restart odoo19-instance1",
                "description": "Restart the Odoo 19 container",
                "risk_level": "high",
            },
        ],
        "django": [
            {
                "name": "Check Django version",
                "command": "python3 -c \"import django; print(django.VERSION)\"",
                "description": "Show the installed Django version",
                "risk_level": "low",
            },
            {
                "name": "Create Django project",
                "command": "django-admin startproject <project_name>",
                "description": "Create a new Django project",
                "risk_level": "low",
            },
            {
                "name": "Run Django migrations",
                "command": "python3 manage.py migrate",
                "description": "Apply database migrations for a Django project",
                "risk_level": "medium",
            },
        ],
        "portainer": [
            {
                "name": "Check Portainer status",
                "command": "docker ps --filter name=portainer",
                "description": "Check if Portainer container is running",
                "risk_level": "low",
            },
            {
                "name": "View Portainer logs",
                "command": "docker logs --tail 50 portainer",
                "description": "View recent Portainer container logs",
                "risk_level": "low",
            },
        ],
        "backup_restore": [
            {
                "name": "Backup Odoo database",
                "command": "./automation/scripts/backup-db.sh 17 odoo17_prod 7",
                "description": "Backup Odoo 17 database with filestore",
                "risk_level": "medium",
            },
            {
                "name": "Restore Odoo database",
                "command": "./automation/scripts/restore-db.sh 17 dump.sql.gz odoo17_prod --force",
                "description": "Restore Odoo 17 database from backup",
                "risk_level": "high",
            },
            {
                "name": "Backup full instance",
                "command": "./deployment/Odoo-MultiVersion-Deployment/scripts/backup.sh instance1 odoo17 /data/backups",
                "description": "Backup complete Odoo instance data",
                "risk_level": "medium",
            },
        ],
        "ssl_security": [
            {
                "name": "Check SSL certificate",
                "command": "echo | openssl s_client -connect <domain>:443 2>/dev/null | openssl x509 -noout -dates",
                "description": "Check SSL certificate expiration dates",
                "risk_level": "low",
            },
            {
                "name": "Generate self-signed certificate",
                "command": "openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes",
                "description": "Generate a self-signed SSL certificate",
                "risk_level": "medium",
            },
        ],
        "monitoring": [
            {
                "name": "Check running processes",
                "command": "ps aux --sort=-%mem | head -20",
                "description": "Show top memory-consuming processes",
                "risk_level": "low",
            },
            {
                "name": "Check system load",
                "command": "uptime && top -bn1 | head -15",
                "description": "Show system load average and top processes",
                "risk_level": "low",
            },
            {
                "name": "Check listening ports",
                "command": "ss -tuln",
                "description": "Show all listening network ports",
                "risk_level": "low",
            },
        ],
    }

    for cat_key, cat_cmds in builtins.items():
        if cat_key not in lib["categories"]:
            lib["categories"][cat_key] = {"name": CATEGORIES.get(cat_key, cat_key), "commands": []}
        for cmd in cat_cmds:
            cmd_id = f"builtin_{cat_key}_{len(lib['commands'])}"
            lib["commands"][cmd_id] = {
                "id": cmd_id,
                "name": cmd["name"],
                "command": cmd["command"],
                "description": cmd["description"],
                "category": cat_key,
                "risk_level": cmd["risk_level"],
                "source": "builtin",
                "created_at": _now_iso(),
                "modified_at": _now_iso(),
            }
            lib["categories"][cat_key]["commands"].append(cmd_id)


class CommandNotebook:
    """Command Notebook - manages commands in JSON storage.

    Supports viewing, editing, saving, searching, copying commands.
    Never executes commands.
    """

    def __init__(self):
        self.library: Dict[str, Any] = load_library()

    def reload(self) -> None:
        """Reload library from disk."""
        self.library = load_library()

    def get_categories(self) -> List[Dict[str, str]]:
        """Return list of all categories with command counts."""
        result = []
        for cat_key, cat_name in CATEGORIES.items():
            cat_data = self.library.get("categories", {}).get(cat_key, {})
            cmd_ids = cat_data.get("commands", [])
            result.append({
                "key": cat_key,
                "name": cat_name,
                "count": len(cmd_ids),
            })
        return result

    def get_commands_by_category(self, cat_key: str) -> List[Dict[str, Any]]:
        """Return commands for a category, sorted by name."""
        cat_data = self.library.get("categories", {}).get(cat_key, {})
        cmd_ids = cat_data.get("commands", [])
        commands = []
        for idx, cmd_id in enumerate(cmd_ids, 1):
            cmd = self.library.get("commands", {}).get(cmd_id)
            if cmd:
                cmd_copy = dict(cmd)
                cmd_copy["display_number"] = idx
                commands.append(cmd_copy)
        commands.sort(key=lambda c: c["name"].lower())
        return commands

    def get_command(self, cmd_id: str) -> Optional[Dict[str, Any]]:
        """Get a single command by ID."""
        return self.library.get("commands", {}).get(cmd_id)

    def add_command(
        self,
        name: str,
        command: str,
        category: str,
        description: str = "",
        risk_level: str = "low",
        *,
        source: str = SOURCE_USER,
        title: Optional[str] = None,
        risk_classification: Optional[str] = None,
        odoo_version: Optional[str] = None,
        required_parameters: Optional[List[str]] = None,
        group: str = "",
        group_number: Optional[int] = None,
        generated_config: Optional[Dict[str, Any]] = None,
        generator: Optional[str] = None,
        generated_key: str = "",
        user_modified: bool = False,
        original_command: Optional[str] = None,
    ) -> str:
        """Add a new command. Returns the new command ID."""
        if category not in CATEGORIES:
            raise ValueError(f"Unknown category: {category}")
        risk_class = _normalize_risk(risk_classification or risk_level)
        cmd_id = f"{source}_{uuid.uuid4().hex[:12]}" if source != SOURCE_BUILTIN else f"builtin_{category}_{uuid.uuid4().hex[:8]}"
        now = _now_iso()
        record = _normalize_command({
            "id": cmd_id,
            "name": name,
            "title": title or name,
            "command": command,
            "description": description,
            "category": category,
            "risk_level": _legacy_risk(risk_class),
            "risk_classification": risk_class,
            "source": source,
            "odoo_version": str(odoo_version) if odoo_version else None,
            "required_parameters": list(required_parameters or []),
            "group": group,
            "group_number": group_number,
            "generated_config": generated_config,
            "generator": generator,
            "generated_key": generated_key,
            "user_modified": user_modified,
            "original_command": original_command,
            "created_at": now,
            "modified_at": now,
        })
        self.library.setdefault("commands", {})[cmd_id] = record
        self.library.setdefault("categories", {}).setdefault(category, {}).setdefault("commands", []).append(cmd_id)
        save_library(self.library)
        return cmd_id

    def update_command(
        self,
        cmd_id: str,
        name: Optional[str] = None,
        command: Optional[str] = None,
        category: Optional[str] = None,
        description: Optional[str] = None,
        risk_level: Optional[str] = None,
        *,
        title: Optional[str] = None,
        risk_classification: Optional[str] = None,
        odoo_version: Optional[str] = None,
        required_parameters: Optional[List[str]] = None,
        mark_user_modified: bool = True,
    ) -> None:
        """Update an existing command. Raises KeyError if not found."""
        commands = self.library.setdefault("commands", {})
        if cmd_id not in commands:
            raise KeyError(f"Command not found: {cmd_id}")
        cmd = _normalize_command(commands[cmd_id])
        if command is not None and command != cmd.get("command"):
            if cmd.get("original_command") is None:
                cmd["original_command"] = cmd.get("command")
                cmd["original_name"] = cmd.get("name")
                cmd["original_description"] = cmd.get("description")
            cmd["command"] = command
            if mark_user_modified and cmd.get("source") in {SOURCE_GENERATED, SOURCE_BUILTIN}:
                cmd["user_modified"] = True
                if cmd.get("source") == SOURCE_GENERATED:
                    cmd["source"] = SOURCE_USER  # preserve user edits across regeneration
        if name is not None:
            cmd["name"] = name
            cmd["title"] = title or name
        if title is not None:
            cmd["title"] = title
        if category is not None:
            if category not in CATEGORIES:
                raise ValueError(f"Unknown category: {category}")
            old_cat = cmd.get("category")
            if old_cat:
                old_cmds = self.library.get("categories", {}).get(old_cat, {}).get("commands", [])
                if cmd_id in old_cmds:
                    old_cmds.remove(cmd_id)
            cmd["category"] = category
            self.library.setdefault("categories", {}).setdefault(category, {}).setdefault("commands", []).append(cmd_id)
        if description is not None:
            cmd["description"] = description
        if risk_level is not None or risk_classification is not None:
            risk_class = _normalize_risk(risk_classification or risk_level)
            cmd["risk_classification"] = risk_class
            cmd["risk_level"] = _legacy_risk(risk_class)
        if odoo_version is not None:
            cmd["odoo_version"] = str(odoo_version) if odoo_version else None
        if required_parameters is not None:
            cmd["required_parameters"] = list(required_parameters)
        cmd["modified_at"] = _now_iso()
        commands[cmd_id] = _normalize_command(cmd)
        save_library(self.library)

    def restore_original_command(self, cmd_id: str) -> None:
        """Restore a command's original generated/builtin text when available."""
        commands = self.library.setdefault("commands", {})
        if cmd_id not in commands:
            raise KeyError(f"Command not found: {cmd_id}")
        cmd = _normalize_command(commands[cmd_id])
        if cmd.get("original_command") is not None:
            cmd["command"] = cmd["original_command"]
        if cmd.get("original_name") is not None:
            cmd["name"] = cmd["original_name"]
            cmd["title"] = cmd["original_name"]
        if cmd.get("original_description") is not None:
            cmd["description"] = cmd["original_description"]
        cmd["user_modified"] = False
        if cmd.get("generator") == "odoo_docker_installation":
            cmd["source"] = SOURCE_GENERATED
        cmd["modified_at"] = _now_iso()
        commands[cmd_id] = cmd
        save_library(self.library)

    def delete_command(self, cmd_id: str, *, confirm_builtin: bool = False) -> None:
        """Delete a command. Built-ins require explicit confirmation flag in non-UI contexts."""
        commands = self.library.get("commands", {})
        if cmd_id not in commands:
            raise KeyError(f"Command not found: {cmd_id}")
        cmd = _normalize_command(commands[cmd_id])
        if cmd.get("source") == SOURCE_BUILTIN and not confirm_builtin:
            raise PermissionError("Deleting a built-in command requires explicit confirmation")
        cat_key = cmd.get("category")
        if cat_key:
            cat_cmds = self.library.get("categories", {}).get(cat_key, {}).get("commands", [])
            if cmd_id in cat_cmds:
                cat_cmds.remove(cmd_id)
        del commands[cmd_id]
        save_library(self.library)

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search commands by name, category, command text, group, or Odoo version."""
        query_lower = (query or "").lower()
        results = []
        for cmd_id, cmd in self.library.get("commands", {}).items():
            cmd = _normalize_command(cmd)
            hay = " ".join([
                str(cmd.get("name", "")),
                str(cmd.get("title", "")),
                str(cmd.get("command", "")),
                str(cmd.get("description", "")),
                str(cmd.get("group", "")),
                str(cmd.get("odoo_version", "")),
                CATEGORIES.get(cmd.get("category", ""), ""),
            ]).lower()
            if query_lower in hay:
                cmd_copy = dict(cmd)
                cmd_copy["category_name"] = CATEGORIES.get(cmd.get("category", ""), cmd.get("category", ""))
                results.append(cmd_copy)
        results.sort(key=lambda c: (c.get("category_name", ""), str(c.get("group_number") or 9999), c["name"].lower()))
        return results

    def export_library(self, export_path: str) -> None:
        """Export the library to a JSON file."""
        lib = _migrate_library(copy.deepcopy(self.library))
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(lib, f, indent=2, ensure_ascii=False)

    def import_library(self, import_path: str, merge: bool = True) -> Dict[str, Any]:
        """Import a library from a JSON file. Returns summary stats."""
        with open(import_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "version" not in data or "commands" not in data:
            raise ValueError("Invalid library file format")
        imported = 0
        skipped = 0
        for cmd_id, cmd in data.get("commands", {}).items():
            if not isinstance(cmd, dict):
                skipped += 1
                continue
            if not merge and cmd_id in self.library.get("commands", {}):
                skipped += 1
                continue
            cmd = _normalize_command(cmd)
            new_id = str(cmd_id)
            if merge and new_id in self.library.get("commands", {}):
                new_id = f"imported_{uuid.uuid4().hex[:8]}_{new_id}"
            cmd["id"] = new_id
            if cmd.get("source") == SOURCE_BUILTIN:
                cmd["source"] = SOURCE_IMPORTED
            self.library.setdefault("commands", {})[new_id] = _normalize_command(cmd)
            cat_key = cmd.get("category", "ubuntu_system")
            if cat_key not in CATEGORIES:
                cat_key = "ubuntu_system"
                self.library["commands"][new_id]["category"] = cat_key
            self.library.setdefault("categories", {}).setdefault(cat_key, {}).setdefault("commands", []).append(new_id)
            imported += 1
        if "generated_configs" in data and isinstance(data["generated_configs"], dict):
            self.library.setdefault("generated_configs", {}).update(data["generated_configs"])
        self.library = _migrate_library(self.library)
        save_library(self.library)
        return {"imported": imported, "skipped": skipped}

    def reset_to_builtin(self) -> None:
        """Reset library to built-in defaults (user/generated commands are lost)."""
        lib = _default_commands()
        _seed_builtin_commands(lib)
        self.library = lib
        save_library(self.library)

    def upsert_generated_commands(
        self,
        generated: List[Dict[str, Any]],
        config_metadata: Dict[str, Any],
        *,
        overwrite_generated: bool = True,
    ) -> Dict[str, Any]:
        """Insert or update generated commands while preserving user-modified records."""
        stats = {"added": 0, "updated": 0, "kept_user_modified": 0}
        lib = _migrate_library(self.library)
        commands = lib.setdefault("commands", {})
        by_key: Dict[str, str] = {}
        for cid, cmd in commands.items():
            key = cmd.get("generated_key")
            if key and cmd.get("odoo_version") == str(config_metadata.get("odoo_version")):
                by_key[str(key)] = cid
        for g in generated:
            g = _normalize_command(g)
            g["odoo_version"] = str(config_metadata.get("odoo_version"))
            g["generated_config"] = config_metadata
            key = g.get("generated_key") or _command_fingerprint(g)
            g["generated_key"] = key
            existing_id = by_key.get(key)
            if existing_id and existing_id in commands:
                existing = _normalize_command(commands[existing_id])
                if existing.get("user_modified") or existing.get("source") in {SOURCE_USER, SOURCE_IMPORTED}:
                    stats["kept_user_modified"] += 1
                    continue
                if not overwrite_generated:
                    continue
                g["id"] = existing_id
                g["created_at"] = existing.get("created_at", g.get("created_at"))
                if existing.get("command") != g.get("command"):
                    g["original_command"] = existing.get("original_command") or existing.get("command")
                commands[existing_id] = g
                stats["updated"] += 1
            else:
                new_id = self.add_command.__func__ and None  # placeholder to satisfy linters in odd contexts
                cid = f"generated_{uuid.uuid4().hex[:12]}"
                g["id"] = cid
                commands[cid] = g
                cat = g["category"]
                lib.setdefault("categories", {}).setdefault(cat, {}).setdefault("commands", []).append(cid)
                stats["added"] += 1
        sig = hashlib.sha256(json.dumps(config_metadata, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
        lib.setdefault("generated_configs", {})[f"odoo{config_metadata.get('odoo_version')}"] = {
            "config": config_metadata,
            "signature": sig,
            "updated_at": _now_iso(),
        }
        self.library = _migrate_library(lib)
        save_library(self.library)
        return stats

    def list_generated_diffs(self, generated: List[Dict[str, Any]], config_metadata: Dict[str, Any]) -> List[Dict[str, str]]:
        """Return diffs for generated commands that would change existing non-user-modified commands."""
        diffs: List[Dict[str, str]] = []
        current = {c.get("generated_key"): _normalize_command(c) for c in self.library.get("commands", {}).values() if c.get("odoo_version") == str(config_metadata.get("odoo_version"))}
        for g in generated:
            g = _normalize_command(g)
            key = g.get("generated_key") or _command_fingerprint(g)
            ex = current.get(key)
            if not ex or ex.get("user_modified"):
                continue
            if ex.get("command") != g.get("command"):
                import difflib
                diff = "".join(difflib.unified_diff(
                    (ex.get("command") or "").splitlines(keepends=True),
                    (g.get("command") or "").splitlines(keepends=True),
                    fromfile=f"saved/{ex.get('name')}",
                    tofile=f"generated/{g.get('name')}",
                ))
                diffs.append({"id": ex.get("id", ""), "name": ex.get("name", ""), "diff": diff})
        return diffs

    def get_builtin_command_ids(self) -> set:
        """Return set of command IDs that are built-in."""
        return {
            cmd_id for cmd_id, cmd in self.library.get("commands", {}).items()
            if _normalize_command(cmd).get("source") == SOURCE_BUILTIN
        }

    def get_user_command_ids(self) -> set:
        """Return set of command IDs that are user-created or imported."""
        return {
            cmd_id for cmd_id, cmd in self.library.get("commands", {}).items()
            if _normalize_command(cmd).get("source") != SOURCE_BUILTIN
        }

    def count(self) -> int:
        """Return total command count."""
        return len(self.library.get("commands", {}))

    def get_risk_label(self, cmd: Dict[str, Any]) -> str:
        return _normalize_risk(cmd.get("risk_classification") or cmd.get("risk_level"))
