"""
Workflow: Deploy Odoo 17 and PostgreSQL 16.

Delegates to automation/scripts/install-odoo.sh, which follows the
minhng92/odoo-17-docker-compose layout (dedicated folder, postgresql/,
addons/, etc/, entrypoint.sh, direct ports 10017/20017) while reading
secrets from the protected .env file.
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


class DeployOdoo17Workflow:
    """Builds step sequence for deploying Odoo 17 & PostgreSQL 16."""

    @staticmethod
    def create_operation(profile: InfrastructureProfile, dry_run: bool = False) -> OperationRecord:
        with_traefik = bool(profile.traefik.enabled and profile.security.enforce_https)
        destination = f"{profile.paths.data_root}/odoo17"

        steps: List[WorkflowStep] = [
            WorkflowStep(
                id="verify-odoo17-dirs",
                name="Ensure Odoo 17 Instance Directories Exist",
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
                id="prepare-odoo17-instance",
                name="Render Odoo 17 Configuration and .env",
                description="Runs install-odoo.sh --no-start to render odoo.conf and the instance .env",
                command=_installer_command(profile, "17", with_traefik) + ["--no-start"],
            ),
            DockerService.build_compose_config_step(
                compose_file=f"{destination}/docker-compose.yml",
                step_id="validate-odoo17-compose",
            ),
            WorkflowStep(
                id="start-odoo17-stack",
                name="Start Odoo 17 & PostgreSQL 16",
                description="Launches the stack via install-odoo.sh (idempotent, secrets from .env)",
                command=_installer_command(profile, "17", with_traefik),
            ),
            WorkflowStep(
                id="wait-for-pg16-readiness",
                name="Wait for PostgreSQL 16 Database Readiness",
                description="Checks that the PostgreSQL 16 container accepts connections",
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
