"""
Unit tests for TraefikDockerManager module.
Verifies discovery, compose generation, label creation, and backup/restore mechanisms.
"""

import unittest
import os
import tempfile
import shutil
from app.services.traefik_manager import (
    TraefikDockerManager,
    TraefikConfig,
    DEFAULT_CONFIG_DIR,
    DEFAULT_DOCKER_IMAGE,
    DEFAULT_HTTP_PORT,
    DEFAULT_DASHBOARD_EXTERNAL_PORT,
    DEFAULT_DASHBOARD_INTERNAL_PORT,
    DEFAULT_ODOO19_PORT,
    DEFAULT_JENKINS_PORT,
)


class TestTraefikDockerManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_inspect_port_returns_object(self):
        port_info = TraefikDockerManager.inspect_port(80, "Traefik HTTP")
        self.assertEqual(port_info.port, 80)
        self.assertEqual(port_info.service_name, "Traefik HTTP")
        self.assertIsInstance(port_info.is_in_use, bool)

    def test_discover_environment_returns_valid_report(self):
        report = TraefikDockerManager.discover_environment(config_dir=self.temp_dir)
        self.assertIsNotNone(report.timestamp)
        self.assertIsInstance(report.docker_installed, bool)
        self.assertIn(report.container_status, ["running", "stopped", "not_found", "error"])
        self.assertGreaterEqual(len(report.ports_audit), 4)

    def test_generate_compose_yaml_standard_defaults(self):
        config = TraefikConfig(
            config_dir=self.temp_dir,
            image=DEFAULT_DOCKER_IMAGE,
            enable_dashboard=True,
            insecure_dashboard=True,
            http_port=DEFAULT_HTTP_PORT,
            dashboard_external_port=DEFAULT_DASHBOARD_EXTERNAL_PORT,
            dashboard_internal_port=DEFAULT_DASHBOARD_INTERNAL_PORT,
            docker_socket_ro=True,
        )
        yaml_content = TraefikDockerManager.generate_compose_yaml(config)

        self.assertIn("image: traefik:v3.7", yaml_content)
        self.assertIn("container_name: traefik", yaml_content)
        self.assertIn("--api.dashboard=true", yaml_content)
        self.assertIn("--providers.docker=true", yaml_content)
        self.assertIn("--providers.docker.exposedbydefault=false", yaml_content)
        self.assertIn("--entrypoints.web.address=:80", yaml_content)
        self.assertIn('"80:80"', yaml_content)
        self.assertIn('"10090:8080"', yaml_content)
        self.assertIn("networks:\n  proxy:\n    external: true", yaml_content)

    def test_generate_service_labels_for_jenkins_and_odoo(self):
        # Jenkins test
        jenkins_labels = TraefikDockerManager.generate_service_labels(
            service_type="jenkins",
            domain="jenkins.example.com",
            target_port=DEFAULT_JENKINS_PORT,
            entrypoints="web"
        )
        self.assertIn("traefik.enable=true", jenkins_labels)
        self.assertIn("traefik.http.routers.jenkins.rule=Host(`jenkins.example.com`)", jenkins_labels)
        self.assertIn(f"traefik.http.services.jenkins.loadbalancer.server.port={DEFAULT_JENKINS_PORT}", jenkins_labels)

        # Odoo 19 test
        odoo19_labels = TraefikDockerManager.generate_service_labels(
            service_type="odoo19",
            domain="odoo19.example.com",
            target_port=DEFAULT_ODOO19_PORT,
            entrypoints="web"
        )
        self.assertIn("traefik.enable=true", odoo19_labels)
        self.assertIn("traefik.http.routers.odoo19.rule=Host(`odoo19.example.com`)", odoo19_labels)
        self.assertIn(f"traefik.http.services.odoo19.loadbalancer.server.port={DEFAULT_ODOO19_PORT}", odoo19_labels)
        # Verify websocket livechat router
        self.assertTrue(any("traefik.http.routers.odoo19-chat" in label for label in odoo19_labels))

    def test_ensure_traefik_directories_and_acme_permissions(self):
        dirs = TraefikDockerManager.ensure_traefik_directories(config_dir=self.temp_dir)
        acme_path = dirs["acme_file"]
        self.assertTrue(os.path.exists(acme_path))
        perm = oct(os.stat(acme_path).st_mode)[-3:]
        self.assertEqual(perm, "600")

    def test_traefik_backup_and_restore(self):
        # Write dummy files
        compose_file = os.path.join(self.temp_dir, "docker-compose.yml")
        with open(compose_file, "w") as f:
            f.write("services:\n  traefik:\n    image: traefik:v3.7\n")

        # Create backup
        backup_res = TraefikDockerManager.create_backup_snapshot(config_dir=self.temp_dir)
        self.assertEqual(backup_res["status"], "verified")
        self.assertTrue(os.path.exists(backup_res["archive_path"]))
        self.assertGreater(backup_res["size_bytes"], 0)
        self.assertTrue(len(backup_res["sha256"]) == 64)

        # Overwrite compose file with test string
        with open(compose_file, "w") as f:
            f.write("corrupted content")

        # Restore from backup
        restore_res = TraefikDockerManager.restore_backup_snapshot(
            backup_res["archive_path"],
            config_dir=self.temp_dir
        )
        self.assertEqual(restore_res["status"], "success")

        # Verify restored content
        with open(compose_file, "r") as f:
            content = f.read()
        self.assertIn("image: traefik:v3.7", content)


if __name__ == "__main__":
    unittest.main()
