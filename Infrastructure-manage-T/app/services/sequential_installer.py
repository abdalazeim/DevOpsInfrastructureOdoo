"""
Sequential Installation & Error Reporting Service.

Provides a reliable installation workflow for all system components:
- Executes installation commands sequentially in defined order
- Continues installing remaining components if one fails
- Tracks individual command success/failure per component
- Captures command, exit code, stdout, stderr, timestamp for every failed command
- Detects already-installed components and skips or updates safely
- Generates a comprehensive final installation report
- Status indicators: SUCCESS, FAILED, SKIPPED, WARNING
"""

from __future__ import annotations

import os
import subprocess
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional

from app.models.operation import OperationStatus, WorkflowStep
from app.services.execution_service import ExecutionService


@dataclass
class CommandResult:
    """Result of executing a single installation command."""
    command: List[str]
    exit_code: int
    stdout: str
    stderr: str
    start_time: str
    end_time: str
    duration_seconds: float
    success: bool

    @property
    def command_str(self) -> str:
        return " ".join(self.command)


@dataclass
class ComponentRecord:
    """Record of installation results for a single component."""
    name: str
    status: OperationStatus = OperationStatus.PENDING
    version: Optional[str] = None
    commands: List[CommandResult] = field(default_factory=list)
    log_file: Optional[str] = None
    skip_reason: Optional[str] = None
    error_summary: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: float = 0.0

    @property
    def failed_commands(self) -> List[CommandResult]:
        return [c for c in self.commands if not c.success]

    @property
    def command_count(self) -> int:
        return len(self.commands)

    @property
    def success_count(self) -> int:
        return sum(1 for c in self.commands if c.success)


