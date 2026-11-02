"""
Safe command execution engine using standard subprocess with telemetry,
safe argument list passing (no raw shell injection), and dry-run preview mode.
"""
from datetime import datetime
import subprocess
from typing import Callable, List, Optional
from app.models.operation import OperationStatus, WorkflowStep

class ExecutionService:
    """Executes external system commands safely without string concatenation vulnerabilities."""

    @staticmethod
    def execute_step(
        step: WorkflowStep,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        on_output: Optional[Callable[[str], None]] = None,
        dry_run: bool = False
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

        try:
            # We use standard Popen with argument list (shell=False) to prevent shell injection
            process = subprocess.Popen(
                step.command,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            stdout_chunks = []
            stderr_chunks = []

            # Read stdout line by line
            if process.stdout:
                for line in process.stdout:
                    stdout_chunks.append(line)
                    if on_output:
                        on_output(line)

            process.wait(timeout=300)
            step.exit_code = process.returncode

            if process.stderr:
                err_text = process.stderr.read()
                stderr_chunks.append(err_text)
                if err_text and on_output:
                    on_output(f"[STDERR] {err_text}")

            step.stdout = "".join(stdout_chunks)
            step.stderr = "".join(stderr_chunks)

            if step.exit_code == 0:
                step.status = OperationStatus.SUCCESS
            else:
                step.status = OperationStatus.FAILED

        except subprocess.TimeoutExpired:
            process.kill()
            step.status = OperationStatus.FAILED
            step.exit_code = 124
            step.stderr = "Operation timed out after 300 seconds."
            if on_output:
                on_output(f"[TIMEOUT] {step.id} exceeded maximum execution time.\n")
        except Exception as e:
            step.status = OperationStatus.FAILED
            step.exit_code = 1
            step.stderr = str(e)
            if on_output:
                on_output(f"[EXCEPTION] Failed to launch command: {e}\n")
        finally:
            step.end_time = datetime.now()

        return step
