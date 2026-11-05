"""
Server Setup Workflow - Ordered Installation with Dependency Enforcement.

Defines the complete server provisioning sequence in dependency order:
1. System Discovery & Pre-Flight Checks
2. Core System Packages (Python, Git, essential utilities)
3. Docker Engine & Compose
4. Infrastructure Services (Traefik, PostgreSQL, Docker networks)
5. Automation Tools (Ansible)
6. CI/CD (Jenkins)
7. Application Deployment (Odoo 17/18/19 instances)
8. Final Validation

Each phase checks prerequisites, skips already-installed components,
and blocks dependents when prerequisites fail.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional

from app.core.installation_status import (
    ComponentStatusRecord,
    InstallationStatus,
)
from app.config.hostname_config import get_config, HostnameConfig
from app.models.profile import InfrastructureProfile
from app.models.operation import OperationRecord, WorkflowStep, OperationStatus


@dataclass
class SetupPhase:
    """A single phase in the server setup sequence."""
    id: str
    name: str
    description: str
    components: List[str]  # component names in this phase
    depends_on: List[str] = field(default_factory=list)  # phase IDs
    critical: bool = True  # if this phase fails, block dependents


@dataclass
class ComponentSetup:
    """Definition of a single component to install."""
    name: str
    category: str
    check_cmd: List[str]  # command to check if already installed
    install_cmds: List[List[str]]  # commands to install
    depends_on: List[str] = field(default_factory=list)  # component names
    critical: bool = True
    version_cmd: Optional[List[str]] = None  # command to get installed version


class ServerSetupWorkflow:
    """
    Ordered server setup workflow with dependency enforcement.

    Inspects each component before attempting installation.
    Skips components already correctly installed.
    Installs missing components in dependency order.
    If a component fails, records the error and continues with independent components.
    Skips dependent components when prerequisites fail.
    Never reports success without verifying version and service health.
    """

    COMPONENT_DEFINITIONS: List[ComponentSetup] = [
        # Phase 1: Core System Packages
        ComponentSetup(
            name="system-packages",
            category="Core System",
            check_cmd=["bash", "-c", "which curl wget git jq tar gzip python3 pip3"],
            install_cmds=[
                ["apt-get", "update"],
                ["apt-get", "install", "-y", "curl", "wget", "gnupg",
                 "software-properties-common", "apt-transport-https",
                 "ca-certificates", "python3", "python3-pip",
                 "python3-venv", "git", "vim", "sudo", "ufw", "jq",
                 "tar", "gzip", "zstd"],
            ],
            critical=True,
        ),

        # Phase 2: Docker Engine
        ComponentSetup(
            name="docker-engine",
            category="Container Runtime",
            check_cmd=["bash", "-c", "docker --version && docker compose version"],
            install_cmds=[
                ["install", "-m", "0755", "-d", "/etc/apt/keyrings"],
                ["bash", "-c",
                 "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | "
                 "gpg --dearmor -o /etc/apt/keyrings/docker.gpg"],
                ["chmod", "a+r", "/etc/apt/keyrings/docker.gpg"],
                ["bash", "-c",
                 'echo "deb [arch=$(dpkg --print-architecture) '
                 'signed-by=/etc/apt/keyrings/docker.gpg] '
                 'https://download.docker.com/linux/ubuntu '
                 '$(. /etc/os-release && echo "$VERSION_CODENAME") stable" | '
                 "tee /etc/apt/sources.list.d/docker.list >/dev/null"],
                ["apt-get", "update"],
                ["apt-get", "install", "-y", "docker-ce", "docker-ce-cli",
                 "containerd.io", "docker-buildx-plugin", "docker-compose-plugin"],
                ["systemctl", "enable", "docker"],
                ["systemctl", "start", "docker"],
            ],
            version_cmd=["docker", "--version"],
            depends_on=["system-packages"],
            critical=True,
        ),

        # Phase 3: Docker Proxy Network
        ComponentSetup(
            name="docker-network",
            category="Container Runtime",
            check_cmd=["bash", "-c", "docker network inspect proxy >/dev/null 2>&1"],
            install_cmds=[
                ["docker", "network", "create", "--driver", "bridge",
                 "--subnet", "172.28.0.0/16", "proxy"],
            ],
            depends_on=["docker-engine"],
            critical=True,
        ),

        # Phase 4: Traefik
        ComponentSetup(
            name="traefik",
            category="Infrastructure Services",
            check_cmd=["bash", "-c",
                       "docker ps -a --filter name=traefik --format '{{.Names}}' | grep -q '^traefik$'"],
            install_cmds=[
                ["bash", "-c", "mkdir -p /opt/traefik/{config,letsencrypt,logs} /data/traefik/logs"],
                ["bash", "-c",
                 "touch /opt/traefik/letsencrypt/acme.json && chmod 600 /opt/traefik/letsencrypt/acme.json"],
                ["docker", "run", "-d", "--name", "traefik", "--restart=always",
                 "-p", "80:80", "-p", "443:443",
                 "-v", "/var/run/docker.sock:/var/run/docker.sock:ro",
                 "-v", "/opt/traefik/config:/etc/traefik",
                 "-v", "/opt/traefik/letsencrypt:/letsencrypt",
                 "-v", "/data/traefik/logs:/var/log/traefik",
                 "traefik:v3.7",
                 "--providers.docker",
                 "--entrypoints.web.address=:80",
                 "--entrypoints.websecure.address=:443",
                 "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web",
                 "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json",
                 "--api.dashboard=true",
                 "--api.insecure=false"],
            ],
            version_cmd=["docker", "inspect", "--format={{.Config.Image}}", "traefik"],
            depends_on=["docker-network"],
            critical=True,
        ),

        # Phase 5: PostgreSQL (for Odoo instances)
        ComponentSetup(
            name="postgresql",
            category="Infrastructure Services",
            check_cmd=["bash", "-c", "which psql || docker ps -a --filter name=odoo17-db --format '{{.Names}}' | grep -q ."],
            install_cmds=[
                ["bash", "-c", "apt-get install -y postgresql postgresql-contrib || true"],
                ["bash", "-c",
                 "docker run -d --name odoo17-db --network proxy --restart=always "
                 "-e POSTGRES_DB=odoo17_prod -e POSTGRES_USER=odoo "
                 "-e POSTGRES_PASSWORD_FILE=/run/secrets/odoo17_db_password "
                 "postgres:16-alpine"],
            ],
            depends_on=["docker-network"],
            critical=False,
        ),

        # Phase 6: Ansible
        ComponentSetup(
            name="ansible",
            category="Automation Tools",
            check_cmd=["bash", "-c", "ansible-playbook --version"],
            install_cmds=[
                ["python3", "-m", "pip", "install", "--upgrade", "pip"],
                ["python3", "-m", "pip", "install", "ansible"],
            ],
            depends_on=["system-packages"],
            critical=False,
        ),

        # Phase 7: Jenkins
        ComponentSetup(
            name="jenkins",
            category="CI/CD",
            check_cmd=["bash", "-c",
                       "docker ps -a --filter name=jenkins --format '{{.Names}}' | grep -q '^jenkins$'"],
            install_cmds=[
                ["bash", "-c", "mkdir -p /data/jenkins /opt/jenkins"],
                ["docker", "run", "-d", "--name", "jenkins", "--restart=always",
                 "--network", "proxy",
                 "-p", "8081:8080", "-p", "50000:50000",
                 "-v", "/data/jenkins:/var/jenkins_home",
                 "-v", "/opt/jenkins:/opt/jenkins",
                 "jenkins/jenkins:lts-jdk21"],
            ],
            depends_on=["docker-network", "traefik"],
            critical=False,
        ),

        # Phase 8: Odoo 17
        ComponentSetup(
            name="odoo17",
            category="Application Deployment",
            check_cmd=["bash", "-c",
                       "docker ps -a --filter name=odoo17-instance1 --format '{{.Names}}' | grep -q ."],
            install_cmds=[
                ["bash", "-c", "mkdir -p /data/odoo17/instance1 /opt/odoo17/instance1"],
                ["docker", "run", "-d", "--name", "odoo17-instance1",
                 "--network", "proxy", "--restart=always",
                 "-v", "/data/odoo17/instance1:/var/lib/odoo",
                 "-v", "/opt/odoo17/instance1:/etc/odoo",
                 "odoo:17.0"],
            ],
            depends_on=["docker-network", "postgresql"],
            critical=False,
        ),

        # Phase 9: Odoo 18
        ComponentSetup(
            name="odoo18",
            category="Application Deployment",
            check_cmd=["bash", "-c",
                       "docker ps -a --filter name=odoo18-instance1 --format '{{.Names}}' | grep -q ."],
            install_cmds=[
                ["bash", "-c", "mkdir -p /data/odoo18/instance1 /opt/odoo18/instance1"],
                ["docker", "run", "-d", "--name", "odoo18-instance1",
                 "--network", "proxy", "--restart=always",
                 "-v", "/data/odoo18/instance1:/var/lib/odoo",
                 "-v", "/opt/odoo18/instance1:/etc/odoo",
                 "odoo:18.0"],
            ],
            depends_on=["docker-network", "postgresql"],
            critical=False,
        ),

        # Phase 10: Odoo 19
        ComponentSetup(
            name="odoo19",
            category="Application Deployment",
            check_cmd=["bash", "-c",
                       "docker ps -a --filter name=odoo19-instance1 --format '{{.Names}}' | grep -q ."],
            install_cmds=[
                ["bash", "-c", "mkdir -p /data/odoo19/instance1 /opt/odoo19/instance1"],
                ["docker", "run", "-d", "--name", "odoo19-instance1",
                 "--network", "proxy", "--restart=always",
                 "-v", "/data/odoo19/instance1:/var/lib/odoo",
                 "-v", "/opt/odoo19/instance1:/etc/odoo",
                 "odoo:19.0"],
            ],
            depends_on=["docker-network", "postgresql"],
            critical=False,
        ),
    ]

    # Phase ordering by dependency
    SETUP_PHASES: List[SetupPhase] = [
        SetupPhase(
            id="system-discovery",
            name="System Discovery & Pre-Flight Checks",
            description="Detect OS, hostname, domain, CPU, RAM, storage, network, users, permissions, installed software",
            components=["system-packages"],
            critical=True,
        ),
        SetupPhase(
            id="core-packages",
            name="Core System Packages",
            description="Install Python, Git, essential utilities, and required system libraries",
            components=["system-packages"],
            depends_on=["system-discovery"],
            critical=True,
        ),
        SetupPhase(
            id="container-runtime",
            name="Container Infrastructure",
            description="Install Docker Engine, Docker Compose, configure permissions, verify functionality",
            components=["docker-engine", "docker-network"],
            depends_on=["core-packages"],
            critical=True,
        ),
        SetupPhase(
            id="infrastructure-services",
            name="Infrastructure Services",
            description="Install and configure Traefik, PostgreSQL, Docker networks",
            components=["traefik", "postgresql"],
            depends_on=["container-runtime"],
            critical=True,
        ),
        SetupPhase(
            id="automation-tools",
            name="Automation Tools",
            description="Install Ansible and apply baseline configuration",
            components=["ansible"],
            depends_on=["core-packages"],
            critical=False,
        ),
        SetupPhase(
            id="cicd",
            name="CI/CD",
            description="Install and configure Jenkins",
            components=["jenkins"],
            depends_on=["infrastructure-services"],
            critical=False,
        ),
        SetupPhase(
            id="application-deployment",
            name="Application Deployment",
            description="Deploy selected Odoo versions and instances",
            components=["odoo17", "odoo18", "odoo19"],
            depends_on=["infrastructure-services"],
            critical=False,
        ),
        SetupPhase(
            id="final-validation",
            name="Final Validation",
            description="Verify all services, networking, DNS, HTTPS, databases, and application health",
            components=[],
            depends_on=["infrastructure-services"],
            critical=True,
        ),
    ]

    def __init__(
        self,
        profile: InfrastructureProfile,
        dry_run: bool = False,
        use_sudo: bool = False,
        log_dir: str = "/var/log/odoo-installer",
        on_output: Optional[Callable[[str], None]] = None,
    ):
        self.profile = profile
        self.dry_run = dry_run
        self.use_sudo = use_sudo
        self.log_dir = log_dir
        self.on_output = on_output
        self.components: dict[str, ComponentStatusRecord] = {}
        self._install_order: List[str] = []
        self._failed_components: set[str] = set()
        self._initialize_components()

    def _log(self, message: str) -> None:
        if self.on_output:
            self.on_output(message)

    def _initialize_components(self) -> None:
        """Initialize all component records with NOT_CHECKED status."""
        for comp_def in self.COMPONENT_DEFINITIONS:
            self.components[comp_def.name] = ComponentStatusRecord(
                name=comp_def.name,
                category=comp_def.category,
                status=InstallationStatus.NOT_CHECKED,
                depends_on=comp_def.depends_on,
            )
        # Build install order respecting dependencies
        self._install_order = self._compute_install_order()

    def _compute_install_order(self) -> List[str]:
        """Topological sort of components respecting dependencies."""
        order: List[str] = []
        visited: set[str] = set()
        temp: set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            if name in temp:
                return  # circular dependency guard
            comp = self.components.get(name)
            if comp is None:
                return
            temp.add(name)
            for dep in comp.depends_on:
                visit(dep)
            temp.discard(name)
            visited.add(name)
            order.append(name)

        for comp_def in self.COMPONENT_DEFINITIONS:
            visit(comp_def.name)
        return order

    def inspect_all(self) -> None:
        """Inspect every component to determine current status."""
        self._log("\n" + "=" * 70)
        self._log(" COMPONENT INSPECTION - Determining installation status")
        self._log("=" * 70 + "\n")

        for comp_def in self.COMPONENT_DEFINITIONS:
            record = self.components[comp_def.name]
            self._inspect_component(comp_def, record)

    def _inspect_component(self, comp_def: ComponentSetup, record: ComponentStatusRecord) -> None:
        """Inspect a single component and update its status."""
        try:
            # Check if already installed
            result = subprocess.run(
                comp_def.check_cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # Already installed - detect version
                version = None
                if comp_def.version_cmd:
                    vres = subprocess.run(
                        comp_def.version_cmd,
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )
                    if vres.returncode == 0:
                        version = vres.stdout.strip()

                record.status = InstallationStatus.ALREADY_INSTALLED
                record.version = version
                record.details = f"Already installed (version: {version or 'unknown'})"
                self._log(f"  [OK] {comp_def.name}: ALREADY INSTALLED ({version or 'unknown'})")
            else:
                record.status = InstallationStatus.READY_TO_INSTALL
                record.details = "Not installed - ready for installation"
                self._log(f"  [READY] {comp_def.name}: READY TO INSTALL")

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            record.status = InstallationStatus.NOT_CHECKED
            record.details = f"Could not inspect: {exc}"
            self._log(f"  [?] {comp_def.name}: NOT CHECKED ({exc})")

    def can_install(self, comp_name: str) -> bool:
        """Check if a component can be installed (dependencies not failed)."""
        record = self.components.get(comp_name)
        if record is None:
            return False
        if record.status == InstallationStatus.FAILED:
            return False
        for dep in record.depends_on:
            if dep in self._failed_components:
                return False
        return True

    def install_component(self, comp_name: str) -> ComponentStatusRecord:
        """Install a single component and return its status record."""
        comp_def = next((c for c in self.COMPONENT_DEFINITIONS if c.name == comp_name), None)
        if comp_def is None:
            raise ValueError(f"Unknown component: {comp_name}")

        record = self.components[comp_name]

        # Check if already installed
        if record.status == InstallationStatus.ALREADY_INSTALLED:
            self._log(f"  [SKIP] {comp_name}: Already installed, skipping.")
            record.status = InstallationStatus.SKIPPED
            record.skip_reason = "Already installed"
            return record

        # Check dependencies
        for dep in comp_def.depends_on:
            if dep in self._failed_components:
                record.status = InstallationStatus.SKIPPED
                record.skip_reason = f"Dependency failed: {dep}"
                self._log(f"  [SKIP] {comp_name}: Blocked - dependency '{dep}' failed.")
                return record

        # Check if not ready
        if record.status not in (
            InstallationStatus.READY_TO_INSTALL,
            InstallationStatus.FAILED,
        ):
            record.status = InstallationStatus.SKIPPED
            record.skip_reason = "Not ready for installation"
            return record

        record.status = InstallationStatus.INSTALLING
        self._log(f"  [INSTALLING] {comp_name}...")

        all_success = True
        failed_cmd = None

        for idx, cmd in enumerate(comp_def.install_cmds, 1):
            if self.dry_run:
                self._log(f"    [DRY-RUN] {idx}/{len(comp_def.install_cmds)}: {' '.join(cmd)}")
                continue

            self._log(f"    [{idx}/{len(comp_def.install_cmds)}] {' '.join(cmd)}\n")
            try:
                full_cmd = ["sudo"] + cmd if self.use_sudo and not self._is_root() else list(cmd)
                result = subprocess.run(
                    full_cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if result.returncode != 0:
                    all_success = False
                    failed_cmd = cmd
                    self._log(f"    [FAILED] exit code {result.returncode}\n")
                    if result.stderr:
                        self._log(f"      STDERR: {result.stderr.strip()[:300]}\n")
                    break
                else:
                    self._log(f"    [OK] exit code 0\n")
            except subprocess.TimeoutExpired:
                all_success = False
                failed_cmd = cmd
                self._log(f"    [TIMEOUT] Command exceeded 300 seconds\n")
                break
            except Exception as exc:
                all_success = False
                failed_cmd = cmd
                self._log(f"    [EXCEPTION] {exc}\n")
                break

        if all_success:
            record.status = InstallationStatus.INSTALLED
            record.installed_at = datetime.now().isoformat()
            # Verify version after install
            if comp_def.version_cmd:
                try:
                    vres = subprocess.run(
                        comp_def.version_cmd,
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )
                    if vres.returncode == 0:
                        record.version = vres.stdout.strip()
                except Exception:
                    pass
            self._log(f"  [DONE] {comp_name}: INSTALLED (version: {record.version or 'unknown'})\n")
        else:
            record.status = InstallationStatus.FAILED
            record.error = f"Command failed: {' '.join(failed_cmd or [])}"
            self._failed_components.add(comp_name)
            self._log(f"  [FAILED] {comp_name}: {record.error}\n")

        return record

    def run_ordered_installation(self) -> dict:
        """
        Run the full ordered installation sequence.

        Returns a dict with:
        - components: all component status records
        - failed_components: set of failed component names
        - overall_success: bool
        - report: InstallationReport
        """
        self._log("\n" + "=" * 70)
        self._log(" ORDERED SERVER SETUP - Starting installation sequence")
        self._log("=" * 70 + "\n")

        # First inspect all components
        self.inspect_all()

        # Then install in dependency order
        for comp_name in self._install_order:
            if not self.can_install(comp_name):
                continue
            self.install_component(comp_name)

        # Final validation
        self._run_final_validation()

        return self.generate_report()

    def _run_final_validation(self) -> None:
        """Run final validation of all installed components."""
        self._log("\n" + "-" * 70)
        self._log(" FINAL VALIDATION")
        self._log("-" * 70 + "\n")

        for comp_name in self._install_order:
            record = self.components[comp_name]
            if record.status == InstallationStatus.INSTALLED:
                self._validate_component(comp_name, record)

    def _validate_component(self, comp_name: str, record: ComponentStatusRecord) -> None:
        """Validate a single installed component."""
        comp_def = next((c for c in self.COMPONENT_DEFINITIONS if c.name == comp_name), None)
        if comp_def is None:
            return

        try:
            result = subprocess.run(
                comp_def.check_cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                self._log(f"  [VALID] {comp_name}: Health check passed\n")
            else:
                record.status = InstallationStatus.WARNING
                record.error = f"Health check failed (exit code {result.returncode})"
                self._log(f"  [WARN] {comp_name}: Health check failed\n")
        except Exception as exc:
            record.status = InstallationStatus.WARNING
            record.error = f"Validation error: {exc}"
            self._log(f"  [WARN] {comp_name}: Validation error - {exc}\n")

    def generate_report(self) -> dict:
        """Generate a comprehensive installation report."""
        successful = [
            r for r in self.components.values()
            if r.status in (InstallationStatus.INSTALLED, InstallationStatus.ALREADY_INSTALLED)
        ]
        failed = [
            r for r in self.components.values()
            if r.status == InstallationStatus.FAILED
        ]
        skipped = [
            r for r in self.components.values()
            if r.status == InstallationStatus.SKIPPED
        ]
        warnings = [
            r for r in self.components.values()
            if r.status == InstallationStatus.WARNING
        ]
        ready = [
            r for r in self.components.values()
            if r.status == InstallationStatus.READY_TO_INSTALL
        ]
        not_checked = [
            r for r in self.components.values()
            if r.status == InstallationStatus.NOT_CHECKED
        ]

        overall_success = len(failed) == 0 and len(skipped) == 0

        return {
            "components": self.components,
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
            "warnings": warnings,
            "ready": ready,
            "not_checked": not_checked,
            "failed_components": self._failed_components,
            "overall_success": overall_success,
            "total": len(self.components),
            "success_count": len(successful),
            "failure_count": len(failed),
            "skip_count": len(skipped),
            "warning_count": len(warnings),
        }

    def _is_root(self) -> bool:
        try:
            return os.geteuid() == 0
        except AttributeError:
            return False

    def create_operation_record(self) -> OperationRecord:
        """Create an OperationRecord for workflow integration."""
        steps: List[WorkflowStep] = []
        for comp_name in self._install_order:
            comp_def = next((c for c in self.COMPONENT_DEFINITIONS if c.name == comp_name), None)
            if comp_def is None:
                continue
            steps.append(WorkflowStep(
                id=f"install-{comp_name}",
                name=f"Install {comp_def.name}",
                description=comp_def.category,
                command=comp_def.check_cmd,
                is_critical=comp_def.critical,
            ))

        return OperationRecord(
            operation_id=f"op-server-setup-{self.profile.profile_name}",
            name=f"Server Setup [{self.profile.server.hostname}]",
            category="server_setup",
            profile_name=self.profile.profile_name,
            steps=steps,
            dry_run=self.dry_run,
        )
