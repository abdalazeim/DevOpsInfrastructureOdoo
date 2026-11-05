"""
Smart Inspector Service - Component Discovery with Status Detection.

Discovers all infrastructure components on the system, determines their
installation status, and provides recommendations for missing or failed
components.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from app.core.installation_status import (
    ComponentStatusRecord,
    InstallationStatus,
    STATUS_COLORS,
    STATUS_SYMBOLS,
)

# ANSI color codes for terminal output
CYAN = "\033[1;36m"
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
RED = "\033[1;31m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


@dataclass
class ComponentDiscovery:
    """Result of discovering a single component."""
    name: str
    category: str
    status: InstallationStatus
    version: Optional[str] = None
    binary_path: Optional[str] = None
    details: str = ""
    why_needed: str = ""
    recommended_action: str = ""
    install_command: Optional[List[str]] = None
    log_file: Optional[str] = None
    error: Optional[str] = None


class SmartInspectorService:
    """
    Discovers infrastructure components and determines their installation status.
    Provides actionable recommendations for each component.
    """

    # Component check definitions: (name, category, check_cmd, version_cmd, why_needed, recommended_action)
    COMPONENT_CHECKS = [
        ("python3", "Core System", ["bash", "-c", "python3 --version"], ["python3", "--version"],
         "Required for Ansible, Odoo, and system scripts",
         "Install python3 and python3-pip via apt"),
        ("git", "Core System", ["bash", "-c", "git --version"], ["git", "--version"],
         "Required for version control and deployment",
         "Install git via apt"),
        ("docker", "Container Runtime", ["bash", "-c", "docker --version"], ["docker", "--version"],
         "Required to run Odoo, Traefik, Jenkins containers",
         "Install Docker Engine from official repository"),
        ("docker-compose", "Container Runtime", ["bash", "-c", "docker compose version"], ["docker", "compose", "version"],
         "Required for multi-container orchestration",
         "Install docker-compose-plugin via apt"),
        ("ansible", "Automation Tools", ["bash", "-c", "ansible-playbook --version"], ["ansible-playbook", "--version"],
         "Required for automated configuration and deployment",
         "Install ansible via pip"),
        ("traefik", "Infrastructure Services", ["bash", "-c", "docker ps -a --filter name=traefik --format '{{.Names}}' | grep -q '^traefik$'"],
         ["docker", "inspect", "--format={{.Config.Image}}", "traefik"],
         "Reverse proxy and SSL termination for Odoo instances",
         "Deploy traefik:v3.7 container on proxy network"),
        ("postgresql", "Infrastructure Services", ["bash", "-c", "which psql || docker ps -a --filter name=odoo17-db --format '{{.Names}}' | grep -q ."],
         None,
         "Database backend for Odoo instances",
         "Install PostgreSQL or deploy postgres container"),
        ("jenkins", "CI/CD", ["bash", "-c", "docker ps -a --filter name=jenkins --format '{{.Names}}' | grep -q '^jenkins$'"],
         ["docker", "inspect", "--format={{.Config.Image}}", "jenkins"],
         "CI/CD pipeline for automated deployments",
         "Deploy jenkins/jenkins:lts-jdk21 container"),
        ("odoo17", "Application Deployment", ["bash", "-c", "docker ps -a --filter name=odoo17-instance1 --format '{{.Names}}' | grep -q ."],
         None,
         "Odoo 17 application instance (PostgreSQL 16)",
         "Deploy odoo:17.0 container"),
        ("odoo18", "Application Deployment", ["bash", "-c", "docker ps -a --filter name=odoo18-instance1 --format '{{.Names}}' | grep -q ."],
         None,
         "Odoo 18 application instance (PostgreSQL 17)",
         "Deploy odoo:18.0 container"),
        ("odoo19", "Application Deployment", ["bash", "-c", "docker ps -a --filter name=odoo19-instance1 --format '{{.Names}}' | grep -q ."],
         None,
         "Odoo 19 application instance (PostgreSQL 18)",
         "Deploy odoo:19.0 container"),
    ]

    def __init__(self):
        self.components: List[ComponentDiscovery] = []
        self.os_name: str = "Unknown"
        self.os_version: str = "Unknown"
        self.timestamp: str = datetime.now().isoformat()
        self.is_supported_ubuntu: bool = False

    def run_full_inspection(self) -> "SmartInspectorService":
        """Run complete system inspection and populate component list."""
        self._detect_os()
        self.components = []

        for name, category, check_cmd, version_cmd, why_needed, recommended_action in self.COMPONENT_CHECKS:
            discovery = self._inspect_component(
                name, category, check_cmd, version_cmd, why_needed, recommended_action
            )
            self.components.append(discovery)

        return self

    def _detect_os(self) -> None:
        """Detect operating system name and version."""
        try:
            import platform
            dist = platform.freedesktop_os_release() if hasattr(platform, 'freedesktop_os_release') else {}
            self.os_name = dist.get("PRETTY_NAME", platform.system())
            self.os_version = dist.get("VERSION_ID", "Unknown")
            self.is_supported_ubuntu = "Ubuntu" in self.os_name
        except Exception:
            self.os_name = platform.system() if "platform" in dir() else "Unknown"
            self.os_version = "Unknown"
            self.is_supported_ubuntu = False

    def _inspect_component(
        self,
        name: str,
        category: str,
        check_cmd: List[str],
        version_cmd: Optional[List[str]],
        why_needed: str,
        recommended_action: str,
    ) -> ComponentDiscovery:
        """Inspect a single component."""
        try:
            result = subprocess.run(
                check_cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                version = None
                binary_path = shutil.which(name.split("-")[0]) if name not in ("traefik", "jenkins", "odoo17", "odoo18", "odoo19") else None

                if version_cmd:
                    try:
                        vres = subprocess.run(
                            version_cmd,
                            capture_output=True,
                            text=True,
                            timeout=15,
                        )
                        if vres.returncode == 0:
                            version = vres.stdout.strip()
                    except Exception:
                        pass

                return ComponentDiscovery(
                    name=name,
                    category=category,
                    status=InstallationStatus.ALREADY_INSTALLED,
                    version=version,
                    binary_path=binary_path,
                    details=f"Installed and verified (version: {version or 'unknown'})",
                    why_needed=why_needed,
                    recommended_action="No action needed - already installed",
                    install_command=None,
                )
            else:
                return ComponentDiscovery(
                    name=name,
                    category=category,
                    status=InstallationStatus.READY_TO_INSTALL,
                    version=None,
                    binary_path=None,
                    details="Not installed",
                    why_needed=why_needed,
                    recommended_action=recommended_action,
                    install_command=None,
                )

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            return ComponentDiscovery(
                name=name,
                category=category,
                status=InstallationStatus.NOT_CHECKED,
                version=None,
                binary_path=None,
                details=f"Could not inspect: {exc}",
                why_needed=why_needed,
                recommended_action=recommended_action,
                install_command=None,
                error=str(exc),
            )

    def get_missing_components(self) -> List[ComponentDiscovery]:
        """Return components that are missing or not checked."""
        return [
            c for c in self.components
            if c.status in (InstallationStatus.READY_TO_INSTALL, InstallationStatus.NOT_CHECKED)
        ]

    def get_installed_components(self) -> List[ComponentDiscovery]:
        """Return components that are already installed."""
        return [
            c for c in self.components
            if c.status == InstallationStatus.ALREADY_INSTALLED
        ]

    def get_failed_components(self) -> List[ComponentDiscovery]:
        """Return components with errors."""
        return [
            c for c in self.components
            if c.status == InstallationStatus.FAILED
        ]

    def print_report(self) -> None:
        """Print a formatted inspection report to the terminal."""
        print(f"\n{BOLD}{CYAN}=============================================================================={RESET}")
        print(f"{BOLD}{CYAN}             SMART INFRASTRUCTURE INSPECTION REPORT                          {RESET}")
        print(f"{BOLD}{CYAN}=============================================================================={RESET}\n")

        print(f"{BOLD}Operating System:{RESET} {self.os_name} ({self.os_version})")
        print(f"{BOLD}Timestamp:{RESET}        {self.timestamp}")
        compliance = "Compliant (Ubuntu 22.04+)" if self.is_supported_ubuntu else "Warning: OS may not be fully supported"
        print(f"{BOLD}Compliance Status:{RESET} {compliance}\n")

        # Table header
        print("┌──────────────────────────────┬──────────────────┬──────────────────┬──────────────────────────────────┐")
        print("│ Component                    │ Status           │ Version          │ Details                        │")
        print("├──────────────────────────────┼──────────────────┼──────────────────┼──────────────────────────────────┤")

        for c in self.components:
            color = STATUS_COLORS.get(c.status, "")
            symbol = STATUS_SYMBOLS.get(c.status, "?")
            status_text = f"{symbol} {c.status.value}"
            comp_name = c.name[:30]
            ver = (c.version or "N/A")[:16]
            det = (c.details or "N/A")[:32]
            print(f"│ {comp_name:<30} │ {color}{status_text:<16}{RESET} │ {ver:<16} │ {det:<32} │")

        print("└──────────────────────────────┴──────────────────┴──────────────────┴──────────────────────────────────┘\n")

        missing = self.get_missing_components()
        if missing:
            print(f"{YELLOW}{BOLD}Missing Components ({len(missing)}):{RESET}")
            for mc in missing:
                print(f"  • {BOLD}{mc.name}{RESET}: {mc.why_needed}")
                print(f"    Action: {mc.recommended_action}")
        else:
            print(f"{GREEN}{BOLD}✔ All required components are installed and verified!{RESET}\n")

        installed = self.get_installed_components()
        if installed:
            print(f"{GREEN}Installed Components ({len(installed)}):{RESET}")
            for ic in installed:
                print(f"  ✓ {ic.name} ({ic.version or 'unknown version'})")
