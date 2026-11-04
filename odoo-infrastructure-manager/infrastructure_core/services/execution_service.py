"""
Safe command execution engine using standard subprocess with telemetry,
safe argument list passing (no raw shell injection), and dry-run preview mode.

stdout and stderr are drained concurrently by reader threads so a process that
writes a lot to stderr can never fill the OS pipe and deadlock the caller.
"""
from datetime import datetime
import subprocess
import threading
from typing import Callable, List, Optional

from infrastructure_engine.models.operation import OperationStatus, WorkflowStep


DEFAULT_TIMEOUT_SECONDS = 300


class ExecutionService:
    """Executes external system commands safely without string concatenation vulnerabilities."""

    @staticmethod
    def _reader(
        stream,
        chunks: List[str],
        on_output: Optional[Callable[[str], None]],
        output_lock: threading.Lock,
        prefix: str = "",
    ) -> None:
        """Drain a pipe until EOF, optionally streaming each line to the callback."""
        try:
            for line in iter(stream.readline, ""):
                chunks.append(line)
                if on_output:
                    with output_lock:
                        on_output(f"{prefix}{line}")
        finally:
            try:
                stream.close()
            except Exception:
                pass

    @staticmethod
    def execute_step(
        step: WorkflowStep,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        on_output: Optional[Callable[[str], None]] = None,
        dry_run: bool = False,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> WorkflowStep:
        step.start_time = datetime.now()
        step.dry_run = dry_run
        step.status = OperationStatus.RUNNING

        cmd_str = " ".join(step.command)
        if on_output:
            on_output(f"==> [{step.id}] Executing: {cmd_str}\n")

        if dry_run:
            step.stdout = f"[DRY-RUN] Command previewed: {cmd_str}"
            step.stderr = ""
            step.exit_code = 0
            step.status = OperationStatus.SUCCESS
            step.end_time = datetime.now()
            if on_output:
                on_output(f"[DRY-RUN] {step.id} simulated successfully (Exit code: 0)\n")
            return step

        process: Optional[subprocess.Popen] = None
        stdout_chunks: List[str] = []
        stderr_chunks: List[str] = []
        stdout_thread: Optional[threading.Thread] = None
        stderr_thread: Optional[threading.Thread] = None
        output_lock = threading.Lock()

        try:
            # shell=False + argument list prevents shell injection.
            process = subprocess.Popen(
                step.command,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            stdout_thread = threading.Thread(
                target=ExecutionService._reader,
                args=(process.stdout, stdout_chunks, on_output, output_lock),
                daemon=True,
            )
            stderr_thread = threading.Thread(
                target=ExecutionService._reader,
                args=(process.stderr, stderr_chunks, on_output, output_lock, "[STDERR] "),
                daemon=True,
            )
            stdout_thread.start()
            stderr_thread.start()

            try:
                process.wait(timeout=timeout)
                step.exit_code = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
                step.status = OperationStatus.FAILED
                step.exit_code = 124
                stderr_chunks.append(f"\nOperation timed out after {timeout} seconds.")
                if on_output:
                    with output_lock:
                        on_output(f"[TIMEOUT] {step.id} exceeded maximum execution time.\n")
            finally:
                # Let the readers finish draining after the process exits.
                for thread in (stdout_thread, stderr_thread):
                    if thread:
                        thread.join(timeout=10)

            step.stdout = "".join(stdout_chunks)
            step.stderr = "".join(stderr_chunks)

            if step.status != OperationStatus.FAILED:
                step.status = (
                    OperationStatus.SUCCESS if step.exit_code == 0 else OperationStatus.FAILED
                )

        except Exception as e:
            if process and process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            step.status = OperationStatus.FAILED
            step.exit_code = 1
            step.stderr = str(e)
            step.stdout = "".join(stdout_chunks)
            if on_output:
                on_output(f"[EXCEPTION] Failed to launch command: {e}\n")
        finally:
            step.end_time = datetime.now()

        return step
