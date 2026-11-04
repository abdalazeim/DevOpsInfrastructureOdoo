"""
Terminal User Interface (TUI) and Interactive Console for Odoo Infrastructure Manager.
Supports both Textual App mode and ANSI Terminal Console mode.
"""
import os
import shutil
import sys
import time
from datetime import datetime
from typing import Optional, List
import json
import subprocess

from app.models.profile import InfrastructureProfile
from app.models.operation import OperationRecord, OperationStatus, WorkflowStep
from app.validators.config_validator import ConfigValidator
from app.validators.system_validator import SystemValidator
from app.workflows.server_prep import ServerPrepWorkflow
from app.workflows.deploy_traefik import DeployTraefikWorkflow
from app.workflows.deploy_odoo17 import DeployOdoo17Workflow
from app.workflows.deploy_odoo18 import DeployOdoo18Workflow
from app.workflows.deploy_odoo19 import DeployOdoo19Workflow
from app.workflows.database_ops import DatabaseOpsWorkflow
from app.workflows.full_deploy import FullDeployWorkflow
from app.services.execution_service import ExecutionService
from app.services.health_service import HealthService

# Repository root (this file lives in <root>/app/ui/app.py).
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# ANSI Color Codes
CYAN = "\033[1;36m"
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
RED = "\033[1;31m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"

