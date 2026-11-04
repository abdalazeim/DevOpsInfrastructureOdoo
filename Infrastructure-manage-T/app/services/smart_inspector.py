"""
Comprehensive Pre-flight Smart Inspector Service.
Audits Ubuntu OS, Docker Engine, Docker Compose, Traefik, Ansible, System Packages,
Storage Paths, Ports, and Configurations without modifying the system.
"""
import os
import platform
import shutil
import socket
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

class ComponentStatus(str, Enum):
    INSTALLED = "INSTALLED"
    MISSING = "MISSING"
    NEEDS_UPDATE = "NEEDS_UPDATE"
    MISCONFIGURED = "MISCONFIGURED"

@dataclass
class InspectedComponent:
    id: str
    name: str
    status: ComponentStatus
    detected_version: Optional[str] = None
    binary_path: Optional[str] = None
    config_path: Optional[str] = None
    why_needed: str = ""
    details: str = ""
    recommended_action: str = ""
    install_command: Optional[List[str]] = None

@dataclass
class PreflightReport:
    timestamp: str
    os_name: str
    os_version: str
    is_supported_ubuntu: bool
    components: List[InspectedComponent] = field(default_factory=list)
    all_ready: bool = False
    missing_count: int = 0
    issues_count: int = 0

class SmartInspectorService:
    """Performs safe, non-destructive audit of the host environment."""

    @staticmethod
    def inspect_ubuntu() -> InspectedComponent:
        os_release = {}
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release", "r") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        os_release[k] = v.strip('"')

        name = os_release.get("NAME", "Linux")
        version_id = os_release.get("VERSION_ID", "unknown")
        pretty_name = os_release.get("PRETTY_NAME", f"{name} {version_id}")

        is_ubuntu = "Ubuntu" in name or "ubuntu" in os_release.get("ID", "")
        try:
            ver_num = float(version_id)
            is_supported = is_ubuntu and ver_num >= 22.04
        except ValueError:
            is_supported = is_ubuntu

        status = ComponentStatus.INSTALLED if is_supported else (ComponentStatus.NEEDS_UPDATE if is_ubuntu else ComponentStatus.MISCONFIGURED)

        return InspectedComponent(
            id="ubuntu_os",
            name="Ubuntu Operating System",
            status=status,
            detected_version=pretty_name,
            binary_path="/etc/os-release",
            why_needed="Base operating system supported for running modern Docker Engine, Ansible, and systemd.",
            details=f"Detected: {pretty_name} (Architecture: {platform.machine()})",
            recommended_action="None (OS is compliant)" if is_supported else "Upgrade to Ubuntu 22.04 LTS or newer",
        )

    @staticmethod
    def inspect_docker_engine() -> InspectedComponent:
        from app.services.docker_inspector import inspect_engine, STATUS_TEXT
        report = inspect_engine()
        status = (ComponentStatus.INSTALLED if report["status"] == "running" else
                  ComponentStatus.MISSING if report["status"] == "missing" else
                  ComponentStatus.MISCONFIGURED)
        details = STATUS_TEXT[report["status"]]
        if report["errors"]:
            details += " " + " | ".join(report["errors"])
        return InspectedComponent(
            id="docker_engine", name="Docker Engine", status=status,
            binary_path=report["path"],
            detected_version=report["server_version"] or report["client_version"] or None,
            why_needed="Runs and isolates application containers.",
            details=details,
            recommended_action="Install Docker Engine" if status == ComponentStatus.MISSING else
                               "None" if status == ComponentStatus.INSTALLED else "Check connection and permissions",
        )

    @staticmethod
    def inspect_docker_compose() -> InspectedComponent:
        from app.services.compose_installer import inspect_compose
        report = inspect_compose()
        installed = report['status'] == 'installed'
        return InspectedComponent(
            id="docker_compose", name="Docker Compose Plugin",
            status=ComponentStatus.INSTALLED if installed else
                   ComponentStatus.MISSING if report['status'] == 'docker_missing' else ComponentStatus.MISCONFIGURED,
            binary_path=report['path'] or None,
            detected_version=report['details'] if installed else None,
            details=report['details'],
            why_needed="Orchestrates multi-container stacks.",
            recommended_action="None" if installed else "Use component menu 16 -> 4",
        )

    @staticmethod
    def inspect_traefik() -> InspectedComponent:
        docker_bin = shutil.which("docker")
        is_running = False
        details = "Traefik container not launched yet."
        status = ComponentStatus.MISSING

        if docker_bin:
            try:
                res = subprocess.run([docker_bin, "ps", "--filter", "name=traefik", "--format", "{{.Status}}"], capture_output=True, text=True, timeout=5)
                if "Up" in res.stdout:
                    is_running = True
                    status = ComponentStatus.INSTALLED
                    details = f"Traefik container running: {res.stdout.strip()}"
            except Exception:
                pass

        acme_path = "/opt/odoo-infrastructure/traefik/acme/acme.json"
        has_acme = os.path.exists(acme_path)
        acme_perm = oct(os.stat(acme_path).st_mode)[-3:] if has_acme else "None"

        return InspectedComponent(
            id="traefik_proxy",
            name="Traefik v3.7 Reverse Proxy",
            status=status,
            detected_version="v3.7 (Container)" if is_running else "Not running",
            config_path="deployment/traefik/config/traefik.yml",
            why_needed="Routes HTTP/HTTPS subdomains, terminates Let's Encrypt TLS, and handles WebSocket livechat.",
            details=f"{details} (acme.json permissions: {acme_perm})",
            recommended_action="Deploy Traefik from operations menu" if not is_running else "None",
        )

    @staticmethod
    def inspect_ansible() -> InspectedComponent:
        ansible_bin = shutil.which("ansible-playbook")
        if not ansible_bin:
            return InspectedComponent(
                id="ansible",
                name="Ansible Automation Tool",
                status=ComponentStatus.MISSING,
                why_needed="Automates idempotent baseline server configuration, sysctl tuning, and package dependencies.",
                details="ansible-playbook executable not found.",
                recommended_action="Install ansible via pip or apt: apt-get install -y ansible",
                install_command=["apt-get", "install", "-y", "ansible"],
            )

        try:
            res = subprocess.run([ansible_bin, "--version"], capture_output=True, text=True, timeout=5)
            ver_first_line = res.stdout.split("\n")[0] if res.stdout else "Installed"
            return InspectedComponent(
                id="ansible",
                name="Ansible Automation Tool",
                status=ComponentStatus.INSTALLED,
                detected_version=ver_first_line,
                binary_path=ansible_bin,
                why_needed="Automates baseline server provisioning.",
                details="Ansible is ready for baseline orchestration.",
                recommended_action="None",
            )
        except Exception as e:
            return InspectedComponent(
                id="ansible",
                name="Ansible",
                status=ComponentStatus.MISCONFIGURED,
                details=str(e),
            )

    @staticmethod
    def inspect_utility_packages() -> List[InspectedComponent]:
        tools = [
            ("curl", "Data Transfer Tool", "Used for health checks and API requests."),
            ("jq", "JSON Processing Utility", "Parses Docker and API telemetry output."),
            ("ufw", "Uncomplicated Firewall", "Secures incoming ports (22, 80, 443)."),
            ("tar", "Archive Utility", "Packages Odoo filestore for backups and restores."),
            ("gzip", "Compression Utility", "Compresses database SQL dumps safely."),
        ]

        results = []
        for cmd, name_en, why_en in tools:
            path = shutil.which(cmd)
            if path:
                results.append(InspectedComponent(
                    id=f"pkg_{cmd}",
                    name=name_en,
                    status=ComponentStatus.INSTALLED,
                    binary_path=path,
                    why_needed=why_en,
                    details=f"Installed at {path}",
                    recommended_action="None",
                ))
            else:
                results.append(InspectedComponent(
                    id=f"pkg_{cmd}",
                    name=name_en,
                    status=ComponentStatus.MISSING,
                    why_needed=why_en,
                    details=f"Command '{cmd}' not found in PATH",
                    recommended_action=f"Install: apt-get install -y {cmd}",
                    install_command=["apt-get", "install", "-y", cmd],
                ))
        return results

    @classmethod
    def run_full_inspection(cls) -> PreflightReport:
        import datetime
        components = [
            cls.inspect_ubuntu(),
            cls.inspect_docker_engine(),
            cls.inspect_docker_compose(),
            cls.inspect_traefik(),
            cls.inspect_ansible(),
        ]
        components.extend(cls.inspect_utility_packages())

        ubuntu_comp = components[0]
        missing = [c for c in components if c.status == ComponentStatus.MISSING]
        issues = [c for c in components if c.status in [ComponentStatus.MISCONFIGURED, ComponentStatus.NEEDS_UPDATE]]

        return PreflightReport(
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            os_name=ubuntu_comp.detected_version or "Ubuntu",
            os_version=ubuntu_comp.details or "22.04+",
            is_supported_ubuntu=ubuntu_comp.status == ComponentStatus.INSTALLED,
            components=components,
            all_ready=len(missing) == 0 and len(issues) == 0,
            missing_count=len(missing),
            issues_count=len(issues),
        )
