"""
Installation Pipeline UI - Terminal interface for the sequential installation pipeline.

Follows the existing TUI design patterns from menu_system.py and app.py.
Provides:
- Odoo version selection
- Dependency-aware pipeline progress display
- Per-component verification results
- Final integration report
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from app.core.installation_pipeline import InstallationPipeline

# ANSI color codes (match existing app.py style)
CYAN = "\033[1;36m"
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
RED = "\033[1;31m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"

ODOO_VERSIONS = {
    "17": {"label": "Odoo 17", "port": 10017, "pg_version": "16"},
    "18": {"label": "Odoo 18", "port": 10018, "pg_version": "17"},
    "19": {"label": "Odoo 19", "port": 10019, "pg_version": "18"},
}


class InstallationPipelineUI:
    """Terminal UI for the sequential installation pipeline."""

    def __init__(self, tui_instance):
        self.tui = tui_instance

    def run(self) -> None:
        """Main entry point for the installation pipeline."""
        while True:
            self._display_main_menu()
            choice = input(f"\n{BOLD}Select an option [1-5] or 0 to return: {RESET}").strip()
            if choice == "0":
                break
            elif choice == "1":
                self._select_odoo_version_and_run()
            elif choice == "2":
                self._run_pipeline(odoo_version=None)
            elif choice == "3":
                self._dry_run_pipeline()
            elif choice == "4":
                self._show_last_report()
            elif choice == "5":
                self._show_dependency_graph()
            else:
                print(f"{RED}Invalid selection.{RESET}")
                input(f"\n{DIM}Press Enter to continue...{RESET}")

    def _display_main_menu(self) -> None:
        print(f"\n{CYAN}{BOLD}")
        print("═" * 70)
        print("  SEQUENTIAL INSTALLATION PIPELINE")
        print("═" * 70)
        print(f"{RESET}")
        print(f"{DIM}Dependency-aware installation with per-component verification.{RESET}")
        print(f"{DIM}Each stage verifies before proceeding to the next.{RESET}\n")
        print(f"  {BOLD}1.{RESET} Select Odoo version & run pipeline")
        print(f"  {BOLD}2.{RESET} Run pipeline (no Odoo selection)")
        print(f"  {BOLD}3.{RESET} Dry-run pipeline (no changes)")
        print(f"  {BOLD}4.{RESET} Show last report")
        print(f"  {BOLD}5.{RESET} Show dependency graph")
        print(f"\n  {BOLD}0.{RESET} Return to Main Menu")
        print(f"{CYAN}══════════════════════════════════════════════════════════════════════════════════{RESET}")

    def _select_odoo_version_and_run(self) -> None:
        """Display Odoo version selection screen."""
        print(f"\n{CYAN}{BOLD}SELECT ODOO VERSION{RESET}\n")
        print(f"{DIM}Choose one Odoo version for this installation.{RESET}\n")
        version_keys = list(ODOO_VERSIONS.keys())
        for idx, key in enumerate(version_keys, 1):
            v = ODOO_VERSIONS[key]
            print(f"  {BOLD}{idx}.{RESET} {v['label']}")
            print(f"     {DIM}PostgreSQL {v['pg_version']} | HTTP port {v['port']} | http://localhost:{v['port']}/{RESET}")
        print(f"\n  {BOLD}0.{RESET} Return")
        choice = input(f"\n{BOLD}Select version [1-{len(version_keys)}] or 0 to return: {RESET}").strip()
        if choice == "0":
            return
        if not choice.isdigit() or not (1 <= int(choice) <= len(version_keys)):
            print(f"{RED}Invalid selection.{RESET}")
            input(f"\n{DIM}Press Enter to continue...{RESET}")
            return
        version = version_keys[int(choice) - 1]
        self._run_pipeline(odoo_version=version)

    def _run_pipeline(self, odoo_version: Optional[str] = None) -> None:
        """Run the installation pipeline."""
        print(f"\n{CYAN}{BOLD}SEQUENTIAL INSTALLATION PIPELINE{RESET}")
        if odoo_version:
            v = ODOO_VERSIONS[odoo_version]
            print(f"{DIM}Odoo version: {v['label']} | PostgreSQL {v['pg_version']} | Port {v['port']}{RESET}")
        else:
            print(f"{DIM}No Odoo version selected (Odoo stage will be skipped){RESET}")
        print(f"{DIM}Dry-run: False{RESET}\n")

        confirm = input(f"{BOLD}Proceed with installation? [y/N]: {RESET}").strip().lower()
        if confirm != "y":
            print(f"{YELLOW}Installation cancelled.{RESET}")
            input(f"\n{DIM}Press Enter to continue...{RESET}")
            return

        from copy import deepcopy
        profile = deepcopy(self.tui.profile)
        for version in ('17', '18', '19'):
            getattr(profile, 'odoo' + version).enabled = version == odoo_version
        pipeline = InstallationPipeline(dry_run=getattr(self.tui, 'dry_run', False), use_sudo=True,
                                        on_output=self._pipeline_log, profile=profile, report_dir="reports/installation")
        report = pipeline.run()
        self._display_report(report)
        input(f"\n{DIM}Press Enter to return to pipeline menu...{RESET}")

    def _dry_run_pipeline(self) -> None:
        """Run the pipeline in dry-run mode."""
        print(f"\n{CYAN}{BOLD}DRY-RUN PIPELINE (NO CHANGES){RESET}\n")
        pipeline = InstallationPipeline(dry_run=True, use_sudo=True, on_output=self._pipeline_log, profile=self.tui.profile)
        report = pipeline.run()
        print(f"\n{GREEN}{BOLD}DRY-RUN COMPLETE{RESET}")
        print(f"  Overall: {'SUCCESS' if report['overall_success'] else 'FAILED'}")
        print(f"  Succeeded: {report['success_count']} | Failed: {report['failure_count']} | Skipped: {report['skip_count']}")
        input(f"\n{DIM}Press Enter to continue...{RESET}")

    def _pipeline_log(self, message: str) -> None:
        """Callback for pipeline log output."""
        print(message, end="")

    def _display_report(self, report: Dict[str, Any]) -> None:
        """Display the final pipeline report."""
        print(f"\n{CYAN}{BOLD}=" * 70)
        print("  FINAL INSTALLATION REPORT")
        print("=" * 70)
        print(f"{RESET}")
        print(f"  Generated: {report.get('report_generated_at', 'N/A')}")
        print(f"  Overall: {GREEN if report['overall_success'] else RED}{'SUCCESS' if report['overall_success'] else 'FAILED'}{RESET}")
        print(f"  Succeeded: {report['success_count']} | Failed: {report['failure_count']} | Skipped: {report['skip_count']} | Total: {report['total']}")
        print()

        for stage_name in report["install_order"]:
            record = report["components"].get(stage_name)
            if record is None:
                continue
            status_color = {
                "installed": GREEN,
                "failed": RED,
                "skipped": YELLOW,
                "pending": DIM,
            }.get(record.status.value, DIM)
            print(f"  {status_color}[{record.status.value.upper()}]{RESET} {record.category} - {record.name}")
            if record.error:
                print(f"     {RED}Error: {record.error}{RESET}")
            if record.version:
                print(f"     {DIM}Version: {record.version}{RESET}")
            for step in record.steps:
                step_color = GREEN if step.success else RED
                print(f"     {step_color}[{step.exit_code}] {step.name}{RESET}")
                if step.stderr:
                    print(f"        {DIM}STDERR: {step.stderr[:200]}{RESET}")

        if report["failed"]:
            print(f"\n{RED}FAILED COMPONENTS:{RESET}")
            for r in report["failed"]:
                print(f"  - {r.name}: {r.error or 'Unknown error'}")

        if report["skipped"]:
            print(f"\n{YELLOW}SKIPPED COMPONENTS (dependency blocked):{RESET}")
            for r in report["skipped"]:
                print(f"  - {r.name}: {r.skip_reason or 'Dependency failed'}")

    def _show_last_report(self) -> None:
        print(f"\n{YELLOW}No saved report available yet. Run the pipeline first.{RESET}")
        input(f"\n{DIM}Press Enter to continue...{RESET}")

    def _show_dependency_graph(self) -> None:
        """Display the dependency graph."""
        print(f"\n{CYAN}{BOLD}DEPENDENCY GRAPH{RESET}\n")
        pipeline = InstallationPipeline()
        for comp in pipeline._component_defs:
            deps = comp.get("depends_on", [])
            dep_str = f" <- {', '.join(deps)}" if deps else ""
            print(f"  {comp['label']}{dep_str}")
        print()
        input(f"{DIM}Press Enter to continue...{RESET}")
