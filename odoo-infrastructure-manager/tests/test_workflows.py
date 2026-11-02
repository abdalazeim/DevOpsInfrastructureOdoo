"""
Unit tests for multi-stage workflow pipeline generation.
"""
import unittest
from app.models.profile import InfrastructureProfile
from app.workflows.server_prep import ServerPrepWorkflow
from app.workflows.deploy_traefik import DeployTraefikWorkflow
from app.workflows.deploy_odoo17 import DeployOdoo17Workflow
from app.workflows.deploy_odoo19 import DeployOdoo19Workflow
from app.workflows.full_deploy import FullDeployWorkflow
from app.workflows.database_ops import DatabaseOpsWorkflow

class TestWorkflows(unittest.TestCase):
    def setUp(self):
        self.profile = InfrastructureProfile(profile_name="test-workflow-profile")

    def test_server_prep_workflow_steps(self):
        op = ServerPrepWorkflow.create_operation(self.profile)
        self.assertEqual(op.category, "server_prep")
        self.assertGreaterEqual(len(op.steps), 2)
        step_ids = [s.id for s in op.steps]
        self.assertIn("initialize-server-dirs", step_ids)

    def test_deploy_traefik_workflow_steps(self):
        op = DeployTraefikWorkflow.create_operation(self.profile)
        self.assertEqual(op.category, "traefik")
        step_ids = [s.id for s in op.steps]
        self.assertIn("verify-acme-permissions", step_ids)
        self.assertIn("start-traefik", step_ids)

    def test_deploy_odoo17_workflow_steps(self):
        op = DeployOdoo17Workflow.create_operation(self.profile)
        self.assertEqual(op.category, "odoo17")
        step_ids = [s.id for s in op.steps]
        self.assertIn("start-odoo17-stack", step_ids)
        self.assertIn("wait-for-pg16-readiness", step_ids)

    def test_deploy_odoo19_workflow_steps(self):
        op = DeployOdoo19Workflow.create_operation(self.profile)
        self.assertEqual(op.category, "odoo19")
        step_ids = [s.id for s in op.steps]
        self.assertIn("start-odoo19-stack", step_ids)
        self.assertIn("wait-for-pg18-readiness", step_ids)

    def test_full_deploy_chains_all_enabled_components(self):
        op = FullDeployWorkflow.create_operation(self.profile)
        self.assertEqual(op.category, "full_deploy")
        step_ids = [s.id for s in op.steps]
        # Traefik, Odoo 17, Odoo 19, and health diagnostic must be in pipeline
        self.assertIn("start-traefik", step_ids)
        self.assertIn("start-odoo17-stack", step_ids)
        self.assertIn("start-odoo19-stack", step_ids)
        self.assertIn("run-health-diagnostics", step_ids)

    def test_database_backup_operation(self):
        op = DatabaseOpsWorkflow.create_backup_operation("17", "odoo17_db", retention_count=7)
        self.assertEqual(op.category, "backup")
        self.assertIn("backup-odoo17", [s.id for s in op.steps])

if __name__ == "__main__":
    unittest.main()
