"""
Operation execution log and workflow step models.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

class OperationStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"

@dataclass
class WorkflowStep:
    id: str
    name: str
    description: str
    command: List[str]
    status: OperationStatus = OperationStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    is_critical: bool = True
    dry_run: bool = False

    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

@dataclass
class OperationRecord:
    operation_id: str
    name: str
    category: str # "server_prep" | "traefik" | "odoo17" | "odoo19" | "backup" | "restore" | "health"
    profile_name: str
    status: OperationStatus = OperationStatus.PENDING
    steps: List[WorkflowStep] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    initiated_by: str = "operator"
    dry_run: bool = False
    error_summary: Optional[str] = None

    @property
    def is_finished(self) -> bool:
        return self.status in [OperationStatus.SUCCESS, OperationStatus.FAILED, OperationStatus.CANCELLED]

    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
