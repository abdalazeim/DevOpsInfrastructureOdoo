"""
Unit tests for SmartInspectorService and SystemBackupService.
"""
import unittest
import os
import tempfile
from app.services.smart_inspector import SmartInspectorService, ComponentStatus
from app.services.system_backup import SystemBackupService

class TestSmartInspectorService(unittest.TestCase):
    def test_inspect_ubuntu_returns_object(self):
        comp = SmartInspectorService.inspect_ubuntu()
        self.assertIsNotNone(comp)
        self.assertEqual(comp.id, "ubuntu_os")
        self.assertIn(comp.status, [ComponentStatus.INSTALLED, ComponentStatus.NEEDS_UPDATE, ComponentStatus.MISCONFIGURED])

    def test_inspect_docker_engine(self):
        comp = SmartInspectorService.inspect_docker_engine()
        self.assertEqual(comp.id, "docker_engine")
        self.assertIn(comp.status, [ComponentStatus.INSTALLED, ComponentStatus.MISSING, ComponentStatus.MISCONFIGURED])
        self.assertTrue(len(comp.why_needed) > 0)

    def test_inspect_utility_packages(self):
        pkgs = SmartInspectorService.inspect_utility_packages()
        self.assertGreaterEqual(len(pkgs), 5)
        ids = [p.id for p in pkgs]
        self.assertIn("pkg_curl", ids)
        self.assertIn("pkg_tar", ids)
        self.assertIn("pkg_gzip", ids)

    def test_run_full_inspection(self):
        report = SmartInspectorService.run_full_inspection()
        self.assertIsNotNone(report.timestamp)
        self.assertGreaterEqual(len(report.components), 8)

class TestSystemBackupService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def test_create_and_verify_snapshot(self):
        manifest = SystemBackupService.create_full_snapshot(
            data_root=self.temp_dir,
            output_dir=self.temp_dir,
            include_db_dumps=False
        )
        self.assertEqual(manifest["status"], "verified")
        self.assertTrue(os.path.exists(manifest["archive_path"]))
        self.assertTrue(manifest["file_size_bytes"] > 0)

        # Verify checksum
        is_valid = SystemBackupService.verify_archive(
            manifest["archive_path"],
            expected_sha256=manifest["sha256"]
        )
        self.assertTrue(is_valid)

if __name__ == "__main__":
    unittest.main()
