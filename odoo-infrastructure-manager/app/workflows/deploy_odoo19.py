"""
Workflow: Deploy Odoo 19 and PostgreSQL 18.
"""
from typing import List
from app.models.profile import InfrastructureProfile
from app.models.operation import OperationRecord, WorkflowStep
from app.services.docker_service import DockerService

class DeployOdoo19Workflow:
    """Builds step sequence for deploying Odoo 19 & PostgreSQL 18."""

    @staticmethod
    def create_operation(profile: InfrastructureProfile, dry_run: bool = False) -> OperationRecord:
        steps: List[WorkflowStep] = [
            WorkflowStep(
                id="verify-odoo19-dirs",
                name="Ensure Odoo 19 Persistent Volumes Exist",
                description=f"Creates filestore and DB directories under {profile.paths.data_root}/odoo19",
                command=["bash", "-c", f"mkdir -p {profile.paths.data_root}/odoo19/data {profile.paths.data_root}/odoo19/db_data {profile.paths.data_root}/odoo19/addons"],
            ),
            DockerService.build_compose_config_step(
                compose_file="deployment/odoo19/docker-compose.yml",
                step_id="validate-odoo19-compose"
            ),
            DockerService.build_compose_up_step(
                compose_file="deployment/odoo19/docker-compose.yml",
                step_id="start-odoo19-stack"
            ),
            WorkflowStep(
                id="wait-for-pg18-readiness",
                name="Wait for PostgreSQL 18 Database Readiness",
                description="Checks that PostgreSQL 18 container accepts connections",
                command=["docker", "exec", "odoo19-db", "pg_isready", "-U", profile.odoo19.database.user],
            ),
            WorkflowStep(
                id="verify-odoo19-status",
                name="Verify Odoo 19 Container Status",
                description="Checks container state and web availability",
                command=["docker", "inspect", "--format={{.State.Status}}", "odoo19"],
            ),
        ]

        return OperationRecord(
            operation_id=f"op-deploy-odoo19-{profile.profile_name}",
            name="Deploy Odoo 19 & PostgreSQL 18 Stack",
            category="odoo19",
            profile_name=profile.profile_name,
            steps=steps,
            dry_run=dry_run,
        )
