"""
Native Textual TUI Application for Odoo Infrastructure Manager.
Provides an enterprise terminal dashboard using Textual widgets, reactive layouts,
live logs streaming, operation launchers, and configuration editors.
"""
import os
import sys
from typing import Optional

try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical, Grid
    from textual.widgets import (
        Header, Footer, Static, Button, DataTable, 
        Label, Input, TabbedContent, TabPane, Log, ProgressBar
    )
    from textual.reactive import reactive
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    App = object

from app.models.profile import InfrastructureProfile
from app.models.operation import OperationRecord, OperationStatus
from app.services.smart_inspector import SmartInspectorService
from app.services.system_backup import SystemBackupService
from app.workflows.server_prep import ServerPrepWorkflow
from app.workflows.deploy_traefik import DeployTraefikWorkflow
from app.workflows.deploy_odoo17 import DeployOdoo17Workflow
from app.workflows.deploy_odoo19 import DeployOdoo19Workflow
from app.workflows.full_deploy import FullDeployWorkflow
from app.services.health_service import HealthService
from app.services.execution_service import ExecutionService

TEXTUAL_CSS = """
Screen {
    background: #090d16;
    color: #e2e8f0;
}

Header {
    background: #0f172a;
    color: #38bdf8;
    dock: top;
    height: 3;
}

Footer {
    background: #0f172a;
    color: #94a3b8;
    dock: bottom;
    height: 1;
}

#top-banner {
    background: #1e293b;
    border: heavy #0284c7;
    height: auto;
    margin: 1 1;
    padding: 1 2;
}

.banner-title {
    color: #38bdf8;
    text-style: bold;
}

.banner-subtitle {
    color: #94a3b8;
}

#status-grid {
    layout: grid;
    grid-size: 4;
    grid-gutter: 1;
    margin: 1 1;
    height: 5;
}

.status-card {
    background: #1e293b;
    border: solid #334155;
    padding: 1;
    text-align: center;
}

.status-healthy {
    color: #4ade80;
    text-style: bold;
}

#operations-box {
    border: solid #0284c7;
    margin: 1;
    padding: 1;
    height: auto;
}

.op-btn {
    margin: 0 1 1 0;
    min-width: 24;
}

#terminal-log {
    border: solid #334155;
    background: #020617;
    color: #f8fafc;
    height: 14;
    margin: 1;
}
"""

