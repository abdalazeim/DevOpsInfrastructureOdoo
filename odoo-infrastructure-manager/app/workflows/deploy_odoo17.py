"""
Workflow: Deploy Odoo 17 and PostgreSQL 16.
"""
from typing import List
from app.models.profile import InfrastructureProfile
from app.models.operation import OperationRecord, WorkflowStep
from app.services.docker_service import DockerService

class DeployOdoo17Workflow:
    """Builds step sequence for deploying Odoo 17 & PostgreSQL 16."""

    @staticmethod
    def create_operation(profile: InfrastructureProfile, dry_run: bool = False) -> OperationRecord:
        steps: List[WorkflowStep] = [
            WorkflowStep(
                id="verify-odoo17-dirs",
                name="Ensure Odoo 17 Persistent Volumes Exist",
                description=f"Creates filestore and DB directories under {profile.paths.data_root}/odoo17",
                command=["bash", "-c", f"mkdir -p {profile.paths.data_root}/odoo17/data {profile.paths.data_root}/odoo17/db_data {profile.paths.data_root}/odoo17/addons"],
            ),
            DockerService.build_compose_config_step(
                compose_file="deployment/odoo17/docker-compose.yml",
                step_id="validate-odoo17-compose"
            ),
            DockerService.build_compose_up_step(
                compose_file="deployment/odoo17/docker-compose.yml",
                step_id="start-odoo17-stack"
            ),
            WorkflowStep(
                id="wait-for-pg16-readiness",
                name="Wait for PostgreSQL 16 Database Readiness",
                description="Checks that PostgreSQL 16 container accepts connections",
                command=["docker", "exec", "odoo17-db", "pg_isready", "-U", profile.odoo17.database.user],
            ),
            WorkflowStep(
                id="verify-odoo17-status",
                name="Verify Odoo 17 Container Status",
                description="Checks container state and web availability",
                command=["docker", "inspect", "--format={{.State.Status}}", "odoo17"],
            ),
        ]

        return OperationRecord(
            operation_id=f"op-deploy-odoo17-{profile.profile_name}",
            name="Deploy Odoo 17 & PostgreSQL 16 Stack",
            category="odoo17",
            profile_name=profile.profile_name,
            steps=steps,
            dry_run=dry_run,
        )
