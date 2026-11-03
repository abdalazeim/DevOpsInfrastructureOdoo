#!/usr/bin/env python3
"""
Odoo Infrastructure Manager - Main CLI & TUI Entry Point.
"""
import sys
import os
import argparse

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from infrastructure_engine.ui.app import TerminalUI
from infrastructure_engine.models.profile import InfrastructureProfile
from infrastructure_engine.validators.config_validator import ConfigValidator
from infrastructure_engine.workflows.server_prep import ServerPrepWorkflow
from infrastructure_engine.workflows.deploy_traefik import DeployTraefikWorkflow
from infrastructure_engine.workflows.deploy_odoo17 import DeployOdoo17Workflow
from infrastructure_engine.workflows.deploy_odoo18 import DeployOdoo18Workflow
from infrastructure_engine.workflows.deploy_odoo19 import DeployOdoo19Workflow
from infrastructure_engine.workflows.full_deploy import FullDeployWorkflow
from infrastructure_engine.services.health_service import HealthService
from infrastructure_engine.models.operation import OperationRecord

def main():
    parser = argparse.ArgumentParser(
        description="Odoo Infrastructure Manager - Multi-Version Ubuntu/Docker Orchestrator"
    )
    parser.add_argument("--profile", "-p", default="profiles/example.yaml", help="Path to profile YAML file")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Simulate execution without modifying system")
    parser.add_argument("--action", "-a", choices=[
        "tui", "textual", "preflight", "prep", "traefik", "traefik-audit", "traefik-backup",
        "odoo17", "odoo18", "odoo19", "full", "health", "validate", "api"
    ], default="tui", help="Action to execute directly or launch interactive TUI")
    parser.add_argument("--api-host", default=os.environ.get("API_HOST", "127.0.0.1"),
                        help="Bind address for --action api (default: 127.0.0.1)")
    parser.add_argument("--api-port", type=int, default=int(os.environ.get("API_PORT", "8787")),
                        help="Port for --action api (default: 8787)")

    args = parser.parse_args()

    tui = TerminalUI(profile_path=args.profile)

    if args.action == "textual":
        from infrastructure_engine.ui.textual_app import run_textual_app
        if not run_textual_app(tui.profile):
            tui.show_menu()
    elif args.action == "tui":
        tui.show_menu()
    elif args.action == "preflight":
        tui.run_preflight_checks()
    elif args.action == "validate":
        tui.validate_current_profile()
    elif args.action == "prep":
        op = ServerPrepWorkflow.create_operation(tui.profile, dry_run=args.dry_run)
        tui.execute_workflow(op, dry_run=args.dry_run)
    elif args.action == "traefik":
        op = DeployTraefikWorkflow.create_operation(tui.profile, dry_run=args.dry_run)
        tui.execute_workflow(op, dry_run=args.dry_run)
    elif args.action == "traefik-audit":
        from infrastructure_engine.services.traefik_manager import TraefikDockerManager
        rep = TraefikDockerManager.discover_environment()
        print(f"Traefik Status: {rep.container_status} | Proxy Network: {'OK' if rep.proxy_network_exists else 'MISSING'}")
        print(f"Dashboard URL: {rep.dashboard_url} (Accessible: {rep.dashboard_accessible})")
        for p in rep.ports_audit:
            print(f"Port {p.port}: {'IN USE' if p.is_in_use else 'FREE'} ({p.service_name})")
    elif args.action == "traefik-backup":
        from infrastructure_engine.services.traefik_manager import TraefikDockerManager
        snap = TraefikDockerManager.create_backup_snapshot("/opt/traefik")
        print(f"Traefik Snapshot created: {snap['archive_path']} (SHA256: {snap['sha256']})")
    elif args.action == "odoo17":
        op = DeployOdoo17Workflow.create_operation(tui.profile, dry_run=args.dry_run)
        tui.execute_workflow(op, dry_run=args.dry_run)
    elif args.action == "odoo18":
        op = DeployOdoo18Workflow.create_operation(tui.profile, dry_run=args.dry_run)
        tui.execute_workflow(op, dry_run=args.dry_run)
    elif args.action == "odoo19":
        op = DeployOdoo19Workflow.create_operation(tui.profile, dry_run=args.dry_run)
        tui.execute_workflow(op, dry_run=args.dry_run)
    elif args.action == "full":
        op = FullDeployWorkflow.create_operation(tui.profile, dry_run=args.dry_run)
        tui.execute_workflow(op, dry_run=args.dry_run)
    elif args.action == "health":
        step = HealthService.build_health_check_step()
        op = OperationRecord("op-health", "Health Diagnostic Check", "health", tui.profile.profile_name, steps=[step])
        tui.execute_workflow(op, dry_run=args.dry_run)
    elif args.action == "api":
        from app.api_server import run_api_server
        run_api_server(
            host=args.api_host,
            port=args.api_port,
            profile_path=args.profile,
            dry_run=args.dry_run,
        )

if __name__ == "__main__":
    main()