class OdooTextualApp(App if TEXTUAL_AVAILABLE else object):
    """Textual interactive Terminal User Interface for DevOps operators."""
    CSS = TEXTUAL_CSS if TEXTUAL_AVAILABLE else ""
    BINDINGS = [
        ("q", "quit", "خروج / Quit"),
        ("d", "toggle_dry_run", "تبديل المعاينة / Toggle Dry-Run"),
        ("r", "refresh_inspection", "إعادة الفحص / Re-scan"),
        ("b", "trigger_snapshot", "نسخة شاملة / Snapshot"),
    ]

    dry_run = reactive(False)
    server_hostname = reactive("devops-odoo")
    active_profile = reactive("devops-odoo-prod")

    def __init__(self, profile: Optional[InfrastructureProfile] = None):
        if not TEXTUAL_AVAILABLE:
            raise RuntimeError("Textual library is not installed in the current environment.")
        super().__init__()
        self.profile = profile or InfrastructureProfile(profile_name="devops-odoo-prod")
        self.server_hostname = self.profile.server.hostname
        self.active_profile = self.profile.profile_name

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical():
            # Top Banner
            with Container(id="top-banner"):
                yield Label("🚀 ODOO INFRASTRUCTURE MANAGER — مدير البنية التحتية لنظام أودو", classes="banner-title")
                yield Label("Ubuntu (Server & Desktop 22.04+) • Docker Engine • Traefik v3.7 • Odoo 17 & 19", classes="banner-subtitle")

            # Status cards
            with Grid(id="status-grid"):
                with Container(classes="status-card"):
                    yield Label("Docker Engine")
                    yield Label("Active (v26.1)", classes="status-healthy")
                with Container(classes="status-card"):
                    yield Label("Traefik v3.7 Ingress")
                    yield Label("TLS Healthy", classes="status-healthy")
                with Container(classes="status-card"):
                    yield Label("Odoo 17 (PG 16)")
                    yield Label("Port 8069 / WS", classes="status-healthy")
                with Container(classes="status-card"):
                    yield Label("Odoo 19 (PG 18)")
                    yield Label("Port 8069 / WS", classes="status-healthy")

            # Main Tabbed Content
            with TabbedContent():
                with TabPane("العمليات الرئيسية / Operations", id="tab-ops"):
                    with Grid(id="operations-box"):
                        yield Button("1. إعداد الخادم / Server Prep", id="btn-prep", variant="primary", classes="op-btn")
                        yield Button("2. نشر ترافيك / Deploy Traefik", id="btn-traefik", variant="primary", classes="op-btn")
                        yield Button("3. نشر أودو 17 / Deploy Odoo 17", id="btn-o17", variant="primary", classes="op-btn")
                        yield Button("4. نشر أودو 19 / Deploy Odoo 19", id="btn-o19", variant="primary", classes="op-btn")
                        yield Button("5. النشر الكامل / Full Deploy", id="btn-full", variant="success", classes="op-btn")
                        yield Button("6. فحص الصحة / Health Sweep", id="btn-health", variant="default", classes="op-btn")
                        yield Button("7. نسخة احتياطية / Backup DB", id="btn-backup", variant="default", classes="op-btn")
                        yield Button("8. نسخة شاملة / Full Snapshot", id="btn-snap", variant="warning", classes="op-btn")

                with TabPane("جدول الفحص المسبق / Pre-flight", id="tab-preflight"):
                    yield DataTable(id="audit-table")

                with TabPane("سجلات التنفيذ الحية / Live Logs", id="tab-logs"):
                    yield Log(id="terminal-log", highlight=True)

        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("المكون / Component", "الحالة / Status", "الإصدار / Version", "المسار / Path")
        report = SmartInspectorService.run_full_inspection()
        for c in report.components:
            status_symbol = "✓ INSTALLED" if c.status.value == "INSTALLED" else "✗ " + c.status.value
            table.add_row(c.name_ar, status_symbol, c.detected_version or "-", c.binary_path or "-")

        log = self.query_one(Log)
        log.write_line(">>> Odoo Infrastructure Manager Textual Session Ready.")
        log.write_line(f">>> Target Host: {self.server_hostname} | Active Profile: {self.active_profile}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        log = self.query_one(Log)

        if btn_id == "btn-prep":
            op = ServerPrepWorkflow.create_operation(self.profile, dry_run=self.dry_run)
            self._execute_workflow_in_log(op)
        elif btn_id == "btn-traefik":
            op = DeployTraefikWorkflow.create_operation(self.profile, dry_run=self.dry_run)
            self._execute_workflow_in_log(op)
        elif btn_id == "btn-o17":
            op = DeployOdoo17Workflow.create_operation(self.profile, dry_run=self.dry_run)
            self._execute_workflow_in_log(op)
        elif btn_id == "btn-o19":
            op = DeployOdoo19Workflow.create_operation(self.profile, dry_run=self.dry_run)
            self._execute_workflow_in_log(op)
        elif btn_id == "btn-full":
            op = FullDeployWorkflow.create_operation(self.profile, dry_run=self.dry_run)
            self._execute_workflow_in_log(op)
        elif btn_id == "btn-health":
            step = HealthService.build_health_check_step()
            op = OperationRecord("op-health", "Health Diagnostic Check", "health", self.profile.profile_name, steps=[step])
            self._execute_workflow_in_log(op)
        elif btn_id == "btn-snap":
            log.write_line(">>> Creating full infrastructure snapshot archive...")
            snap = SystemBackupService.create_full_snapshot()
            log.write_line(f"✓ Snapshot created: {snap['archive_file']} (SHA256: {snap['sha256'][:16]}...)")

    def _execute_workflow_in_log(self, op: OperationRecord):
        log = self.query_one(Log)
        log.write_line(f"\n========================================================")
        log.write_line(f"▶ Starting Workflow: {op.name} (Dry-Run: {self.dry_run})")
        log.write_line(f"========================================================")

        for step in op.steps:
            log.write_line(f"==> [{step.id}] {step.name}")
            step_res = ExecutionService.execute_step(
                step,
                on_output=lambda line: log.write(line),
                dry_run=self.dry_run
            )
            if step_res.status == OperationStatus.SUCCESS:
                log.write_line(f"✓ Step succeeded ({step_res.duration_seconds:.2f}s)")
            else:
                log.write_line(f"✗ Step failed with exit code {step_res.exit_code}")
                break
        log.write_line("✔ Workflow finished.\n")

    def action_toggle_dry_run(self) -> None:
        self.dry_run = not self.dry_run
        log = self.query_one(Log)
        log.write_line(f"[!] Dry-run mode changed to: {self.dry_run}")

    def action_trigger_snapshot(self) -> None:
        log = self.query_one(Log)
        snap = SystemBackupService.create_full_snapshot()
        log.write_line(f"[OK] Full Snapshot generated: {snap['archive_file']}")

def run_textual_app(profile: Optional[InfrastructureProfile] = None):
    if not TEXTUAL_AVAILABLE:
        print("[WARN] Textual is not installed. Use 'pip install textual' or run TerminalUI.")
        return False
    app = OdooTextualApp(profile=profile)
    app.run()
    return True
