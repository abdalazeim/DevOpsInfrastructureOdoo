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
        "server-setup", "inspect", "install-report", "final-workflow",
    ], default="tui", help="Action to execute directly or launch interactive TUI")
    parser.add_argument('--odoo-version', choices=['17', '18', '19'])
    parser.add_argument('--mode', choices=['local', 'domain'], default=None)
    parser.add_argument('--http-port', type=int)
    parser.add_argument('--apply', action='store_true', help='Apply installation in final-workflow; default is read-only verification')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--report-dir', default='reports/final-workflow')
    args = parser.parse_args()

    tui = TerminalUI(profile_path=args.profile)
    tui.dry_run = args.dry_run
    if args.action in ('final-workflow', 'server-setup', 'sequential-install') and not args.odoo_version:
        parser.error('--odoo-version is required; no automatic installation of every Odoo version')
    if args.odoo_version:
        for version in ('17', '18', '19'):
            getattr(tui.profile, 'odoo' + version).enabled = version == args.odoo_version
        if args.http_port:
            if not 1024 <= args.http_port <= 65535:
                parser.error('--http-port must be in 1024..65535')
            getattr(tui.profile, 'odoo' + args.odoo_version).http_port = args.http_port
    if args.mode:
        tui.profile.deployment_mode = args.mode
    if args.action == 'final-workflow':
        from app.core.final_workflow import FinalWorkflow
        report = FinalWorkflow(tui.profile, args.report_dir, args.dry_run, args.apply, args.resume).run()
        print(report['status'])
        if not args.dry_run and report['status'] == 'NOT READY':
            sys.exit(1)
        return
    if args.dry_run and args.action in ('tui', 'preflight'):
        from app.core.installation_pipeline import InstallationPipeline
        report = InstallationPipeline(dry_run=True, profile=tui.profile, on_output=print).run()
        print('DRY RUN: commands planned; infrastructure not modified or verified.')
        return


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
        if args.dry_run:
            print("DRY RUN: would archive Traefik configuration; no files written")
            return
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
        from app.core.installation_pipeline import InstallationPipeline
        report = InstallationPipeline(profile=tui.profile, dry_run=args.dry_run, use_sudo=True, on_output=print).run()
        print(f"Planned only: {args.dry_run}; success: {report['overall_success']}")
        if not args.dry_run and not report['overall_success']:
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
