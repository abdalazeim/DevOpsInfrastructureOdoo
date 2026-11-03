"""
Workflow: Deploy Traefik v3.7 Reverse Proxy.
"""
from typing import List
from infrastructure_engine.models.profile import InfrastructureProfile
from infrastructure_engine.models.operation import OperationRecord, WorkflowStep
from infrastructure_engine.services.docker_service import DockerService

class DeployTraefikWorkflow:
    """Builds step sequence for deploying Traefik v3.7 with TLS & ACME support."""

    @staticmethod
    def create_operation(profile: InfrastructureProfile, dry_run: bool = False) -> OperationRecord:
        steps: List[WorkflowStep] = [
            WorkflowStep(
                id="verify-acme-permissions",
                name="Verify ACME Certificate File Permissions",
                description="Ensures acme.json has restrictive permissions 0600",
                command=["bash", "-c", f"mkdir -p {profile.paths.data_root}/traefik/acme && touch {profile.paths.data_root}/traefik/acme/acme.json && chmod 600 {profile.paths.data_root}/traefik/acme/acme.json"],
            ),
            DockerService.build_compose_config_step(
                compose_file="deployment/traefik/docker-compose.yml",
                step_id="validate-traefik-compose"
            ),
            DockerService.build_compose_up_step(
                compose_file="deployment/traefik/docker-compose.yml",
                step_id="start-traefik"
            ),
            WorkflowStep(
                id="verify-traefik-health",
                name="Verify Traefik Service Status",
                description="Checks that Traefik container is in running state",
                command=["docker", "inspect", "--format={{.State.Status}}", "traefik"],
            ),
        ]

        return OperationRecord(
            operation_id=f"op-deploy-traefik-{profile.profile_name}",
            name="Deploy Traefik v3.7 Reverse Proxy",
            category="traefik",
            profile_name=profile.profile_name,
            steps=steps,
            dry_run=dry_run,
        )
