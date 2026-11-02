"""
Unit tests for service command builders and safe execution runner.
"""
import unittest
from app.services.docker_service import DockerService
from app.services.ansible_service import AnsibleService
from app.services.backup_service import BackupService
from app.services.execution_service import ExecutionService
from app.models.operation import OperationStatus, WorkflowStep

class TestServices(unittest.TestCase):
    def test_docker_network_create_step(self):
        step = DockerService.build_network_create_step("proxy", "172.28.0.0/16")
        self.assertEqual(step.command, ["docker", "network", "create", "--driver", "bridge", "--subnet", "172.28.0.0/16", "proxy"])

    def test_docker_compose_config_step(self):
        step = DockerService.build_compose_config_step("deployment/traefik/docker-compose.yml")
        self.assertEqual(step.command, ["docker", "compose", "-f", "deployment/traefik/docker-compose.yml", "config"])

    def test_docker_compose_down_with_volumes(self):
        step = DockerService.build_compose_down_step("path/compose.yml", remove_volumes=True)
        self.assertIn("-v", step.command)

    def test_ansible_playbook_check_mode(self):
        step = AnsibleService.build_playbook_step(check_mode=True)
        self.assertIn("--check", step.command)

    def test_backup_service_command(self):
        step = BackupService.build_backup_step(version="17", db_name="odoo17_prod", retention_count=5)
        self.assertEqual(step.command, ["bash", "automation/scripts/backup-db.sh", "17", "odoo17_prod", "5"])

    def test_restore_service_force_flag(self):
        step = BackupService.build_restore_step("19", "/tmp/dump.sql.gz", "odoo19_test", force=True)
        self.assertIn("--force", step.command)

    def test_execution_service_dry_run(self):
        step = WorkflowStep(
            id="test-dry-run",
            name="Simulated Command",
            description="Preview command only",
            command=["rm", "-rf", "/dangerous/path"]
        )
        res = ExecutionService.execute_step(step, dry_run=True)
        self.assertEqual(res.status, OperationStatus.SUCCESS)
        self.assertEqual(res.exit_code, 0)
        self.assertIn("[DRY-RUN]", res.stdout)

if __name__ == "__main__":
    unittest.main()