class ComponentInstaller:
    """
    Installs a single component by executing its commands sequentially.
    Tracks per-command results and captures full telemetry for failures.
    """

    def __init__(
        self,
        name: str,
        commands: List[List[str]],
        check_installed: Optional[Callable[[], tuple[bool, Optional[str]]]] = None,
        log_dir: str = "/var/log/odoo-installer",
        dry_run: bool = False,
        use_sudo: bool = False,
        on_output: Optional[Callable[[str], None]] = None,
    ):
        self.name = name
        self.commands = commands
        self.check_installed = check_installed
        self.log_dir = log_dir
        self.dry_run = dry_run
        self.use_sudo = use_sudo
        self.on_output = on_output
        self._lock = threading.Lock()

    def _log(self, message: str) -> None:
        if self.on_output:
            with self._lock:
                self.on_output(message)

    def _is_installed(self) -> tuple[bool, Optional[str]]:
        """Check if component is already installed. Returns (installed, version)."""
        if self.check_installed:
            return self.check_installed()
        return False, None

    def _prepare_log_file(self) -> str:
        # F20: Ensure log directory is writable; use sudo when configured.
        if self.use_sudo and not self._is_root():
            import subprocess as _sp
            _sp.run(["sudo", "mkdir", "-p", self.log_dir], check=False)
        else:
            os.makedirs(self.log_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = self.name.replace(" ", "_").replace("/", "_")
        return os.path.join(self.log_dir, f"install_{safe_name}_{ts}.log")

    def _run_command(self, command: List[str], log_file: str) -> CommandResult:
        """Execute a single command and capture all output."""
        start = datetime.now()
        cmd_display = " ".join(command)

        prefix = ["sudo"] if self.use_sudo and not self._is_root() else []
        full_cmd = prefix + command

        self._log(f"  [CMD] {cmd_display}\n")

        if self.dry_run:
            end = datetime.now()
            return CommandResult(
                command=full_cmd,
                exit_code=0,
                stdout=f"[DRY-RUN] Would execute: {cmd_display}",
                stderr="",
                start_time=start.isoformat(),
                end_time=end.isoformat(),
                duration_seconds=(end - start).total_seconds(),
                success=True,
            )

        stdout_chunks: List[str] = []
        stderr_chunks: List[str] = []
        output_lock = threading.Lock()

        def drain(stream, chunks: List[str], prefix_tag: str = ""):
            try:
                for line in iter(stream.readline, ""):
                    chunks.append(line)
                    with output_lock:
                        self._log(f"    {prefix_tag}{line}")
            finally:
                try:
                    stream.close()
                except Exception:
                    pass

        try:
            process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                # F20: Create a new process group so we can kill children on timeout.
                start_new_session=True,
            )

            stdout_thread = threading.Thread(
                target=drain, args=(process.stdout, stdout_chunks, ""), daemon=True
            )
            stderr_thread = threading.Thread(
                target=drain, args=(process.stderr, stderr_chunks, "[STDERR] "), daemon=True
            )
            stdout_thread.start()
            stderr_thread.start()

            try:
                process.wait(timeout=300)
                exit_code = process.returncode
            except subprocess.TimeoutExpired:
                # F20: Kill the whole process group, not just the direct process.
                try:
                    import signal as _sig
                    os.killpg(os.getpgid(process.pid), _sig.SIGKILL)
                except Exception:
                    process.kill()
                process.wait(timeout=5)
                exit_code = 124
                stderr_chunks.append(f"\nOperation timed out after 300 seconds.\n")
                self._log("    [TIMEOUT] Command exceeded maximum execution time.\n")

            for thread in (stdout_thread, stderr_thread):
                thread.join(timeout=10)

        except Exception as exc:
            exit_code = 1
            stderr_chunks.append(str(exc))
            self._log(f"    [EXCEPTION] {exc}\n")

        end = datetime.now()
        stdout = "".join(stdout_chunks)
        stderr = "".join(stderr_chunks)

        # Also write to log file
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{start.isoformat()}] {cmd_display}\n")
            f.write(f"Exit code: {exit_code}\n")
            if stdout:
                f.write(f"STDOUT:\n{stdout}\n")
            if stderr:
                f.write(f"STDERR:\n{stderr}\n")
            f.write("-" * 60 + "\n")

        return CommandResult(
            command=full_cmd,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            duration_seconds=(end - start).total_seconds(),
            success=(exit_code == 0),
        )

    @staticmethod
    def _is_root() -> bool:
        try:
            return os.geteuid() == 0
        except AttributeError:
            return False

    def install(self) -> ComponentRecord:
        """Execute all commands for this component sequentially."""
        record = ComponentRecord(name=self.name)
        record.start_time = datetime.now().isoformat()

        # Check if already installed
        already_installed, version = self._is_installed()
        if already_installed:
            record.status = OperationStatus.SKIPPED
            record.version = version
            record.skip_reason = "Already installed"
            record.end_time = datetime.now().isoformat()
            record.duration_seconds = 0.0
            self._log(f"  [{self.name}] SKIPPED: Already installed (version: {version or 'unknown'})\n")
            return record

        os.makedirs(self.log_dir, exist_ok=True)
        log_file = self._prepare_log_file()
        record.log_file = log_file

        self._log(f"  [{self.name}] Starting installation...\n")
        self._log(f"  Log file: {log_file}\n")

        all_success = True
        for idx, command in enumerate(self.commands, 1):
            self._log(f"  Step {idx}/{len(self.commands)}: {command[0] if command else '...'}\n")
            result = self._run_command(command, log_file)
            record.commands.append(result)

            if not result.success:
                all_success = False
                record.error_summary = (
                    f"Command failed: {result.command_str} (exit code {result.exit_code})"
                )
                self._log(
                    f"  [{self.name}] FAILED step {idx}: exit code {result.exit_code}\n"
                )
                # F19: Stop the failed component's command chain — do not run
                # dependent steps after a failure within the same component.
                break
            else:
                self._log(
                    f"  [{self.name}] OK step {idx}: exit code 0\n"
                )

        record.end_time = datetime.now().isoformat()
        start_dt = datetime.fromisoformat(record.start_time)
        end_dt = datetime.fromisoformat(record.end_time)
        record.duration_seconds = (end_dt - start_dt).total_seconds()

        if all_success:
            record.status = OperationStatus.SUCCESS
            # F20: Final verification — use the boolean result of _is_installed().
            installed, version = self._is_installed()
            record.version = version
            if installed:
                self._log(f"  [{self.name}] SUCCESS: Installation completed and verified\n")
            else:
                self._log(f"  [{self.name}] WARNING: Commands succeeded but final install check failed\n")
                record.status = OperationStatus.WARNING
        else:
            record.status = OperationStatus.FAILED
            self._log(f"  [{self.name}] FAILED: One or more commands failed\n")

        return record


