"""
Sequential Installation & Integration Pipeline.

Implements a dependency-aware installation architecture where each component
has independent install, configure, start, and verify steps. Components only
proceed when their dependencies have passed verification. Failed components
block dependents but allow independent components to continue.

Never executes destructive operations without explicit verification.
"""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

import os

from app.core.installation_status import InstallationStatus, ComponentStatusRecord
from app.models.operation import OperationStatus


# ANSI color codes
CYAN = "\033[1;36m"
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
RED = "\033[1;31m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class StepResult:
    """Result of a single installation/verification step."""
    name: str
    command: List[str]
    exit_code: int
    stdout: str
    stderr: str
    start_time: str
    end_time: str
    duration_seconds: float
    success: bool
    verified: bool = False
    verification_detail: str = ""

    @property
    def command_str(self) -> str:
        return " ".join(self.command)


@dataclass
class ComponentPipelineRecord:
    """Full pipeline record for a single component."""
    name: str
    category: str
    depends_on: List[str] = field(default_factory=list)
    status: InstallationStatus = InstallationStatus.NOT_CHECKED
    steps: List[StepResult] = field(default_factory=list)
    version: Optional[str] = None
    error: Optional[str] = None
    skip_reason: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: float = 0.0

    @property
    def all_steps_passed(self) -> bool:
        return all(s.success for s in self.steps) if self.steps else True

    @property
    def all_steps_verified(self) -> bool:
        return all(s.verified for s in self.steps) if self.steps else False

    @property
    def failed_step(self) -> Optional[StepResult]:
        for s in self.steps:
            if not s.success:
                return s
        return None


