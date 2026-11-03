"""
Workflow: Deploy Odoo 19 and PostgreSQL 18.

Delegates to automation/scripts/install-odoo.sh, which follows the
minhng92/odoo-19-docker-compose layout (dedicated folder, postgresql/,
addons/, etc/, entrypoint.sh, direct ports 10019/20019).
"""
from typing import List
from app.models.profile import InfrastructureProfile
from app.models.operation import OperationRecord, WorkflowStep
from app.services.docker_service import DockerService


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


class DeployOdoo19Workflow:
    """Builds step sequence for deploying Odoo 19 & PostgreSQL 18."""

    @staticmethod
    def create_operation(profile: InfrastructureProfile, dry_run: bool = False) -> OperationRecord:
        with_traefik = bool(profile.traefik.enabled and profile.security.enforce_https)
        destination = f"{profile.paths.data_root}/odoo19"

        steps: List[WorkflowStep] = [
            WorkflowStep(
                id="verify-odoo19-dirs",
                name="Ensure Odoo 19 Instance Directories Exist",
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
                id="prepare-odoo19-instance",
                name="Render Odoo 19 Configuration and .env",
                description="Runs install-odoo.sh --no-start to render odoo.conf and the instance .env",
                command=_installer_command(profile, "19", with_traefik) + ["--no-start"],
            ),
            DockerService.build_compose_config_step(
                compose_file=f"{destination}/docker-compose.yml",
                step_id="validate-odoo19-compose",
            ),
            WorkflowStep(
                id="start-odoo19-stack",
                name="Start Odoo 19 & PostgreSQL 18",
                description="Launches the stack via install-odoo.sh (idempotent, secrets from .env)",
                command=_installer_command(profile, "19", with_traefik),
            ),
            WorkflowStep(
                id="wait-for-pg18-readiness",
                name="Wait for PostgreSQL 18 Database Readiness",
                description="Checks that the PostgreSQL 18 container accepts connections",
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