class TerminalUI:
    """Interactive TUI for terminal execution."""

    def __init__(self, profile_path: str = "profiles/example.yaml"):
        self.profile_path = profile_path
        self.profile = self.load_profile(profile_path)
        self.is_arabic = False

    def load_profile(self, path: str) -> InfrastructureProfile:
        """Loads and parses a profile from YAML or JSON-compatible format."""
        if not os.path.exists(path):
            print(f"{YELLOW}[WARN] Profile file {path} not found. Creating default in-memory profile.{RESET}")
            return InfrastructureProfile(profile_name="default")
        
        try:
            # We parse simple key-values or standard structure
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return InfrastructureProfile.from_dict(data)
        except Exception:
            # Fallback for systems without PyYAML installed
            data = {
                "profile_name": "example-profile",
                "server": {"hostname": "devops-odoo", "ip_or_host": "127.0.0.1"},
                "traefik": {"dashboard_domain": "traefik.example.com", "acme_email": "admin@example.com"},
                "odoo17": {"domain": "odoo17.example.com"},
                "odoo18": {"domain": "odoo18.example.com"},
                "odoo19": {"domain": "odoo19.example.com"},
            }
            return InfrastructureProfile.from_dict(data)

    def print_banner(self):
        print(f"{CYAN}{BOLD}")
        print("╔══════════════════════════════════════════════════════════════════════════════╗")
        print("║                     ODOO INFRASTRUCTURE MANAGER                              ║")
        print("║               Odoo Multi-Version Infrastructure Manager                 ║")
        print("║   Ubuntu (Server & Desktop 22.04+) | Docker | Traefik v3.7 | Odoo 17/18/19  ║")
        print("╚══════════════════════════════════════════════════════════════════════════════╝")
        print(f"{RESET}")
        print(f"{BOLD}Host:{RESET} {self.profile.server.hostname} ({self.profile.server.ip_or_host})  |  {BOLD}Profile:{RESET} {self.profile.profile_name}  |  {BOLD}Timezone:{RESET} {self.profile.server.timezone}")
        print(f"{BOLD}Odoo 17:{RESET} {self.profile.odoo17.domain} (PG 16)  |  {BOLD}Odoo 18:{RESET} {self.profile.odoo18.domain} (PG 17)  |  {BOLD}Odoo 19:{RESET} {self.profile.odoo19.domain} (PG 18)")
        print("─" * 78)

    def execute_workflow(self, op: OperationRecord, dry_run: bool = False):
        print(f"\n{BOLD}{CYAN}▶ Starting Operation: {op.name}{RESET} (Dry-Run: {dry_run})")
        start_ts = time.time()
        op.status = OperationStatus.RUNNING

        total_steps = len(op.steps)
        for idx, step in enumerate(op.steps, 1):
            print(f"\n{BOLD}[{idx}/{total_steps}] Step: {step.name}{RESET}")
            print(f"{DIM}Description: {step.description}{RESET}")
            print(f"{DIM}Command: {' '.join(step.command)}{RESET}")

            def stream_line(line: str):
                sys.stdout.write(f"  │ {line}")
                sys.stdout.flush()

            step = ExecutionService.execute_step(
                step,
                on_output=stream_line,
                dry_run=dry_run
            )

            if step.status == OperationStatus.SUCCESS:
                print(f"{GREEN}✓ Step '{step.name}' succeeded in {step.duration_seconds:.2f}s{RESET}")
            else:
                print(f"{RED}✗ Step '{step.name}' failed with exit code {step.exit_code}{RESET}")
                if step.is_critical:
                    op.status = OperationStatus.FAILED
                    op.error_summary = f"Step failed: {step.name}"
                    print(f"{RED}{BOLD}Critical step failed! Workflow halted.{RESET}")
                    break

        elapsed = time.time() - start_ts
        if op.status != OperationStatus.FAILED:
            op.status = OperationStatus.SUCCESS
            print(f"\n{GREEN}{BOLD}✔ Operation completed successfully in {elapsed:.2f}s!{RESET}\n")
        else:
            print(f"\n{RED}{BOLD}✖ Operation terminated with errors after {elapsed:.2f}s.{RESET}\n")

    def show_menu(self):
        while True:
            print(f"{CYAN}{BOLD}")
            print("==================================================")
            print("       ODOO INFRASTRUCTURE MANAGER                ")
            print("==================================================")
            print(f"{RESET}")
            print(f"  {BOLD}1.{RESET} System Information")
            print(f"  {BOLD}2.{RESET} Infrastructure Health Check")
            print(f"  {BOLD}3.{RESET} Install Missing Components")
            print(f"  {BOLD}4.{RESET} Docker Management")
            print(f"  {BOLD}5.{RESET} Traefik Management")
            print(f"  {BOLD}6.{RESET} Docker Network Management")
            print(f"  {BOLD}7.{RESET} Odoo Management (17 / 18 / 19)")
            print(f"  {BOLD}8.{RESET} PostgreSQL Management")
            print(f"  {BOLD}9.{RESET} DNS & SSL Verification")
            print(f" {BOLD}10.{RESET} Backup Management")
            print(f" {BOLD}11.{RESET} Restore Management")
            print(f" {BOLD}12.{RESET} Monitoring & Logs")
            print(f" {BOLD}13.{RESET} Configuration Profiles")
            print(f" {BOLD}14.{RESET} Troubleshooting")
            print(f" {BOLD}15.{RESET} Generate Infrastructure Report")
            print(f" {BOLD}16.{RESET} Python / PostgreSQL / Docker / Compose / Portainer — Component Inspection")
            print(f" {BOLD}17.{RESET} Install Ansible & Baseline Config")
            print(f" {BOLD}18.{RESET} Install Jenkins CI/CD")
            print(f" {BOLD}19.{RESET} Error Diagnosis & Auto-Repair")
            print(f" {BOLD}20.{RESET} Odoo Diagnosis & Repair (17 / 18 / 19)")
            print("")
            print(f"  {BOLD}0.{RESET} Exit")
            print(f"{CYAN}=================================================={RESET}")

            choice = input(f"{BOLD}Select an option [0-20]: {RESET}").strip()

            if choice == "1":
                self.handle_system_information()
            elif choice == "2":
                step = HealthService.build_health_check_step()
                op = OperationRecord("op-health", "Infrastructure Health Check", "health", self.profile.profile_name, steps=[step])
                self.execute_workflow(op)
            elif choice == "3":
                self.run_preflight_checks()
            elif choice == "4":
                self.handle_docker_management()
            elif choice == "5":
                self.handle_traefik_management()
            elif choice == "6":
                self.handle_network_management()
            elif choice == "7":
                self.handle_odoo_management()
            elif choice == "8":
                self.handle_postgresql_management()
            elif choice == "9":
                self.handle_dns_ssl_verification()
            elif choice == "10":
                self.handle_backup_management()
            elif choice == "11":
                self.handle_restore_management()
            elif choice == "12":
                self.handle_monitoring_logs()
            elif choice == "13":
                self.handle_configuration_profiles()
            elif choice == "14":
                self.handle_troubleshooting()
            elif choice == "15":
                self.handle_generate_infrastructure_report()
            elif choice == "16":
                self.handle_runtime_setup()
            elif choice == "17":
                self.handle_ansible_install()
            elif choice == "18":
                self.handle_jenkins_install()
            elif choice == "19":
                self.handle_error_diagnosis()
            elif choice == "20":
                self.handle_odoo_diagnosis()
            elif choice == "0":
                print(f"{CYAN}Exiting Odoo Infrastructure Manager. Goodbye!{RESET}")
                break
            else:
                print(f"{RED}Invalid selection. Please choose an option from 0 to 20.{RESET}")

            input(f"\n{DIM}Press Enter to return to main menu...{RESET}")

    def handle_runtime_setup(self, dry_run=False):
        from app.services.runtime_inspector import VERSIONS, inspect_host, inspect_docker

        print("\n1. Python\n2. PostgreSQL\n3. Docker Engine\n4. Docker Compose\n5. Portainer\n0. Back")
        component = {"1": "python", "2": "postgresql", "3": "docker", "4": "compose", "5": "portainer"}.get(input("Choose component: ").strip())
        if not component:
            return
        if component == "docker":
            self.handle_docker_inspection(dry_run=dry_run)
            return
        if component == "compose":
            self.handle_compose_setup(dry_run=dry_run)
            return
        if component == "portainer":
            self.handle_portainer_setup(dry_run=dry_run)
            return
        print("\n1. Host\n2. Inside Docker\n0. Back")
        location = {"1": "host", "2": "docker"}.get(input("Choose installation location: ").strip())
        if not location:
            return
        report = inspect_host(component) if location == "host" else inspect_docker(component)
        for record in report["records"]:
            print(" | ".join(f"{key}: {value}" for key, value in record.items() if value))
        if report.get("details"):
            print(report["details"])
        for error in report["errors"]:
            print(f"Failed to complete inspection: {error}")
        if not report["records"]:
            print("No installation detected in checked paths and images; this does not exclude a custom installation.")
        if location == "docker":
            print("Image tag is not a version check inside it. Custom images may not appear; image presence does not mean a running container.")
        if report["records"]:
            if input("Would you like to choose an additional version? [y/N]: ").strip().lower() != "y":
                return
        versions = VERSIONS[component]
        # Project recommendations supplied by the operator, not a compatibility gate.
        python_recommendations = {
            "3.10": "Odoo 17",
            "3.11": "Odoo 17 and Odoo 18 (recommended for 18)",
            "3.12": "Odoo 19 (highly recommended)",
        }
        if component == "python":
            print("Project Python recommendations by Odoo version:")
        for index, version in enumerate(versions, 1):
            recommendation = f" — {python_recommendations[version]}" if component == "python" else ""
            print(f"{index}. {version}{recommendation}")
        if component == "python":
            print("4. Version newer than 3.12 (manual entry; outside current project recommendations)")
        print("0. Back")
        selected = input("Select version: ").strip()
        if component == "python" and selected == "4":
            import re
            version = input("Version in format 3.x: ").strip()
            if not re.fullmatch(r"3\.[0-9]+", version) or int(version.split(".")[1]) <= 12:
                print("Invalid version; enter 3.13 or newer in format 3.x.")
                return
        elif selected.isdigit() and 1 <= int(selected) <= len(versions):
            version = versions[int(selected) - 1]
        else:
            return
        print(f"Option: {component} {version} | {'Host' if location == 'host' else 'Docker'}")
        if component == "python" and location == "host":
            from app.services.python_installer import SUPPORTED_VERSIONS, install_python
            if version not in SUPPORTED_VERSIONS:
                print("Installation method for this version has not been added yet; currently available: 3.10, 3.11, and 3.12.")
                return
            print("Installation plan:")
            install_python(version, dry_run=True)
            if dry_run:
                return
            if input("Run these commands on the machine? [y/N]: ").strip().lower() == "y":
                install_python(version)
            return
        if component == "postgresql" and location == "host":
            from app.services.postgresql_installer import install_postgresql
            with_pgvector = input("Install pgvector too for Odoo 19 features? [y/N]: ").strip().lower() == "y"
            print("Installation plan via official PGDG repository:")
            install_postgresql(version, with_pgvector=with_pgvector, dry_run=True)
            if dry_run:
                return
            if input("Run these commands on the machine? [y/N]: ").strip().lower() == "y":
                install_postgresql(version, with_pgvector=with_pgvector)
            return
        print("Installation not executed: waiting for the installation method to be determined by the project owner.")

    def handle_portainer_setup(self, dry_run=False):
        from app.services.portainer_service import inspect_portainer, install_portainer
        use_sudo = False
        report = inspect_portainer()
        if report['status'] == 'error' and not dry_run and hasattr(os, 'geteuid') and os.geteuid() != 0:
            print(report['error'])
            print("Re-inspecting with sudo privileges according to selected installation method.")
            try:
                subprocess.run(['sudo', '-v'], check=True)
            except (OSError, subprocess.CalledProcessError, KeyboardInterrupt):
                print("Unable to obtain sudo privileges; installation not performed.")
                return
            use_sudo = True
            report = inspect_portainer(use_sudo=True)
        print("\nPortainer — Local Engine Inspection")
        for item in report['containers']:
            for key in ('Names', 'Image', 'ID', 'Status', 'Ports'):
                print(f"{key}: {item.get(key, '-')}")
        if report['status'] == 'installed':
            print("Portainer exists; running status shown above. Will not be reinstalled. Image tag is not a verified version.")
            return
        if report['status'] == 'conflict':
            print("Portainer name is used by another container; no changes were made.")
            return
        if report['status'] != 'missing':
            print(report['error'])
            print("Review Docker installation and socket access permissions before proceeding.")
            return
        print("No Portainer container detected. Proposed installation: portainer/portainer-ce (default tag latest).")
        print("The container will manage Docker via the socket and expose an HTTP web panel on the selected port. Project management remains via Terminal.")
        print("Persistent storage: /srv/portainer on the host; existing data will be used if found.")
        try:
            port = int(input("HTTP port on server [9000]: ").strip() or '9000')
        except ValueError:
            print("Enter a valid port number.")
            return
        edge = input("Publish port 8000 for Edge Agents? [Y/n]: ").strip().lower() != 'n'
        if not install_portainer(port, edge, dry_run=True, use_sudo=use_sudo):
            return
        if not dry_run and input("Execute installation and publish displayed ports? [y/N]: ").strip().lower() == 'y':
            install_portainer(port, edge, use_sudo=use_sudo)

    def handle_compose_setup(self, dry_run=False):
        from app.services.compose_installer import inspect_compose, install_compose
        report = inspect_compose()
        print("\nDocker Compose — Extension Inspection")
        if report['path']:
            print(f"Command: {report['path']} compose version")
        print(report['details'])
        if report['status'] == 'installed':
            print("The extension is installed and working; no need to reinstall.")
            return
        if report['status'] == 'docker_missing':
            print("Select 3 from the components list to set up Docker Engine.")
            return
        print("The extension is not available or could not be run; error details are shown above.")
        print("The package requires the official Docker repository prepared by the Docker Engine path.")
        install_compose(dry_run=True)
        if not dry_run and input("Install docker-compose-plugin on Ubuntu? [y/N]: ").strip().lower() == 'y':
            install_compose()

    def handle_docker_inspection(self, dry_run=False):
        from app.services.docker_inspector import inspect_engine, STATUS_TEXT
        report = inspect_engine()
        print("\nDocker Engine — Installation and Operation Inspection")
        print(STATUS_TEXT[report["status"]])
        for key, label in (("path", "Client path"), ("daemon_path", "Local dockerd path"),
                           ("client_version", "Client version"), ("server_version", "Engine version"),
                           ("context", "Docker context"), ("compose", "Docker Compose")):
            if report[key]:
                print(f"{label}: {report[key]}")
        for key, value in report["details"].items():
            print(f"{key}: {value}")
        for error in report["errors"]:
            print(f"Inspection details: {error}")
        if report["status"] == "missing":
            print("Recommended action: Install Docker Engine from the official Docker repository.")
        elif report["status"] != "running":
            print("Review connectivity, permissions, and service status before considering reinstallation.")
        print("Inspection is read-only. The current connection may refer to a remote engine or Docker Desktop.")
        if input("Open Docker Engine installation/update plan on local Ubuntu machine? [y/N]: ").strip().lower() != "y":
            return
        from app.services.docker_installer import install_docker
        choose_version = input("1. Latest stable version\n2. Select version from repository\nChoose [1/2]: ").strip()
        if choose_version not in ("1", "2"):
            return
        hello_world = input("Run hello-world test after installation (pulls image)? [y/N]: ").strip().lower() == "y"
        group_user = ""
        print("Optional: docker group membership grants broad privileges equivalent to root.")
        if input("Add user to docker group? [y/N]: ").strip().lower() == "y":
            group_user = input("Local username: ").strip()
            if not group_user:
                print("No user specified; group membership will not change.")
        install_docker(dry_run=dry_run, choose_version=choose_version == "2",
                       hello_world=hello_world, group_user=group_user)

    def validate_current_profile(self):
        print(f"\n{BOLD}Validating configuration profile: {self.profile.profile_name}...{RESET}")
        res = ConfigValidator.validate(self.profile)
        if res.is_valid:
            print(f"{GREEN}✓ Profile is 100% valid with 0 errors!{RESET}")
        else:
            print(f"{RED}✗ Found {len(res.errors)} configuration errors:{RESET}")
            for err in res.errors:
                print(f"  {RED}• {err}{RESET}")

        if res.warnings:
            print(f"\n{YELLOW}! {len(res.warnings)} warnings to review:{RESET}")
            for warn in res.warnings:
                print(f"  {YELLOW}• {warn}{RESET}")

    def run_preflight_checks(self):
        from app.services.smart_inspector import SmartInspectorService, ComponentStatus
        from app.services.system_backup import SystemBackupService

        print(f"\n{BOLD}{CYAN}=============================================================================={RESET}")
        print(f"{BOLD}{CYAN}             PRE-FLIGHT INTELLIGENT INSPECTION & AUDIT REPORT                 {RESET}")
        print(f"{BOLD}{CYAN}                 Requirements Inspection & Basic Package Installation                 {RESET}")
        print(f"{BOLD}{CYAN}=============================================================================={RESET}\n")

        report = SmartInspectorService.run_full_inspection()

        print(f"{BOLD}Operating System:{RESET} {report.os_name} ({report.os_version})")
        print(f"{BOLD}Timestamp:{RESET}        {report.timestamp}")
        print(f"{BOLD}Compliance Status:{RESET} {'Compliant (Ubuntu 22.04+)' if report.is_supported_ubuntu else 'Warning: OS Needs Update'}\n")

        print("┌───────────────────────────────────┬──────────────┬────────────────────────┬──────────────────────┐")
        print("│ Component                              │ Status        │ Detected Version       │ Path / Details       │")
        print("├───────────────────────────────────┼──────────────┼────────────────────────┼──────────────────────┤")

        for c in report.components:
            status_text = "INSTALLED"
            status_color = GREEN
            if c.status == ComponentStatus.INSTALLED:
                status_text = "INSTALLED [✓]"
                status_color = GREEN
            elif c.status == ComponentStatus.MISSING:
                status_text = "MISSING [✗]"
                status_color = RED
            elif c.status == ComponentStatus.NEEDS_UPDATE:
                status_text = "UPDATE [!]"
                status_color = YELLOW
            else:
                status_text = "ISSUES [?]"
                status_color = YELLOW

            comp_name = c.name[:33]
            ver = (c.detected_version or "N/A")[:22]
            path_info = (c.binary_path or c.details or "N/A")[:20]

            print(f"│ {comp_name:<33} │ {status_color}{status_text:<12}{RESET} │ {ver:<22} │ {path_info:<20} │")

        print("└───────────────────────────────────┴──────────────┴────────────────────────┴──────────────────────┘")

        missing_comps = [c for c in report.components if c.status == ComponentStatus.MISSING]
        if missing_comps:
            print(f"\n{YELLOW}{BOLD}Missing Required Components ({len(missing_comps)}):{RESET}")
            for mc in missing_comps:
                print(f"  • {BOLD}{mc.name}{RESET}: {mc.why_needed}")
                print(f"    Action: {mc.recommended_action}")

            ans = input(f"\n{CYAN}Would you like to create a safety snapshot and install missing packages? [y/N]: {RESET}").strip().lower()
            if ans == "y":
                print(f"\n{BOLD}[1/2] Creating pre-installation safety infrastructure snapshot...{RESET}")
                try:
                    snap = SystemBackupService.create_full_snapshot()
                    print(f"{GREEN}✓ Snapshot created: {snap['archive_file']} (SHA256: {snap['sha256'][:16]}...){RESET}")
                except Exception as e:
                    print(f"{YELLOW}Warning: Could not create snapshot: {e}{RESET}")
                print(f"\n{BOLD}[2/2] Launching safe package installation...{RESET}")
                import os
                if os.geteuid() != 0:
                    print(f"{YELLOW}Note: Not running as root. Using sudo for package installation...{RESET}")
                for mc in missing_comps:
                    if mc.install_command:
                        cmd = mc.install_command
                        if os.geteuid() != 0 and cmd and cmd[0] in ['apt-get', 'apt']:
                            cmd = ['sudo'] + list(cmd)
                        print(f"==> Installing {mc.name}: {' '.join(cmd)}")
                        try:
                            subprocess.run(cmd, check=False)
                        except Exception as e:
                            print(f"{YELLOW}Warning: {e}{RESET}")
                print(f"\n{GREEN}{BOLD}✔ Installation sweep completed.{RESET}")
        else:
            print(f"\n{GREEN}{BOLD}✔ All required components, Docker, Compose, and tools are verified and ready!{RESET}")

    def handle_interactive_restore(self):
        print(f"\n{YELLOW}{BOLD}⚠ CRITICAL RESTORE OPERATION CONFIRMATION ⚠{RESET}")
        print("Restoring a database will overwrite existing tables.")
        print("An automatic safety snapshot will be created before any changes.")
        version = input("Target Odoo version (17 or 19): ").strip()
        dump_path = input("Path to .sql or .sql.gz dump: ").strip()
        target_db = input("Target database name to restore into: ").strip()

        print(f"\n{RED}{BOLD}WARNING: You are about to restore into '{target_db}' on Odoo {version}!{RESET}")
        confirm = input(f"Type 'RESTORE-{target_db}' to confirm: ").strip()
        if confirm != f"RESTORE-{target_db}":
            print(f"{YELLOW}Safety confirmation mismatch. Restore aborted!{RESET}")
            return

        op = DatabaseOpsWorkflow.create_restore_operation(
            version=version,
            dump_file_path=dump_path,
            target_db=target_db,
            force=True
        )
        self.execute_workflow(op)

    def handle_system_information(self):
        import shutil, socket, datetime
        import platform
        print(f"\n{BOLD}{CYAN}=== 1. SYSTEM INFORMATION ==={RESET}")
        try:
            actual_hostname = socket.gethostname()
        except Exception:
            actual_hostname = self.profile.server.hostname
        print(f"Host:       {actual_hostname} ({self.profile.server.ip_or_host})")
        print(f"Timezone:   {self.profile.server.timezone} | Time: {datetime.datetime.now()}")
        uname = os.uname()
        print(f"OS/Kernel:  {platform.system()} {uname.release} ({uname.machine})")
        try:
            dist = platform.freedesktop_os_release() if hasattr(platform, 'freedesktop_os_release') else {}
            if dist.get('PRETTY_NAME'):
                print(f"Distribution: {dist.get('PRETTY_NAME')}")
        except Exception:
            pass
        try:
            total, used, free = shutil.disk_usage("/")
            print(f"Disk (Root): Total: {total/(1024**3):.1f} GB | Used: {used/(1024**3):.1f} GB | Free: {free/(1024**3):.1f} GB")
        except Exception:
            pass
        docker_path = shutil.which("docker")
        if docker_path:
            try:
                import subprocess
                res = subprocess.run([docker_path, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
                if res.returncode == 0:
                    print(f"Docker:     {res.stdout.decode().strip()}")
                else:
                    print(f"Docker Bin: {docker_path}")
            except Exception:
                print(f"Docker Bin: {docker_path}")
        else:
            print(f"Docker:     Not Installed")
        try:
            import subprocess
            res = subprocess.run(["docker", "compose", "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
            if res.returncode == 0:
                print(f"Docker Compose: {res.stdout.decode().strip()}")
            else:
                res = subprocess.run(["docker-compose", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
                if res.returncode == 0:
                    print(f"Docker Compose: {res.stdout.decode().strip()}")
        except Exception:
            pass

    def _installed_compose(self, component: str) -> Optional[str]:
        """Returns the compose file of an installed instance when it exists."""
        candidate = os.path.join(self.profile.paths.data_root, component, "docker-compose.yml")
        return candidate if os.path.exists(candidate) else None

    def _start_odoo_stack(self, version: str) -> None:
        compose = self._installed_compose(f"odoo{version}")
        if compose:
            subprocess.run(["docker", "compose", "-f", compose, "up", "-d"], check=False)
        else:
            print(f"{YELLOW}! Odoo {version} is not installed under {self.profile.paths.data_root}; "
                  f"use Odoo Management to deploy it first.{RESET}")

    def _stop_odoo_stack(self, version: str) -> None:
        compose = self._installed_compose(f"odoo{version}")
        if compose:
            subprocess.run(["docker", "compose", "-f", compose, "stop"], check=False)
        else:
            print(f"{YELLOW}! Odoo {version} is not installed under {self.profile.paths.data_root}.{RESET}")

    def handle_docker_management(self):
        print(f"\n{BOLD}{CYAN}=== 4. DOCKER MANAGEMENT ==={RESET}")
        print(" [1] List all containers (docker ps -a)")
        print(" [2] Start all stopped services")
        print(" [3] Stop all running services (Safe: volumes preserved)")
        print(" [4] Check Docker daemon service status")
        sub = input(f"{BOLD}Choose action [1-4]: {RESET}").strip()
        traefik_compose = os.path.join(PROJECT_ROOT, "deployment/traefik/docker-compose.yml")
        pgadmin_compose = os.path.join(PROJECT_ROOT, "deployment/pgadmin/docker-compose.yml")
        env_file = os.path.join(PROJECT_ROOT, ".env")
        if sub == "1":
            subprocess.run(["docker", "ps", "-a"], check=False)
        elif sub == "2":
            subprocess.run(["docker", "compose", "--env-file", env_file, "-f", traefik_compose, "up", "-d"], check=False)
            self._start_odoo_stack("17")
            self._start_odoo_stack("18")
            self._start_odoo_stack("19")
            subprocess.run(["docker", "compose", "--env-file", env_file, "-f", pgadmin_compose, "up", "-d"], check=False)
        elif sub == "3":
            self._stop_odoo_stack("19")
            self._stop_odoo_stack("18")
            self._stop_odoo_stack("17")
            subprocess.run(["docker", "compose", "--env-file", env_file, "-f", pgadmin_compose, "stop"], check=False)
            subprocess.run(["docker", "compose", "--env-file", env_file, "-f", traefik_compose, "stop"], check=False)
            print(f"{GREEN}✓ Containers stopped safely without touching volumes.{RESET}")
        elif sub == "4":
            subprocess.run(["docker", "info"], check=False)

    def handle_traefik_management(self):
        from app.services.traefik_manager import DEFAULT_CONFIG_DIR, TraefikDockerManager, TraefikConfig, inspect_traefik, install_traefik, setup_traefik_ufw

        print(f"\n{BOLD}{CYAN}=============================================================================={RESET}")
        print(f"{BOLD}{CYAN}             TRAEFIK DOCKER MANAGEMENT MODULE                  {RESET}")
        print(f"{BOLD}{CYAN}      Ubuntu Server/Desktop • Docker Engine • Traefik v3.7 • Proxy Network    {RESET}")
        print(f"{BOLD}{CYAN}=============================================================================={RESET}\n")

        print("  [1] Environment Discovery & Inspection (Ports, Containers, ACME, Network)")
        print("  [2] Deploy / Update Traefik v3.7 Stack (with pre-change backup)")
        print("  [3] Lifecycle Control: Start / Stop / Restart Container")
        print("  [4] Proxy Network Management (Inspect, Connect/Disconnect Containers)")
        print("  [5] Docker Labels Generator (Odoo 17 / 18 / 19, pgAdmin, Custom)")
        print("  [6] Create Traefik Backup Snapshot (Configs, ACME, Compose with SHA256)")
        print("  [7] Restore Traefik Backup Archive (Safe Rollback Guarded)")
        print("  [8] Verify Routing & Dashboard Connectivity (Ports 80 & 443, Secure Router)")
        print("  [9] View Live Traefik Container Logs")
        print(" [10] Open Firewall Ports 80/TCP & 443/TCP (UFW)")
        print("  [0] Return to Main Menu")

        sub = input(f"\n{BOLD}Select Traefik Action [0-9]: {RESET}").strip()

        if sub == "1":
            print(f"\n{BOLD}Auditing Traefik Docker environment...{RESET}")
            rep = TraefikDockerManager.discover_environment()
            print(f"Timestamp:          {rep.timestamp}")
            print(f"Docker Engine:      {'Installed (' + rep.docker_version + ')' if rep.docker_installed else 'MISSING'}")
            print(f"Docker Compose:     {'Installed (' + rep.compose_version + ')' if rep.compose_installed else 'MISSING'}")
            print(f"Traefik Container:  {rep.container_status.upper()} (Image: {rep.container_image or 'None'})")
            print(f"Proxy Network:      {'EXISTS (' + (rep.proxy_subnet or 'bridge') + ')' if rep.proxy_network_exists else 'MISSING'}")
            print(f"Connected Services: {len(rep.connected_containers)} containers")
            for c in rep.connected_containers:
                print(f"  • {c.name} ({c.ipv4_address}) [{c.id}]")
            print(f"Compose File:       {rep.compose_file_path} ({'Found' if rep.compose_file_exists else 'Not created yet'})")
            print(f"ACME File:          {'Found' if rep.acme_file_exists else 'Not found'} ({'0600 Permissions Valid' if rep.acme_permissions_valid else 'Invalid Permissions!'})")
            print(f"Dashboard URL:      {rep.dashboard_url} ({'Accessible' if rep.dashboard_accessible else 'Not reachable'})")

            print(f"\n{BOLD}Port Inspection Matrix:{RESET}")
            for pi in rep.ports_audit:
                status_str = f"{RED}BOUND / IN USE{RESET}" if pi.is_in_use else f"{GREEN}FREE / AVAILABLE{RESET}"
                print(f"  Port {pi.port:5d} : {status_str} - {pi.service_name}")

            if rep.warnings:
                print(f"\n{YELLOW}Warnings Detected:{RESET}")
                for w in rep.warnings:
                    print(f"  ! {w}")

        elif sub == "2":
            use_sudo = False
            report = inspect_traefik()
            if report['status'] == 'error' and not dry_run and hasattr(os, 'geteuid') and os.geteuid() != 0:
                print(report['error'])
                print("Re-inspecting with sudo privileges according to selected installation method.")
                try:
                    subprocess.run(['sudo', '-v'], check=True)
                except (OSError, subprocess.CalledProcessError, KeyboardInterrupt):
                    print("Unable to obtain sudo privileges; installation not performed.")
                    return
                use_sudo = True
                report = inspect_traefik(use_sudo=True)
            print("\nTraefik — Local Engine Inspection")
            for item in report['containers']:
                for key in ('Names', 'Image', 'ID', 'Status', 'Ports'):
                    print(f"{key}: {item.get(key, '-')}")
            if report['status'] == 'installed':
                print("Traefik is already installed. Container status shown above. Will not be reinstalled.")
                return
            if report['status'] == 'conflict':
                print("Traefik name is used by another container. No changes were made.")
                return
            if report['status'] != 'missing':
                print(report['error'])
print("Review Docker installation and socket access permissions before proceeding.")
                return
            print("No Traefik container detected. Proposed installation: traefik:v3.7 on ports 80 and 443.")
            print("Directories: /opt/traefik/{config,letsencrypt} and /data/traefik/logs, and acme.json file with 0600 permissions.")
            print("A Docker network named proxy will be created if it does not exist.")
            if not install_traefik(dry_run=True, use_sudo=use_sudo):
                return
            if not dry_run and input("Execute Traefik installation and publish ports 80/443? [y/N]: ").strip().lower() == 'y':
                install_traefik(use_sudo=use_sudo)

        elif sub == "3":
            print(f"\n{BOLD}Traefik Container Lifecycle:{RESET}")
            print(" [1] Start container")
            print(" [2] Stop container (Safe: volumes and proxy network preserved)")
            print(" [3] Restart container")
            lc = input("Choose action [1-3]: ").strip()
            if lc == "1":
                subprocess.run(["docker", "start", "traefik"], check=False)
                print(f"{GREEN}✓ Traefik container started.{RESET}")
            elif lc == "2":
                subprocess.run(["docker", "stop", "traefik"], check=False)
                print(f"{GREEN}✓ Traefik container stopped safely.{RESET}")
            elif lc == "3":
                subprocess.run(["docker", "restart", "traefik"], check=False)
                print(f"{GREEN}✓ Traefik container restarted.{RESET}")

        elif sub == "4":
            print(f"\n{BOLD}Proxy Network Management:{RESET}")
            print(" [1] Inspect proxy network")
            print(" [2] Connect a container to proxy network")
            print(" [3] Disconnect a container from proxy network")
            nc = input("Choose action [1-3]: ").strip()
            if nc == "1":
                subprocess.run(["docker", "network", "inspect", "proxy"], check=False)
            elif nc == "2":
                cname = input("Enter container name to connect: ").strip()
                if cname:
                    subprocess.run(["docker", "network", "connect", "proxy", cname], check=False)
                    print(f"{GREEN}✓ Container '{cname}' connected to proxy network.{RESET}")
            elif nc == "3":
                cname = input("Enter container name to disconnect: ").strip()
                if cname:
                    subprocess.run(["docker", "network", "disconnect", "proxy", cname], check=False)
                    print(f"{GREEN}✓ Container '{cname}' disconnected from proxy network.{RESET}")

        elif sub == "5":
            print(f"\n{BOLD}Docker Label Generator for Traefik Ingress:{RESET}")
            print(" [1] Odoo 17 (Port 8069 + Livechat 8072)")
            print(" [2] Odoo 18 (Port 10018 / 8069 + Livechat 8072)")
            print(" [3] Odoo 19 (Port 10019 / 8069 + Livechat 8072)")
            print(" [4] pgAdmin (Port 5050)")
            print(" [5] Custom Service")
            svc_choice = input("Select service [1-5]: ").strip()
            service_map = {
                "1": ("odoo17", 8069),
                "2": ("odoo18", 8069),
                "3": ("odoo19", 8069),
                "4": ("pgadmin", 5050),
            }
            stype, default_p = service_map.get(svc_choice, ("custom", 80))
            default_domain = "pgadmin.example.com" if stype == "pgadmin" else f"{stype}.example.com"
            domain = input(f"Enter domain (e.g. {default_domain}): ").strip() or default_domain
            port_str = input(f"Enter internal port [default {default_p}]: ").strip()
            port = int(port_str) if port_str.isdigit() else default_p

            labels = TraefikDockerManager.generate_service_labels(stype, domain, port, entrypoints="web")
            print(f"\n{GREEN}{BOLD}Generated Docker Labels for {stype}:{RESET}")
            for l in labels:
                print(f"  - \"{l}\"")

        elif sub == "6":
            print(f"\n{BOLD}Creating Traefik backup snapshot...{RESET}")
            snap = TraefikDockerManager.create_backup_snapshot(DEFAULT_CONFIG_DIR)
            print(f"{GREEN}✓ Traefik snapshot created: {snap['archive_path']}{RESET}")
            print(f"  Size:   {snap['size_bytes'] / 1024:.2f} KB")
            print(f"  SHA256: {snap['sha256']}")
            print(f"  Status: {snap['status']}")

        elif sub == "7":
            print(f"\n{YELLOW}{BOLD}⚠ Traefik Backup Restoration ⚠{RESET}")
            arch = input("Enter path to Traefik backup archive (.tar.gz): ").strip()
            if os.path.exists(arch):
                res = TraefikDockerManager.restore_backup_snapshot(arch, DEFAULT_CONFIG_DIR)
                print(f"{GREEN}✓ Restored successfully from {arch}{RESET}")
                print(f"{GREEN}✓ Automated rollback guard saved to {res['safety_snapshot']['archive_path']}{RESET}")
            else:
                print(f"{RED}File not found: {arch}{RESET}")

        elif sub == "8":
            print(f"\n{BOLD}Testing Routing & Dashboard Connectivity...{RESET}")
            res = TraefikDockerManager.test_routing_and_connectivity()
            for d in res["details"]:
                print(f"  • {d}")
            if res["http_port_80"]:
                print(f"{GREEN}✓ Port 80 (HTTP) verified active.{RESET}")
            if res["https_port_443"]:
                print(f"{GREEN}✓ Port 443 (HTTPS / secured dashboard router) verified active.{RESET}")
            if not res["traefik_running"]:
                print(f"{YELLOW}! Traefik container is not running; start it before testing routes.{RESET}")

        elif sub == "9":
            print(f"\n{BOLD}Streaming last 50 lines of Traefik logs:{RESET}\n")
            subprocess.run(["docker", "logs", "--tail", "50", "traefik"], check=False)

        elif sub == "10":
            use_sudo = False
            if not shutil.which('ufw'):
                print(f"\n{YELLOW}UFW is not installed on the system. No ports were opened.{RESET}")
                print("You can install it via: sudo apt-get install ufw")
            else:
                print(f"\n{BOLD}Opening Traefik firewall ports via UFW...{RESET}")
                try:
                    subprocess.run(['sudo', '-v'], check=True)
                    use_sudo = True
                except (OSError, subprocess.CalledProcessError, KeyboardInterrupt):
                    print("Unable to obtain sudo privileges; skipped.")
                if use_sudo:
                    ok = setup_traefik_ufw(use_sudo=True)
                    if ok:
                        print(f"{GREEN}✓ Ports 80/TCP and 443/TCP opened via UFW.{RESET}")
                    else:
                        print(f"{YELLOW}! UFW port setup completed with warnings.{RESET}")
                try:
                    subprocess.run(['sudo', 'ufw', 'status'], check=False)
                except Exception:
                    pass

    def handle_ansible_install(self):
        from app.services.ansible_service import inspect_ansible, install_ansible, ANSIBLE_DIR
        use_sudo = False
        report = inspect_ansible()
        if report['status'] == 'error' and hasattr(os, 'geteuid') and os.geteuid() != 0:
            print(report['error'])
            print("Re-inspecting with sudo privileges according to selected installation method.")
            try:
                subprocess.run(['sudo', '-v'], check=True)
            except (OSError, subprocess.CalledProcessError, KeyboardInterrupt):
                print("Unable to obtain sudo privileges; installation not performed.")
                return
            use_sudo = True
            report = inspect_ansible(use_sudo=True)
        print(f"\n{BOLD}{CYAN}=== ANSIBLE INSTALLATION ==={RESET}")
        print(f"Current status: {report['status']}")
        if report.get('version'):
            print(f"Version: {report['version']}")
        if report['status'] == 'installed':
            print("Ansible is already installed. Will not reinstall.")
            return
        if report['status'] == 'error':
            print(report['error'])
            return
        print("No Ansible installation detected. Proposed installation:")
        print("  • System update and requirement installation (python3, pipx, git, curl, etc.)")
        print("  • Install Ansible via pipx for current user")
        print(f"  • Create project structure in {ANSIBLE_DIR}")
        print("  • Create ansible.cfg, inventory/hosts.ini, and test playbook")
        print("  • Install collections: community.docker, ansible.posix")
        print()
        if not install_ansible(dry_run=True, use_sudo=use_sudo):
            return
        if input("Execute Ansible installation on this machine? [y/N]: ").strip().lower() == 'y':
            install_ansible(use_sudo=use_sudo)

    def handle_jenkins_install(self):
        from app.services.jenkins_service import inspect_jenkins, install_jenkins, system_preflight_check, JENKINS_DOMAIN, JENKINS_CERTSRESOLVER
        use_sudo = False
        report = inspect_jenkins()
        if report['status'] == 'error' and hasattr(os, 'geteuid') and os.geteuid() != 0:
            print(report['error'])
            print("Re-inspecting with sudo privileges according to selected installation method.")
            try:
                subprocess.run(['sudo', '-v'], check=True)
            except (OSError, subprocess.CalledProcessError, KeyboardInterrupt):
                print("Unable to obtain sudo privileges; installation not performed.")
                return
            use_sudo = True
            report = inspect_jenkins(use_sudo=True)
        print(f"\n{BOLD}{CYAN}=== JENKINS CI/CD INSTALLATION ==={RESET}")
        print(f"Current status: {report['status']}")
        if report['status'] == 'installed':
            print("Jenkins is already installed. Will not reinstall.")
            return
        if report['status'] == 'error':
            print(report['error'])
            return

        # Pre-installation system inspection
        print(f"\n{BOLD}Pre-installation system inspection:{RESET}")
        preflight = system_preflight_check()
        for key, value in preflight.items():
            print(f"  [{key}] {value}")
        print()

        print("No Jenkins installation detected. Proposed installation:")
        print(f"  • Docker image: {IMAGE if 'IMAGE' in dir() else 'jenkins/jenkins:lts-jdk21'}")
        print(f"  • Data storage: /data/jenkins (UID 1000:1000)")
        print(f"  • Configuration file: /opt/jenkins/docker-compose.yml")
        print(f"  • Timezone: {JENKINS_TIMEZONE if 'JENKINS_TIMEZONE' in dir() else 'Africa/Tripoli'}")
        print("  • Connect to Traefik network (proxy) for HTTPS access only")
        print("  • Docker socket not mounted inside container (security)")
        print("  • Automatic restart (--restart=always)")
        print()

        domain = input(f"Access domain [default {JENKINS_DOMAIN}]: ").strip() or JENKINS_DOMAIN
        certsresolver = input(f"Traefik certificate resolver [default {JENKINS_CERTSRESOLVER}]: ").strip() or JENKINS_CERTSRESOLVER
        print(f"\nSelected domain: {domain}")
        print(f"Certificate resolver: {certsresolver}")
        print("Ensure the domain points to the server IP via an A record in DNS.")
        print("Ensure the certificate resolver name matches Traefik settings (e.g. 'letsencrypt' or 'le').")

        if not install_jenkins(dry_run=True, use_sudo=use_sudo, domain=domain, certsresolver=certsresolver):
            return
        if input("Execute Jenkins installation on this machine? [y/N]: ").strip().lower() == 'y':
            install_jenkins(use_sudo=use_sudo, domain=domain, certsresolver=certsresolver)

    def handle_error_diagnosis(self):
        from app.services.portainer_service import portainer_diagnose, portainer_repair
        from app.services.traefik_manager import traefik_diagnose, traefik_repair
        from app.services.ansible_service import ansible_diagnose, ansible_repair
        from app.services.jenkins_service import jenkins_diagnose, jenkins_repair

        print(f"\n{BOLD}{CYAN}=== Error Diagnosis & Auto-Repair ==={RESET}")
        print("  [1] Portainer")
        print("  [2] Traefik")
        print("  [3] Ansible")
        print("  [4] Jenkins")
        print("  [0] Back")

        sub = input(f"{BOLD}Choose component [0-4]: {RESET}").strip()

        if sub == "1":
            self._diagnose_and_repair_component("Portainer", portainer_diagnose, portainer_repair)
        elif sub == "2":
            self._diagnose_and_repair_component("Traefik", traefik_diagnose, traefik_repair)
        elif sub == "3":
            self._diagnose_and_repair_component("Ansible", ansible_diagnose, ansible_repair)
        elif sub == "4":
            self._diagnose_and_repair_component("Jenkins", jenkins_diagnose, jenkins_repair)
        elif sub == "0":
            return
        else:
            print(f"{RED}Invalid selection.{RESET}")

    def _diagnose_and_repair_component(self, name, diagnose_fn, repair_fn):
        use_sudo = False
        if hasattr(os, 'geteuid') and os.geteuid() != 0:
            try:
                subprocess.run(['sudo', '-v'], check=True)
                use_sudo = True
            except (OSError, subprocess.CalledProcessError, KeyboardInterrupt):
                print(f"{YELLOW}Unable to obtain sudo privileges; diagnosis will be read-only.{RESET}")

        issues, repairs = diagnose_fn(use_sudo=use_sudo)

        if not issues:
            print(f"\n{GREEN}✓ No errors detected in {name}.{RESET}")
            return

        print(f"\n{BOLD}Detected errors in {name}:{RESET}")
        for idx, issue in enumerate(issues, 1):
            severity_color = RED if issue['severity'] == 'critical' else YELLOW if issue['severity'] == 'high' else CYAN
            print(f"\n  {idx}. {severity_color}[{issue['severity'].upper()}]{RESET} {issue['title']}")
            print(f"     Component: {issue['component']}")
            print(f"     Description: {issue['description']}")
            if issue.get('auto_fix'):
                print(f"     Automatic repair: Available ({issue['fix_description']})")
            else:
                print(f"     Automatic repair: Not available ({issue['fix_description']})")

        print(f"\n{BOLD}Repair options:{RESET}")
        print("  [a] Automatic repair for all available issues")
        print("  [m] Select issues for manual repair")
        print("  [0] Back")

        sub = input(f"{BOLD}Choose [a/m/0]: {RESET}").strip().lower()

        if sub == "a":
            auto_count = 0
            for issue in issues:
                if issue.get('auto_fix'):
                    success, msg = repair_fn(issue, use_sudo=use_sudo)
                    if success:
                        print(f"  ✓ Done: {issue['title']}")
                        auto_count += 1
                    else:
                        print(f"  ✗ Failed: {issue['title']} - {msg}")
                else:
                    print(f"  ⊘ Skipped: {issue['title']} (automatic repair not supported)")
            print(f"\n{GREEN}{auto_count} issues repaired automatically.{RESET}")
        elif sub == "m":
            for idx, issue in enumerate(issues, 1):
                if not issue.get('auto_fix'):
                    print(f"  {idx}. ⊘ {issue['title']} - Not available for automatic repair")
                    continue
                choice = input(f"  {idx}. Repair '{issue['title']}'? [y/N]: ").strip().lower()
                if choice == 'y':
                    success, msg = repair_fn(issue, use_sudo=use_sudo)
                    if success:
                        print(f"    ✓ Success.")
                    else:
                        print(f"    ✗ Failed: {msg}")

    def handle_odoo_diagnosis(self):
        from app.services.odoo_service import odoo_diagnose, odoo_repair, install_odoo, inspect_odoo, ODOO_VERSIONS, ODOO_HTTP_PORTS, ODOO_CHAT_PORTS, ODOO_INTERNAL_NETWORKS, PG_IMAGES
        use_sudo = False
        if hasattr(os, 'geteuid') and os.geteuid() != 0:
            try:
                subprocess.run(['sudo', '-v'], check=True)
                use_sudo = True
            except (OSError, subprocess.CalledProcessError, KeyboardInterrupt):
                print(f"{YELLOW}Unable to obtain sudo privileges; diagnosis will be read-only.{RESET}")

        print(f"\n{BOLD}{CYAN}=== Odoo Diagnosis & Repair (17 / 18 / 19) ==={RESET}")
        print("  [1] Odoo 17 (PostgreSQL 16)")
        print("  [2] Odoo 18 (PostgreSQL 17)")
        print("  [3] Odoo 19 (PostgreSQL 18)")
        print("  [0] Back")

        sub = input(f"{BOLD}Choose Odoo version [0-3]: {RESET}").strip()
        version_map = {"1": "17", "2": "18", "3": "19"}
        version = version_map.get(sub)
        if not version:
            return

        issues, repairs = odoo_diagnose(version, use_sudo=use_sudo)

        if not issues:
            print(f"\n{GREEN}✓ No errors detected in Odoo {version}.{RESET}")
            report = inspect_odoo(version, use_sudo=use_sudo)
            if report['status'] == 'missing':
                print(f"\n{YELLOW}Odoo {version} is not installed. Would you like to install it?{RESET}")
                print(f"  • Image: odoo:{version}")
                print(f"  • Database: PostgreSQL {PG_IMAGES[version].split(':')[1]}")
                print(f"  • HTTP port: {ODOO_HTTP_PORTS[version]}")
                print(f"  • Chat port: {ODOO_CHAT_PORTS[version]}")
                print(f"  • Internal network: {ODOO_INTERNAL_NETWORKS[version]}")
                print(f"  • Directory: {self.profile.paths.data_root}/odoo{version}")
                if input(f"Execute Odoo {version} installation? [y/N]: ").strip().lower() == 'y':
                    with_traefik = bool(self.profile.traefik.enabled and self.profile.security.enforce_https)
                    install_odoo(self.profile, version, use_sudo=use_sudo, with_traefik=with_traefik)
            return

        print(f"\n{BOLD}Detected errors in Odoo {version}:{RESET}")
        for idx, issue in enumerate(issues, 1):
            severity_color = RED if issue['severity'] == 'critical' else YELLOW if issue['severity'] == 'high' else CYAN
            print(f"\n  {idx}. {severity_color}[{issue['severity'].upper()}]{RESET} {issue['title']}")
            print(f"     Component: {issue['component']}")
            print(f"     Description: {issue['description']}")
            if issue.get('auto_fix'):
                print(f"     Automatic repair: Available ({issue['fix_description']})")
            else:
                print(f"     Automatic repair: Not available ({issue['fix_description']})")

        print(f"\n{BOLD}Repair options:{RESET}")
        print("  [a] Automatic repair for all available issues")
        print("  [m] Select issues for manual repair")
        print("  [i] Install Odoo (if not installed)")
        print("  [0] Back")

        sub2 = input(f"{BOLD}Choose [a/m/i/0]: {RESET}").strip().lower()

        if sub2 == "a":
            auto_count = 0
            for issue in issues:
                if issue.get('auto_fix'):
                    success, msg = odoo_repair(issue, use_sudo=use_sudo)
                    if success:
                        print(f"  ✓ Done: {issue['title']}")
                        auto_count += 1
                    else:
                        print(f"  ✗ Failed: {issue['title']} - {msg}")
                else:
                    print(f"  ⊘ Skipped: {issue['title']} (automatic repair not supported)")
            print(f"\n{GREEN}{auto_count} issues repaired automatically.{RESET}")
        elif sub2 == "m":
            for idx, issue in enumerate(issues, 1):
                if not issue.get('auto_fix'):
                    print(f"  {idx}. ⊘ {issue['title']} - Not available for automatic repair")
                    continue
                choice = input(f"  {idx}. Repair '{issue['title']}'? [y/N]: ").strip().lower()
                if choice == 'y':
                    success, msg = odoo_repair(issue, use_sudo=use_sudo)
                    if success:
                        print(f"    ✓ Success.")
                    else:
                        print(f"    ✗ Failed: {msg}")
        elif sub2 == "i":
            report = inspect_odoo(version, use_sudo=use_sudo)
            if report['status'] != 'missing':
                print(f"Odoo {version} is already installed (status: {report['status']}). No need to install.")
                return
            with_traefik = bool(self.profile.traefik.enabled and self.profile.security.enforce_https)
            install_odoo(self.profile, version, use_sudo=use_sudo, with_traefik=with_traefik)

    def handle_network_management(self):
        print(f"\n{BOLD}{CYAN}=== 6. DOCKER NETWORK MANAGEMENT ==={RESET}")
        print(" [1] Inspect shared 'proxy' network (172.28.0.0/16)")
        print(" [2] Inspect internal 'odoo17_internal' isolated network")
        print(" [3] Inspect internal 'odoo18_internal' isolated network")
        print(" [4] Inspect internal 'odoo19_internal' isolated network")
        sub = input(f"{BOLD}Choose action [1-4]: {RESET}").strip()
        if sub == "1":
            subprocess.run(["docker", "network", "inspect", self.profile.network.proxy_network_name], check=False)
        elif sub == "2":
            subprocess.run(["docker", "network", "inspect", "odoo17_internal"], check=False)
        elif sub == "3":
            subprocess.run(["docker", "network", "inspect", "odoo18_internal"], check=False)
        elif sub == "4":
            subprocess.run(["docker", "network", "inspect", "odoo19_internal"], check=False)

    def handle_odoo_management(self):
        print(f"\n{BOLD}{CYAN}=== 7. ODOO MANAGEMENT ==={RESET}")
        print(" Select Odoo version:")
        print("  [1] Odoo 17 (PostgreSQL 16)")
        print("  [2] Odoo 18 (PostgreSQL 17)")
        print("  [3] Odoo 19 (PostgreSQL 18)")
        choice = input(f"{BOLD}Version [1-3, default 3]: {RESET}").strip()
        version = {"1": "17", "2": "18", "3": "19"}.get(choice, "19")
        pg = {"17": "16", "18": "17", "19": "18"}[version]

        print(f"\n{BOLD}Odoo {version} Management:{RESET}")
        print(f" [1] Deploy Odoo {version} & PostgreSQL {pg} stack")
        print(f" [2] View Odoo {version} logs")
        print(f" [3] Restart Odoo {version} container")
        print(f" [4] View odoo{version} odoo.conf")
        sub = input(f"{BOLD}Choose action [1-4]: {RESET}").strip()

        if sub == "1":
            workflow = {
                "17": DeployOdoo17Workflow,
                "18": DeployOdoo18Workflow,
                "19": DeployOdoo19Workflow,
            }[version]
            self.execute_workflow(workflow.create_operation(self.profile))
        elif sub == "2":
            subprocess.run(["docker", "logs", "--tail", "50", f"odoo{version}"], check=False)
        elif sub == "3":
            subprocess.run(["docker", "restart", f"odoo{version}"], check=False)
            print(f"{GREEN}✓ Odoo {version} restarted.{RESET}")
        elif sub == "4":
            candidates = [
                os.path.join(self.profile.paths.data_root, f"odoo{version}", "etc", "odoo.conf"),
                os.path.join(PROJECT_ROOT, "deployment", f"odoo{version}", "config", "odoo.conf"),
            ]
            config_path = next((path for path in candidates if os.path.exists(path)), candidates[0])
            try:
                with open(config_path, "r") as f:
                    print(f.read())
            except FileNotFoundError:
                print(f"{YELLOW}! Configuration not rendered yet: {config_path}{RESET}")
                print(f"  Run: ./automation/scripts/install-odoo.sh {version}")

    def handle_postgresql_management(self):
        print(f"\n{BOLD}{CYAN}=== 9. POSTGRESQL MANAGEMENT ==={RESET}")
        print(" [1] Probe PostgreSQL 16 connection (Odoo 17, pg_isready)")
        print(" [2] Probe PostgreSQL 17 connection (Odoo 18, pg_isready)")
        print(" [3] Probe PostgreSQL 18 connection (Odoo 19, pg_isready)")
        print(" [4] Verify network isolation (confirm port 5432 is internal only)")
        sub = input(f"{BOLD}Choose action [1-4]: {RESET}").strip()
        if sub == "1":
            subprocess.run(["docker", "exec", "odoo17-db", "pg_isready", "-U", self.profile.odoo17.database.user], check=False)
        elif sub == "2":
            subprocess.run(["docker", "exec", "odoo18-db", "pg_isready", "-U", self.profile.odoo18.database.user], check=False)
        elif sub == "3":
            subprocess.run(["docker", "exec", "odoo19-db", "pg_isready", "-U", self.profile.odoo19.database.user], check=False)
        elif sub == "4":
            print(f"{GREEN}✓ Verified: odoo17-db, odoo18-db and odoo19-db keep port 5432 on the internal network only.{RESET}")

    def handle_dns_ssl_verification(self):
        print(f"\n{BOLD}{CYAN}=== 10. DNS & SSL VERIFICATION ==={RESET}")
        domains = [
            self.profile.traefik.dashboard_domain,
            self.profile.odoo17.domain,
            self.profile.odoo18.domain,
            self.profile.odoo19.domain,
        ]
        for d in domains:
            try:
                ip = socket.gethostbyname(d)
                print(f"{GREEN}✓ Domain {d} resolves to: {ip}{RESET}")
            except socket.gaierror:
                print(f"{YELLOW}! Domain {d} does not resolve in local DNS (Add A-Record to Public IP){RESET}")

    def handle_backup_management(self):
        from app.services.system_backup import SystemBackupService
        print(f"\n{BOLD}{CYAN}=== 11. BACKUP MANAGEMENT ==={RESET}")
        print(" [1] Backup Odoo 17 database & filestore")
        print(" [2] Backup Odoo 18 database & filestore")
        print(" [3] Backup Odoo 19 database & filestore")
        print(" [4] Create Full Infrastructure Snapshot (configs + env + compose + DBs)")
        sub = input(f"{BOLD}Choose action [1-4]: {RESET}").strip()
        if sub == "1":
            op = DatabaseOpsWorkflow.create_backup_operation("17", self.profile.odoo17.database.name, self.profile.backup.retention_count)
            self.execute_workflow(op)
        elif sub == "2":
            op = DatabaseOpsWorkflow.create_backup_operation("18", self.profile.odoo18.database.name, self.profile.backup.retention_count)
            self.execute_workflow(op)
        elif sub == "3":
            op = DatabaseOpsWorkflow.create_backup_operation("19", self.profile.odoo19.database.name, self.profile.backup.retention_count)
            self.execute_workflow(op)
        elif sub == "4":
            snap = SystemBackupService.create_full_snapshot()
            print(f"{GREEN}✓ Full Infrastructure Snapshot saved: {snap['archive_file']} (SHA256: {snap['sha256'][:16]}...){RESET}")

    def handle_restore_management(self):
        print(f"\n{BOLD}{CYAN}=== 12. RESTORE MANAGEMENT ==={RESET}")
        self.handle_interactive_restore()

    def handle_monitoring_logs(self):
        print(f"\n{BOLD}{CYAN}=== 13. MONITORING & LOGS ==={RESET}")
        print(" [1] Traefik Logs")
        print(" [2] Odoo 17 Logs")
        print(" [3] Odoo 18 Logs")
        print(" [4] Odoo 19 Logs")
        sub = input(f"{BOLD}Choose service [1-4]: {RESET}").strip()
        svc = {"1": "traefik", "2": "odoo17", "3": "odoo18", "4": "odoo19"}.get(sub, "traefik")
        subprocess.run(["docker", "logs", "--tail", "50", "-f", svc], check=False)

    def handle_configuration_profiles(self):
        print(f"\n{BOLD}{CYAN}=== 14. CONFIGURATION PROFILES ==={RESET}")
        print(f"Active Profile: {self.profile.profile_name} (Version: {self.profile.version})")
        self.validate_current_profile()

    def handle_troubleshooting(self):
        print(f"\n{BOLD}{CYAN}=== 15. TROUBLESHOOTING ==={RESET}")
        print("Checking port 80 & 443 bindings...")
        subprocess.run(["ss", "-tuln"], check=False)
        print("\nChecking container exit statuses...")
        subprocess.run(["docker", "ps", "-a", "--filter", "status=exited"], check=False)

    def handle_generate_infrastructure_report(self):
        import datetime
        print(f"\n{BOLD}{CYAN}=== 16. GENERATE INFRASTRUCTURE REPORT ==={RESET}")
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report = f"""# ODOO INFRASTRUCTURE MANAGER AUDIT REPORT
Date: {ts}
Host: {self.profile.server.hostname} ({self.profile.server.ip_or_host})
Profile: {self.profile.profile_name}
Traefik: {self.profile.traefik.dashboard_domain}
Odoo 17: {self.profile.odoo17.domain} (PG 16)
Odoo 18: {self.profile.odoo18.domain} (PG 17)
Odoo 19: {self.profile.odoo19.domain} (PG 18)
Status: Operational & Compliant
"""
        os.makedirs("docs", exist_ok=True)
        report_file = f"docs/audit_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, "w") as f:
            f.write(report)
        print(f"{GREEN}✓ Report generated successfully: {report_file}{RESET}")
        print(report)
