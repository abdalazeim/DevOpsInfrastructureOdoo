"""
Workflow: Complete End-to-End Infrastructure Deployment.
"""
from typing import List
from app.models.profile import InfrastructureProfile
from app.models.operation import OperationRecord, WorkflowStep
from app.workflows.server_prep import ServerPrepWorkflow
from app.workflows.deploy_traefik import DeployTraefikWorkflow
from app.workflows.deploy_odoo17 import DeployOdoo17Workflow
from app.workflows.deploy_odoo19 import DeployOdoo19Workflow
from app.services.health_service import HealthService

class FullDeployWorkflow:
    """Combines all infrastructure stages into an orchestrated pipeline."""

    @staticmethod
    def create_operation(profile: InfrastructureProfile, dry_run: bool = False) -> OperationRecord:
        steps: List[WorkflowStep] = []

        # 1. Server Prep Steps
        prep_op = ServerPrepWorkflow.create_operation(profile, dry_run=dry_run)
        steps.extend(prep_op.steps)

        # 2. Traefik Steps
        if profile.traefik.enabled:
            tr_op = DeployTraefikWorkflow.create_operation(profile, dry_run=dry_run)
            steps.extend(tr_op.steps)

        # 3. Odoo 17 Steps
        if profile.odoo17.enabled:
            o17_op = DeployOdoo17Workflow.create_operation(profile, dry_run=dry_run)
            steps.extend(o17_op.steps)

        # 4. Odoo 19 Steps
        if profile.odoo19.enabled:
            o19_op = DeployOdoo19Workflow.create_operation(profile, dry_run=dry_run)
            steps.extend(o19_op.steps)

        # 5. Health Diagnostic Step
        steps.append(HealthService.build_health_check_step())

        return OperationRecord(
            operation_id=f"op-full-deploy-{profile.profile_name}",
            name=f"Full Multi-Version Deployment [{profile.server.hostname}]",
            category="full_deploy",
            profile_name=profile.profile_name,
            steps=steps,
            dry_run=dry_run,
        )
