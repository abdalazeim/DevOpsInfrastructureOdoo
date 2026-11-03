"""
Workflow: Deploy Odoo 18 and PostgreSQL 17.

Uses the same installer/layout as Odoo 17 and 19:
  https://github.com/minhng92/odoo-18-docker-compose
"""
from typing import List
from infrastructure_engine.models.profile import InfrastructureProfile
from infrastructure_engine.models.operation import OperationRecord, WorkflowStep
from infrastructure_engine.services.docker_service import DockerService


def _installer_command(profile: InfrastructureProfile, version: str, with_traefik: bool) -> List[str]:
    destination = f"{profile.paths.data_root}/odoo{version}"
    command = [
        "bash",
        "automation/scripts/install-odoo.sh",
        version,
        "--destination",
        destination,
    ]
    if with_traefik:
        command.append("--with-traefik")
    return command


class DeployOdoo18Workflow:
    """Builds step sequence for deploying Odoo 18 & PostgreSQL 17."""

    @staticmethod
    def create_operation(profile: InfrastructureProfile, dry_run: bool = False) -> OperationRecord:
        with_traefik = bool(profile.traefik.enabled and profile.security.enforce_https)
        destination = f"{profile.paths.data_root}/odoo18"

        steps: List[WorkflowStep] = [
            WorkflowStep(
                id="verify-odoo18-dirs",
                name="Ensure Odoo 18 Instance Directories Exist",
                description=(
                    f"Creates the minhng92-style layout under {destination} "
                    "(addons/, etc/, postgresql/, backup/)"
                ),
                command=[
                    "mkdir", "-p",
                    f"{destination}/addons",
                    f"{destination}/etc",
                    f"{destination}/postgresql",
                    f"{destination}/backup",
                ],
            ),
            WorkflowStep(
                id="prepare-odoo18-instance",
                name="Render Odoo 18 Configuration and .env",
                description="Runs install-odoo.sh --no-start to render odoo.conf and the instance .env",
                command=_installer_command(profile, "18", with_traefik) + ["--no-start"],
            ),
            DockerService.build_compose_config_step(
                compose_file=f"{destination}/docker-compose.yml",
                step_id="validate-odoo18-compose",
            ),
            WorkflowStep(
                id="start-odoo18-stack",
                name="Start Odoo 18 & PostgreSQL 17",
                description="Launches the stack via install-odoo.sh (idempotent, secrets from .env)",
                command=_installer_command(profile, "18", with_traefik),
            ),
            WorkflowStep(
                id="wait-for-pg17-readiness",
                name="Wait for PostgreSQL 17 Database Readiness",
                description="Checks that the PostgreSQL 17 container accepts connections",
                command=["docker", "exec", "odoo18-db", "pg_isready", "-U", profile.odoo18.database.user],
            ),
            WorkflowStep(
                id="verify-odoo18-status",
                name="Verify Odoo 18 Container Status",
                description="Checks container state and web availability",
                command=["docker", "inspect", "--format={{.State.Status}}", "odoo18"],
            ),
        ]

        return OperationRecord(
            operation_id=f"op-deploy-odoo18-{profile.profile_name}",
            name="Deploy Odoo 18 & PostgreSQL 17 Stack",
            category="odoo18",
            profile_name=profile.profile_name,
            steps=steps,
            dry_run=dry_run,
        )
