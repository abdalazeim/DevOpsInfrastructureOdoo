"""
Workflow: Server Preparation and Baseline Setup.
"""
from typing import List
from infrastructure_engine.models.profile import InfrastructureProfile
from infrastructure_engine.models.operation import OperationRecord, WorkflowStep
from infrastructure_engine.services.docker_service import DockerService

class ServerPrepWorkflow:
    """Builds the sequence of steps for baseline server configuration."""

    @staticmethod
    def create_operation(profile: InfrastructureProfile, dry_run: bool = False) -> OperationRecord:
        steps: List[WorkflowStep] = [
            WorkflowStep(
                id="check-system-prerequisites",
                name="Check Host Prerequisites",
                description="Verifies Ubuntu release, CPU, memory, and disk space",
                command=["bash", "-c", "uname -a && free -m && df -h /"],
            ),
            WorkflowStep(
                id="initialize-server-dirs",
                name="Initialize Server Directories & Permissions",
                description=f"Creates {profile.paths.data_root} directories and proxy network",
                command=["bash", "automation/scripts/init-server.sh"],
            ),
            DockerService.build_network_create_step(
                network_name=profile.network.proxy_network_name,
                subnet=profile.network.proxy_subnet
            ),
        ]

        return OperationRecord(
            operation_id=f"op-server-prep-{profile.profile_name}",
            name=f"Prepare Server [{profile.server.hostname}]",
            category="server_prep",
            profile_name=profile.profile_name,
            steps=steps,
            dry_run=dry_run,
        )
