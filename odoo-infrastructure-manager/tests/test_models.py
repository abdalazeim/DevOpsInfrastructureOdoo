"""
Unit tests for data models and dictionary serialization.
"""
import unittest
from datetime import datetime, timedelta
from app.models.profile import InfrastructureProfile
from app.models.operation import OperationRecord, OperationStatus, WorkflowStep

class TestModels(unittest.TestCase):
    def test_profile_from_dict_defaults(self):
        profile = InfrastructureProfile.from_dict({
            "profile_name": "prod-server",
            "server": {"hostname": "prod-odoo", "timezone": "Asia/Riyadh"},
            "traefik": {"dashboard_domain": "traefik.prod.com"},
        })
        self.assertEqual(profile.profile_name, "prod-server")
        self.assertEqual(profile.server.hostname, "prod-odoo")
        self.assertEqual(profile.server.timezone, "Asia/Riyadh")
        self.assertEqual(profile.odoo17.version, "17")
        self.assertEqual(profile.odoo19.version, "19")

    def test_workflow_step_duration(self):
        now = datetime.now()
        step = WorkflowStep(
            id="step-1",
            name="Sample Step",
            description="Testing duration",
            command=["echo", "1"],
            start_time=now,
            end_time=now + timedelta(seconds=2.5)
        )
        self.assertAlmostEqual(step.duration_seconds, 2.5, places=1)

    def test_operation_record_completion(self):
        op = OperationRecord(
            operation_id="op-1",
            name="Test Op",
            category="test",
            profile_name="default",
            status=OperationStatus.SUCCESS
        )
        self.assertTrue(op.is_finished)

if __name__ == "__main__":
    unittest.main()