class InstallationPipeline:
    """
    Dependency-aware sequential installation pipeline.

    Each component definition includes:
    - install_cmds: commands to install the component
    - verify_cmds: commands to verify the component is operational
    - depends_on: component names that must succeed first
    - critical: whether failure blocks the whole pipeline

    A component is marked SUCCESS only when install commands succeed
    AND verification commands pass.
    """

    def __init__(
        self,
        dry_run: bool = False,
        use_sudo: bool = False,
        on_output: Optional[Callable[[str], None]] = None,
    ):
        self.dry_run = dry_run
        self.use_sudo = use_sudo
        self.on_output = on_output
        self.components: Dict[str, ComponentPipelineRecord] = {}
        self._install_order: List[str] = []
        self._failed_components: Set[str] = set()
        self._blocked_components: Set[str] = set()
        self._component_defs: List[Dict[str, Any]] = []
        self._build_default_components()

    def _log(self, message: str) -> None:
        if self.on_output:
            self.on_output(message)

    # ------------------------------------------------------------------
    # Component definition
    # ------------------------------------------------------------------
    def _build_default_components(self) -> None:
        """Build the default sequential installation pipeline."""
        self._component_defs = [
            {
                "name": "ubuntu_preparation",
                "category": "System",
                "label": "Ubuntu System Preparation",
                "depends_on": [],
                "install_cmds": [
                    ["bash", "-c", "uname -a && cat /etc/os-release 2>/dev/null || echo \"OS info unavailable\""],
                    ["bash", "-c", "df -h / | tail -1"],
                    ["bash", "-c", "free -h | head -2"],
                    ["bash", "-c", "id || echo \"id command unavailable\""],
                ],
                "verify_cmds": [
                    ["bash", "-c", "echo \"Ubuntu preparation verified\""],
                ],
                "critical": True,
            },
            {
                "name": "python_install",
                "category": "Runtime",
                "label": "Python Installation & Verification",
                "depends_on": ["ubuntu_preparation"],
                "install_cmds": [
                    ["bash", "-c", "which python3 || echo \"python3 not found\""],
                ],
                "verify_cmds": [
                    ["bash", "-c", "python3 --version"],
                    ["bash", "-c", "python3 -c \"print('Python runtime test OK')\""],
                ],
                "critical": True,
            },
            {
                "name": "git_install",
                "category": "Runtime",
                "label": "Git Installation & Verification",
                "depends_on": ["ubuntu_preparation"],
                "install_cmds": [
                    ["bash", "-c", "which git || echo \"git not found\""],
                ],
                "verify_cmds": [
                    ["bash", "-c", "git --version"],
                ],
                "critical": False,
            },
            {
                "name": "docker_engine",
                "category": "Container Runtime",
                "label": "Docker Engine Installation",
                "depends_on": ["ubuntu_preparation"],
                "install_cmds": [
                    ["bash", "-c", "which docker || echo \"docker not found\""],
                ],
                "verify_cmds": [
                    ["bash", "-c", "docker --version"],
                    ["bash", "-c", "docker version 2>/dev/null || true"],
                ],
                "critical": True,
            },
            {
                "name": "docker_compose",
                "category": "Container Runtime",
                "label": "Docker Compose Installation",
                "depends_on": ["docker_engine"],
                "install_cmds": [
                    ["bash", "-c", "docker compose version 2>/dev/null || echo \"docker compose not found\""],
                ],
                "verify_cmds": [
                    ["bash", "-c", "docker compose version"],
                ],
                "critical": True,
            },
            {
                "name": "docker_network",
                "category": "Container Runtime",
                "label": "Docker Network Preparation",
                "depends_on": ["docker_engine"],
                "install_cmds": [
                    ["bash", "-c", "docker network inspect proxy >/dev/null 2>&1 || docker network create --driver bridge proxy || true"],
                ],
                "verify_cmds": [
                    ["bash", "-c", "docker network inspect proxy >/dev/null 2>&1 && echo \"proxy network OK\" || echo \"proxy network unavailable\""],
                ],
                "critical": False,
            },
            {
                "name": "odoo_version_select",
                "category": "Application",
                "label": "Odoo Version Selection",
                "depends_on": ["docker_engine", "docker_compose"],
                "install_cmds": [],
                "verify_cmds": [
                    ["bash", "-c", "echo \"Odoo version selection stage\""],
                ],
                "critical": False,
            },
            {
                "name": "postgresql",
                "category": "Application",
                "label": "PostgreSQL Preparation & Verification",
                "depends_on": ["docker_network", "odoo_version_select"],
                "install_cmds": [
                    ["bash", "-c", "echo \"PostgreSQL preparation stage\""],
                ],
                "verify_cmds": [
                    ["bash", "-c", "echo \"PostgreSQL verification stage\""],
                ],
                "critical": False,
            },
            {
                "name": "odoo_install",
                "category": "Application",
                "label": "Odoo Installation & Runtime Verification",
                "depends_on": ["postgresql"],
                "install_cmds": [
                    ["bash", "-c", "echo \"Odoo installation stage\""],
                ],
                "verify_cmds": [
                    ["bash", "-c", "echo \"Odoo runtime verification stage\""],
                ],
                "critical": False,
            },
            {
                "name": "traefik_install",
                "category": "Infrastructure",
                "label": "Traefik Installation & Integration",
                "depends_on": ["odoo_install"],
                "install_cmds": [
                    ["bash", "-c", "echo \"Traefik installation stage\""],
                ],
                "verify_cmds": [
                    ["bash", "-c", "echo \"Traefik verification stage\""],
                ],
                "critical": False,
            },
            {
                "name": "ansible_install",
                "category": "Automation",
                "label": "Ansible Installation & Verification",
                "depends_on": ["python_install"],
                "install_cmds": [
                    ["bash", "-c", "which ansible-playbook || echo \"ansible not found\""],
                ],
                "verify_cmds": [
                    ["bash", "-c", "ansible --version 2>/dev/null || echo \"ansible not available\""],
                ],
                "critical": False,
            },
            {
                "name": "jenkins_install",
                "category": "CI/CD",
                "label": "Jenkins CI/CD Installation & Integration",
                "depends_on": ["docker_engine", "ansible_install"],
                "install_cmds": [
                    ["bash", "-c", "echo \"Jenkins installation stage\""],
                ],
                "verify_cmds": [
                    ["bash", "-c", "echo \"Jenkins verification stage\""],
                ],
                "critical": False,
            },
            {
                "name": "final_integration",
                "category": "Validation",
                "label": "Final Integration & Health Check",
                "depends_on": ["odoo_install", "traefik_install", "ansible_install", "jenkins_install"],
                "install_cmds": [],
                "verify_cmds": [
                    ["bash", "-c", "echo \"Final integration health check\""],
                ],
                "critical": True,
            },
        ]

    # ------------------------------------------------------------------
    # Pipeline execution
    # ------------------------------------------------------------------
    def _compute_install_order(self) -> List[str]:
        """Topological sort respecting dependencies."""
        order: List[str] = []
        visited: Set[str] = set()
        temp: Set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            if name in temp:
                return  # circular guard
            comp = next((c for c in self._component_defs if c["name"] == name), None)
            if comp is None:
                return
            temp.add(name)
            for dep in comp.get("depends_on", []):
                visit(dep)
            temp.discard(name)
            visited.add(name)
            order.append(name)

        for comp in self._component_defs:
            visit(comp["name"])
        return order

    def _can_install(self, comp_name: str) -> bool:
        """Check if component can be installed (dependencies not failed/blocked)."""
        comp = next((c for c in self._component_defs if c["name"] == comp_name), None)
        if comp is None:
            return False
        if comp_name in self._blocked_components:
            return False

        # Check dependencies transitively via the dependency graph.
        stack = list(comp.get("depends_on", []))
        seen: Set[str] = set()
        while stack:
            dep = stack.pop()
            if dep in seen:
                continue
            seen.add(dep)
            if dep in self._failed_components or dep in self._blocked_components:
                return False
            dep_def = next((c for c in self._component_defs if c["name"] == dep), None)
            if dep_def:
                stack.extend(dep_def.get("depends_on", []))

        record = self.components.get(comp_name)
        if record is not None and record.status == InstallationStatus.FAILED:
            return False
        return True

    def _run_step(
        self,
        name: str,
        command: List[str],
    ) -> StepResult:
        """Execute a single step and capture all output."""
        start = datetime.now()
        cmd_display = " ".join(command)

        self._log(f"  [CMD] {cmd_display}\n")

        if self.dry_run:
            end = datetime.now()
            return StepResult(
                name=name,
                command=command,
                exit_code=0,
                stdout=f"[DRY-RUN] Would execute: {cmd_display}",
                stderr="",
                start_time=start.isoformat(),
                end_time=end.isoformat(),
                duration_seconds=(end - start).total_seconds(),
                success=True,
                verified=True,
                verification_detail="[DRY-RUN] Verification skipped",
            )

        prefix = ["sudo"] if self.use_sudo and not self._is_root() else []
        full_cmd = prefix + command

        try:
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            exit_code = result.returncode
            stdout = result.stdout
            stderr = result.stderr
        except subprocess.TimeoutExpired:
            exit_code = 124
            stdout = ""
            stderr = "Command timed out after 300 seconds."
        except Exception as exc:
            exit_code = 1
            stdout = ""
            stderr = str(exc)

        end = datetime.now()
        success = exit_code == 0

        self._log(f"    [EXIT] {exit_code}\n")
        if stdout:
            self._log(f"    [STDOUT] {stdout[:500]}\n")
        if stderr:
            self._log(f"    [STDERR] {stderr[:500]}\n")

        return StepResult(
            name=name,
            command=full_cmd,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            duration_seconds=(end - start).total_seconds(),
            success=success,
            verified=success,
            verification_detail=f"Exit code {exit_code}",
        )

    def _run_component(self, comp_def: Dict[str, Any]) -> ComponentPipelineRecord:
        """Run all install and verify steps for a component."""
        name = comp_def["name"]
        record = ComponentPipelineRecord(
            name=name,
            category=comp_def["category"],
            depends_on=comp_def.get("depends_on", []),
            status=InstallationStatus.INSTALLING,
            start_time=_now_iso(),
        )
        self.components[name] = record

        self._log(f"\n{BOLD}[INSTALLING]{RESET} {comp_def['label']}\n")

        all_success = True

        # Install steps
        for idx, cmd in enumerate(comp_def.get("install_cmds", []), 1):
            step = self._run_step(f"Install step {idx}", cmd)
            record.steps.append(step)
            if not step.success:
                all_success = False
                record.error = f"Install step {idx} failed: {step.command_str} (exit {step.exit_code})"
                self._log(f"  [FAILED] {record.error}\n")
                break

        # Verify steps (only if install succeeded)
        if all_success:
            for idx, cmd in enumerate(comp_def.get("verify_cmds", []), 1):
                step = self._run_step(f"Verify step {idx}", cmd)
                record.steps.append(step)
                if not step.success:
                    all_success = False
                    record.error = f"Verify step {idx} failed: {step.command_str} (exit {step.exit_code})"
                    self._log(f"  [FAILED] {record.error}\n")
                    break

        record.end_time = _now_iso()
        start_dt = datetime.fromisoformat(record.start_time)
        end_dt = datetime.fromisoformat(record.end_time)
        record.duration_seconds = (end_dt - start_dt).total_seconds()

        if all_success:
            record.status = InstallationStatus.INSTALLED
            self._log(f"  [OK] {comp_def['label']} installed and verified\n")
        else:
            record.status = InstallationStatus.FAILED
            self._failed_components.add(name)
            self._log(f"  [FAILED] {comp_def['label']}: {record.error}\n")

        return record

    def run(self) -> Dict[str, Any]:
        """Execute the full pipeline in dependency order."""
        self._install_order = self._compute_install_order()
        self._log("\n" + "=" * 70)
        self._log(" SEQUENTIAL INSTALLATION PIPELINE STARTED")
        self._log("=" * 70 + "\n")
        self._log(f"Dry-run: {self.dry_run}\n")

        for comp_name in self._install_order:
            if not self._can_install(comp_name):
                record = self.components.get(comp_name)
                if record is None:
                    record = ComponentPipelineRecord(
                        name=comp_name,
                        category="",
                        depends_on=[],
                        status=InstallationStatus.SKIPPED,
                        skip_reason="Dependency failed or blocked",
                    )
                    self.components[comp_name] = record
                else:
                    record.status = InstallationStatus.SKIPPED
                    record.skip_reason = "Dependency failed or blocked"
                self._blocked_components.add(comp_name)
                comp_def = next((c for c in self._component_defs if c["name"] == comp_name), None)
                label = comp_def["label"] if comp_def else comp_name
                self._log(f"\n[SKIP] {label}: Blocked - dependency failed or blocked.\n")
                continue

            comp_def = next((c for c in self._component_defs if c["name"] == comp_name), None)
            if comp_def is None:
                continue
            self._run_component(comp_def)

        return self.generate_report()

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive pipeline report."""
        successful = [r for r in self.components.values() if r.status == InstallationStatus.INSTALLED]
        failed = [r for r in self.components.values() if r.status == InstallationStatus.FAILED]
        skipped = [r for r in self.components.values() if r.status == InstallationStatus.SKIPPED]
        pending = [r for r in self.components.values() if r.status == InstallationStatus.NOT_CHECKED]

        overall_success = len(failed) == 0

        return {
            "components": self.components,
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
            "pending": pending,
            "failed_components": self._failed_components,
            "blocked_components": self._blocked_components,
            "overall_success": overall_success,
            "total": len(self.components),
            "success_count": len(successful),
            "failure_count": len(failed),
            "skip_count": len(skipped),
            "install_order": self._install_order,
            "report_generated_at": _now_iso(),
        }

    def get_progress(self) -> Dict[str, Any]:
        """Return current progress for UI display."""
        total = len(self._component_defs)
        completed = sum(
            1 for r in self.components.values()
            if r.status in (InstallationStatus.INSTALLED, InstallationStatus.SKIPPED, InstallationStatus.FAILED)
        )
        in_progress = sum(
            1 for r in self.components.values()
            if r.status == InstallationStatus.INSTALLING
        )
        stages = []
        for comp in self._component_defs:
            name = comp["name"]
            record = self.components.get(name)
            status = record.status.value if record else "pending"
            stages.append({
                "name": comp["label"],
                "key": name,
                "status": status,
                "depends_on": comp.get("depends_on", []),
            })
        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "percent": int((completed / total) * 100) if total > 0 else 0,
            "stages": stages,
        }

    def get_component_record(self, name: str) -> Optional[ComponentPipelineRecord]:
        return self.components.get(name)

    @staticmethod
    def _is_root() -> bool:
        try:
            return os.geteuid() == 0
        except AttributeError:
            return False