@dataclass
class InstallationReport:
    """Comprehensive final installation report."""
    total_components: int = 0
    successful: List[ComponentRecord] = field(default_factory=list)
    failed: List[ComponentRecord] = field(default_factory=list)
    skipped: List[ComponentRecord] = field(default_factory=list)
    warnings: List[ComponentRecord] = field(default_factory=list)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: float = 0.0
    overall_status: OperationStatus = OperationStatus.PENDING
    report_file: Optional[str] = None

    @property
    def success_count(self) -> int:
        return len(self.successful)

    @property
    def failure_count(self) -> int:
        return len(self.failed)

    @property
    def skip_count(self) -> int:
        return len(self.skipped)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def to_text(self) -> str:
        lines: List[str] = []
        lines.append("=" * 78)
        lines.append(" SEQUENTIAL INSTALLATION - FINAL REPORT")
        lines.append("=" * 78)
        lines.append("")
        lines.append(f"Total components processed: {self.total_components}")
        lines.append(f"  SUCCESS: {self.success_count}")
        lines.append(f"  FAILED:  {self.failure_count}")
        lines.append(f"  SKIPPED: {self.skip_count}")
        lines.append(f"  WARNING: {self.warning_count}")
        lines.append("")
        if self.start_time and self.end_time:
            lines.append(f"Start time:  {self.start_time}")
            lines.append(f"End time:    {self.end_time}")
            lines.append(f"Duration:    {self.duration_seconds:.2f} seconds")
        lines.append(f"Overall status: {self.overall_status.value}")
        lines.append("")

        if self.successful:
            lines.append("-" * 78)
            lines.append(" SUCCESSFUL COMPONENTS")
            lines.append("-" * 78)
            for comp in self.successful:
                lines.append(f"  [SUCCESS] {comp.name}")
                if comp.version:
                    lines.append(f"    Version: {comp.version}")
                lines.append(f"    Commands executed: {comp.command_count}")
                lines.append(f"    Duration: {comp.duration_seconds:.2f}s")
                if comp.log_file:
                    lines.append(f"    Log: {comp.log_file}")
                lines.append("")

        if self.skipped:
            lines.append("-" * 78)
            lines.append(" SKIPPED COMPONENTS")
            lines.append("-" * 78)
            for comp in self.skipped:
                lines.append(f"  [SKIPPED] {comp.name}")
                if comp.version:
                    lines.append(f"    Version: {comp.version}")
                lines.append(f"    Reason: {comp.skip_reason or 'Already installed'}")
                lines.append("")

        if self.failed:
            lines.append("-" * 78)
            lines.append(" FAILED COMPONENTS")
            lines.append("-" * 78)
            for comp in self.failed:
                lines.append(f"  [FAILED] {comp.name}")
                lines.append(f"    Error summary: {comp.error_summary or 'Unknown error'}")
                for cmd in comp.failed_commands:
                    lines.append(f"    FAILED COMMAND: {cmd.command_str}")
                    lines.append(f"      Exit code: {cmd.exit_code}")
                    lines.append(f"      Timestamp: {cmd.start_time}")
                    lines.append(f"      Duration: {cmd.duration_seconds:.2f}s")
                    if cmd.stderr:
                        lines.append(f"      STDERR: {cmd.stderr.strip()[:500]}")
                    if cmd.stdout:
                        lines.append(f"      STDOUT: {cmd.stdout.strip()[:500]}")
                if comp.log_file:
                    lines.append(f"    Log: {comp.log_file}")
                lines.append("")

        lines.append("=" * 78)
        lines.append(" END OF REPORT")
        lines.append("=" * 78)
        return "\n".join(lines)


class SequentialInstaller:
    """
    Manages sequential installation of multiple components.
    Continues on failure, tracks all results, generates final report.
    """

    def __init__(
        self,
        log_dir: str = "/var/log/odoo-installer",
        dry_run: bool = False,
        use_sudo: bool = False,
        on_output: Optional[Callable[[str], None]] = None,
    ):
        self.log_dir = log_dir
        self.dry_run = dry_run
        self.use_sudo = use_sudo
        self.on_output = on_output
        self.components: List[ComponentInstaller] = []

    def _log(self, message: str) -> None:
        if self.on_output:
            self.on_output(message)

    def add_component(
        self,
        name: str,
        commands: List[List[str]],
        check_installed: Optional[Callable[[], tuple[bool, Optional[str]]]] = None,
    ) -> None:
        """Add a component to the installation sequence."""
        installer = ComponentInstaller(
            name=name,
            commands=commands,
            check_installed=check_installed,
            log_dir=self.log_dir,
            dry_run=self.dry_run,
            use_sudo=self.use_sudo,
            on_output=self.on_output,
        )
        self.components.append(installer)

    def run_all(self) -> InstallationReport:
        """Execute all components sequentially. Continues on failure."""
        report = InstallationReport()
        report.total_components = len(self.components)
        report.start_time = datetime.now().isoformat()

        self._log("\n" + "=" * 78)
        self._log(" SEQUENTIAL INSTALLATION STARTED")
        self._log("=" * 78 + "\n")

        for installer in self.components:
            self._log(f"\n>>> Installing component: {installer.name}\n")
            record = installer.install()

            if record.status == OperationStatus.SUCCESS:
                report.successful.append(record)
            elif record.status == OperationStatus.SKIPPED:
                report.skipped.append(record)
            elif record.status == OperationStatus.WARNING:
                report.warnings.append(record)
            else:
                report.failed.append(record)

        report.end_time = datetime.now().isoformat()
        start_dt = datetime.fromisoformat(report.start_time)
        end_dt = datetime.fromisoformat(report.end_time)
        report.duration_seconds = (end_dt - start_dt).total_seconds()

        # Determine overall status
        if report.failure_count > 0:
            report.overall_status = OperationStatus.FAILED
        elif report.warning_count > 0:
            report.overall_status = OperationStatus.WARNING
        elif report.skip_count == report.total_components:
            report.overall_status = OperationStatus.SKIPPED
        else:
            report.overall_status = OperationStatus.SUCCESS

        # Write report to file
        os.makedirs(self.log_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.log_dir, f"installation_report_{ts}.txt")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report.to_text())
        report.report_file = report_file

        self._log("\n" + report.to_text() + "\n")
        self._log(f"\nFull report saved to: {report_file}\n")

        return report
