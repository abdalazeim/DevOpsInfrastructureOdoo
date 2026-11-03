"""
Service for inspecting host health, docker container statuses, and endpoint readiness.
"""
from typing import List
from app.models.operation import WorkflowStep

class HealthService:
    """Orchestrates comprehensive infrastructure health diagnostics."""

    @staticmethod
    def build_health_check_step() -> WorkflowStep:
        return WorkflowStep(
            id="run-health-diagnostics",
            name="Run Infrastructure Health Diagnostics",
            description="Inspects Docker daemon, containers, PostgreSQL ping, and host resources",
            command=["bash", "automation/scripts/health-check.sh"],
        )
