#!/usr/bin/env python3
"""
Odoo Infrastructure Manager - Main CLI & TUI Entry Point.
"""
import sys
import os
import argparse

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ui.app import TerminalUI
from app.models.profile import InfrastructureProfile
from app.validators.config_validator import ConfigValidator
from app.workflows.server_prep import ServerPrepWorkflow
from app.workflows.deploy_traefik import DeployTraefikWorkflow
from app.workflows.deploy_odoo17 import DeployOdoo17Workflow
from app.workflows.deploy_odoo18 import DeployOdoo18Workflow
from app.workflows.deploy_odoo19 import DeployOdoo19Workflow
from app.workflows.full_deploy import FullDeployWorkflow
from app.services.health_service import HealthService
from app.services.sequential_installer import SequentialInstaller
from app.models.operation import OperationRecord, OperationStatus

def main():
    parser = argparse.ArgumentParser(
        description="Odoo Infrastructure Manager - Multi-Version Ubuntu/Docker Orchestrator"
    )
    parser.add_argument("--profile", "-p", default="profiles/example.yaml", help="Path to profile YAML file")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Simulate execution without modifying system")
    parser.add_argument("--action", "-a", choices=[
        "tui", "textual", "preflight", "prep", "traefik", "traefik-audit", "traefik-backup",
        "odoo17", "odoo18", "odoo19", "full", "health", "validate", "runtimes", "sequential-install",
        "server-setup", "inspect", "install-report",
    ], default="tui", help="Action to execute directly or launch interactive TUI")
    args = parser.parse_args()

    tui = TerminalUI(profile_path=args.profile)
    tui.dry_run = args.dry_run

    if args.action == "textual":
        from app.ui.textual_app import run_textual_app
        if not run_textual_app(tui.profile, dry_run=args.dry_run):
            tui.show_menu()
    elif args.action == "tui":
        tui.show_menu()
    elif args.action == "preflight":
        tui.run_preflight_checks()
    elif args.action == "runtimes":
        tui.handle_runtime_setup(dry_run=args.dry_run)
    elif args.action == "validate":
        tui.validate_current_profile()
    elif args.action == "prep":
        op = ServerPrepWorkflow.create_operation(tui.profile, dry_run=args.dry_run)
        op = tui.execute_workflow(op, dry_run=args.dry_run)
        if op.status == OperationStatus.FAILED:
            sys.exit(1)
    elif args.action == "traefik":
        op = DeployTraefikWorkflow.create_operation(tui.profile, dry_run=args.dry_run)
        op = tui.execute_workflow(op, dry_run=args.dry_run)
        if op.status == OperationStatus.FAILED:
            sys.exit(1)
    elif args.action == "traefik-audit":
        from app.services.traefik_manager import TraefikDockerManager
        rep = TraefikDockerManager.discover_environment()
        print(f"Traefik Status: {rep.container_status} | Proxy Network: {'OK' if rep.proxy_network_exists else 'MISSING'}")
        print(f"Dashboard URL: {rep.dashboard_url} (Accessible: {rep.dashboard_accessible})")
        for p in rep.ports_audit:
            print(f"Port {p.port}: {'IN USE' if p.is_in_use else 'FREE'} ({p.service_name})")
    elif args.action == "traefik-backup":
        from app.services.traefik_manager import TraefikDockerManager
        snap = TraefikDockerManager.create_backup_snapshot("/opt/traefik")
        print(f"Traefik Snapshot created: {snap['archive_path']} (SHA256: {snap['sha256']})")
    elif args.action == "odoo17":
        op = DeployOdoo17Workflow.create_operation(tui.profile, dry_run=args.dry_run)
        op = tui.execute_workflow(op, dry_run=args.dry_run)
        if op.status == OperationStatus.FAILED:
            sys.exit(1)
    elif args.action == "odoo18":
        op = DeployOdoo18Workflow.create_operation(tui.profile, dry_run=args.dry_run)
        op = tui.execute_workflow(op, dry_run=args.dry_run)
        if op.status == OperationStatus.FAILED:
            sys.exit(1)
    elif args.action == "odoo19":
        op = DeployOdoo19Workflow.create_operation(tui.profile, dry_run=args.dry_run)
        op = tui.execute_workflow(op, dry_run=args.dry_run)
        if op.status == OperationStatus.FAILED:
            sys.exit(1)
    elif args.action == "full":
        op = FullDeployWorkflow.create_operation(tui.profile, dry_run=args.dry_run)
        op = tui.execute_workflow(op, dry_run=args.dry_run)
        if op.status == OperationStatus.FAILED:
            sys.exit(1)
    elif args.action == "health":
        step = HealthService.build_health_check_step()
        op = OperationRecord("op-health", "Health Diagnostic Check", "health", tui.profile.profile_name, steps=[step])
        op = tui.execute_workflow(op, dry_run=args.dry_run)
        if op.status == OperationStatus.FAILED:
            sys.exit(1)
    elif args.action == "sequential-install":
        installer = SequentialInstaller(
            log_dir="/var/log/odoo-installer",
            dry_run=args.dry_run,
            use_sudo=True,
            on_output=lambda msg: print(msg, end=""),
        )
        installer.add_component(
            name="Basic System Packages",
            commands=[
                ["apt-get", "update"],
                ["apt-get", "install", "-y", "curl", "wget", "gnupg", "software-properties-common",
                 "apt-transport-https", "ca-certificates", "python3", "python3-pip",
                 "python3-venv", "git", "vim", "sudo", "ufw", "jq", "tar", "gzip", "zstd"],
            ],
        )
        installer.add_component(
            name="Docker Engine",
            commands=[
                ["install", "-m", "0755", "-d", "/etc/apt/keyrings"],
                ["bash", "-c", "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg"],
                ["chmod", "a+r", "/etc/apt/keyrings/docker.gpg"],
                ["bash", "-c", 'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list >/dev/null'],
                ["apt-get", "update"],
                ["apt-get", "install", "-y", "docker-ce", "docker-ce-cli", "containerd.io", "docker-buildx-plugin", "docker-compose-plugin"],
                ["systemctl", "enable", "docker"],
                ["systemctl", "start", "docker"],
            ],
        )
        installer.add_component(
            name="Ansible",
            commands=[
                ["python3", "-m", "pip", "install", "--upgrade", "pip"],
                ["python3", "-m", "pip", "install", "ansible"],
            ],
        )
        report = installer.run_all()
        print(f"\nSequential installation complete. Report: {report.report_file}")
        print(f"Overall: {report.overall_status.value} | SUCCESS: {report.success_count} | FAILED: {report.failure_count} | SKIPPED: {report.skip_count} | WARNING: {report.warning_count}")
        if report.overall_status == OperationStatus.FAILED:
            sys.exit(1)

    elif args.action == "server-setup":
        from app.core.server_setup import ServerSetupWorkflow
        setup = ServerSetupWorkflow(tui.profile, dry_run=args.dry_run, use_sudo=True)
        result = setup.run_ordered_installation()
        print(f"\nOverall: {'SUCCESS' if result['overall_success'] else 'FAILED'}")
        print(f"  SUCCESS: {result['success_count']} | FAILED: {result['failure_count']} | SKIPPED: {result['skip_count']} | WARNING: {result['warning_count']}")
        if not result['overall_success']:
            sys.exit(1)

    elif args.action == "inspect":
        from app.core.smart_inspector import SmartInspectorService
        inspector = SmartInspectorService().run_full_inspection()
        inspector.print_report()

    elif args.action == "install-report":
        from app.core.server_setup import ServerSetupWorkflow
        setup = ServerSetupWorkflow(tui.profile, dry_run=args.dry_run, use_sudo=True)
        setup.inspect_all()
        print("\nComponent Installation Status:")
        print("  " + "-" * 60)
        for name, record in sorted(setup.components.items()):
            print(f"  [{record.symbol}] {name}: {record.status.value} (version: {record.version or 'N/A'})")


if __name__ == "__main__":
    main()
