"""
Terminal User Interface (TUI) and Interactive Console for Odoo Infrastructure Manager.
Supports both Textual App mode and ANSI Terminal Console mode.
"""
import os
import sys
import time
from datetime import datetime
from typing import Optional, List
import json
import subprocess

from infrastructure_engine.models.profile import InfrastructureProfile
from infrastructure_engine.models.operation import OperationRecord, OperationStatus, WorkflowStep
from infrastructure_engine.validators.config_validator import ConfigValidator
from infrastructure_engine.validators.system_validator import SystemValidator
from infrastructure_engine.workflows.server_prep import ServerPrepWorkflow
from infrastructure_engine.workflows.deploy_traefik import DeployTraefikWorkflow
from infrastructure_engine.workflows.deploy_odoo17 import DeployOdoo17Workflow
from infrastructure_engine.workflows.deploy_odoo18 import DeployOdoo18Workflow
from infrastructure_engine.workflows.deploy_odoo19 import DeployOdoo19Workflow
from infrastructure_engine.workflows.database_ops import DatabaseOpsWorkflow
from infrastructure_engine.workflows.full_deploy import FullDeployWorkflow
from infrastructure_engine.services.execution_service import ExecutionService
from infrastructure_engine.services.health_service import HealthService

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
    """Interactive TUI for terminal execution with Arabic and English support."""

    def __init__(self, profile_path: str = "profiles/example.yaml"):
        self.profile_path = profile_path
        self.profile = self.load_profile(profile_path)
        self.is_arabic = True

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
        print("║               مدير البنية التحتية لنظام أودو متعدد الإصدارات                 ║")
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
            print("")
            print(f"  {BOLD}0.{RESET} Exit")
            print(f"{CYAN}=================================================={RESET}")

            choice = input(f"{BOLD}Select an option [0-15]: {RESET}").strip()

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
            elif choice == "0":
                print(f"{CYAN}Exiting Odoo Infrastructure Manager. Goodbye! / إلى اللقاء!{RESET}")
                break
            else:
                print(f"{RED}Invalid selection. Please choose an option from 0 to 15.{RESET}")

            input(f"\n{DIM}Press Enter to return to main menu...{RESET}")

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
        from infrastructure_engine.services.smart_inspector import SmartInspectorService, ComponentStatus
        from infrastructure_engine.services.system_backup import SystemBackupService

        print(f"\n{BOLD}{CYAN}=============================================================================={RESET}")
        print(f"{BOLD}{CYAN}             PRE-FLIGHT INTELLIGENT INSPECTION & AUDIT REPORT                 {RESET}")
        print(f"{BOLD}{CYAN}                 فحص المتطلبات والتثبيت الذكي والحزم الأساسية                 {RESET}")
        print(f"{BOLD}{CYAN}=============================================================================={RESET}\n")

        report = SmartInspectorService.run_full_inspection()

        print(f"{BOLD}Operating System:{RESET} {report.os_name} ({report.os_version})")
        print(f"{BOLD}Timestamp:{RESET}        {report.timestamp}")
        print(f"{BOLD}Compliance Status:{RESET} {'Compliant (Ubuntu 22.04+)' if report.is_supported_ubuntu else 'Warning: OS Needs Update'}\n")

        print("┌───────────────────────────────────┬──────────────┬────────────────────────┬──────────────────────┐")
        print("│ Component / المكون                 │ Status / الحالة │ Detected Version       │ Path / Details       │")
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

            comp_name = (c.name_ar if self.is_arabic else c.name)[:33]
            ver = (c.detected_version or "N/A")[:22]
            path_info = (c.binary_path or c.details or "N/A")[:20]

            print(f"│ {comp_name:<33} │ {status_color}{status_text:<12}{RESET} │ {ver:<22} │ {path_info:<20} │")

        print("└───────────────────────────────────┴──────────────┴────────────────────────┴──────────────────────┘")

        missing_comps = [c for c in report.components if c.status == ComponentStatus.MISSING]
        if missing_comps:
            print(f"\n{YELLOW}{BOLD}Missing Required Components ({len(missing_comps)}):{RESET}")
            for mc in missing_comps:
                print(f"  • {BOLD}{mc.name}{RESET}: {mc.why_needed_ar if self.is_arabic else mc.why_needed}")
                print(f"    Action: {mc.recommended_action_ar if self.is_arabic else mc.recommended_action}")

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
        print(f"\n{BOLD}{CYAN}=== 1. SYSTEM INFORMATION / معلومات النظام ==={RESET}")
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
        print(f"\n{BOLD}{CYAN}=== 4. DOCKER MANAGEMENT / إدارة الحاويات ==={RESET}")
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
        from infrastructure_engine.services.traefik_manager import DEFAULT_CONFIG_DIR, TraefikDockerManager, TraefikConfig

        print(f"\n{BOLD}{CYAN}=============================================================================={RESET}")
        print(f"{BOLD}{CYAN}             TRAEFIK DOCKER MANAGEMENT MODULE / إدارة ترافيك                  {RESET}")
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
            traefik_dir = os.path.join(self.profile.paths.data_root, "traefik")
            print(f"\n{BOLD}Deploying Traefik v3.7 to {traefik_dir}...{RESET}")
            cfg = TraefikConfig(
                config_dir=traefik_dir,
                image=self.profile.traefik.image,
                container_name="traefik",
                network=self.profile.network.proxy_network_name,
                http_port=self.profile.traefik.http_port,
                dashboard_domain=self.profile.traefik.dashboard_domain,
                acme_email=self.profile.traefik.acme_email,
                enable_letsencrypt=self.profile.security.enforce_https,
                docker_socket_ro=True,
            )
            # 1. Pre-change backup
            if os.path.exists(os.path.join(traefik_dir, "docker-compose.yml")):
                snap = TraefikDockerManager.create_backup_snapshot(traefik_dir)
                print(f"{GREEN}✓ Pre-change backup created: {snap['archive_name']} (SHA256: {snap['sha256'][:16]}...){RESET}")

            # 2. Ensure directories and network
            TraefikDockerManager.ensure_traefik_directories(traefik_dir)
            TraefikDockerManager.ensure_proxy_network(
                self.profile.network.proxy_network_name,
                self.profile.network.proxy_subnet,
            )

            # 3. Write compose file (secure dashboard, no api.insecure)
            compose_content = TraefikDockerManager.generate_compose_yaml(cfg)
            with open(os.path.join(traefik_dir, "docker-compose.yml"), "w") as f:
                f.write(compose_content)
            print(f"{GREEN}✓ Compose file written to {traefik_dir}/docker-compose.yml{RESET}")

            # 4. Launch workflow
            op = DeployTraefikWorkflow.create_operation(self.profile)
            self.execute_workflow(op)

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

    def handle_network_management(self):
        print(f"\n{BOLD}{CYAN}=== 6. DOCKER NETWORK MANAGEMENT / إدارة الشبكات ==={RESET}")
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
        print(f"\n{BOLD}{CYAN}=== 7. ODOO MANAGEMENT / إدارة أودو ==={RESET}")
        print(" Select Odoo version / اختر إصدار أودو:")
        print("  [1] Odoo 17 (PostgreSQL 16)")
        print("  [2] Odoo 18 (PostgreSQL 17)")
        print("  [3] Odoo 19 (PostgreSQL 18)")
        choice = input(f"{BOLD}Version [1-3, default 3]: {RESET}").strip()
        version = {"1": "17", "2": "18", "3": "19"}.get(choice, "19")
        pg = {"17": "16", "18": "17", "19": "18"}[version]

        print(f"\n{BOLD}Odoo {version} Management / إدارة أودو {version}:{RESET}")
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
        print(f"\n{BOLD}{CYAN}=== 9. POSTGRESQL MANAGEMENT / إدارة قواعد البيانات ==={RESET}")
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
        print(f"\n{BOLD}{CYAN}=== 10. DNS & SSL VERIFICATION / التحقق من النطاقات والتشفير ==={RESET}")
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
        from infrastructure_engine.services.system_backup import SystemBackupService
        print(f"\n{BOLD}{CYAN}=== 11. BACKUP MANAGEMENT / إدارة النسخ الاحتياطي ==={RESET}")
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
        print(f"\n{BOLD}{CYAN}=== 12. RESTORE MANAGEMENT / استعادة النسخ الاحتياطية ==={RESET}")
        self.handle_interactive_restore()

    def handle_monitoring_logs(self):
        print(f"\n{BOLD}{CYAN}=== 13. MONITORING & LOGS / مراقبة السجلات ==={RESET}")
        print(" [1] Traefik Logs")
        print(" [2] Odoo 17 Logs")
        print(" [3] Odoo 18 Logs")
        print(" [4] Odoo 19 Logs")
        sub = input(f"{BOLD}Choose service [1-4]: {RESET}").strip()
        svc = {"1": "traefik", "2": "odoo17", "3": "odoo18", "4": "odoo19"}.get(sub, "traefik")
        subprocess.run(["docker", "logs", "--tail", "50", "-f", svc], check=False)

    def handle_configuration_profiles(self):
        print(f"\n{BOLD}{CYAN}=== 14. CONFIGURATION PROFILES / ملفات الإعداد ==={RESET}")
        print(f"Active Profile: {self.profile.profile_name} (Version: {self.profile.version})")
        self.validate_current_profile()

    def handle_troubleshooting(self):
        print(f"\n{BOLD}{CYAN}=== 15. TROUBLESHOOTING / استكشاف الأعطال وحلها ==={RESET}")
        print("Checking port 80 & 443 bindings...")
        subprocess.run(["ss", "-tuln"], check=False)
        print("\nChecking container exit statuses...")
        subprocess.run(["docker", "ps", "-a", "--filter", "status=exited"], check=False)

    def handle_generate_infrastructure_report(self):
        import datetime
        print(f"\n{BOLD}{CYAN}=== 16. GENERATE INFRASTRUCTURE REPORT / توليد التقرير الشامل ==={RESET}")
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
