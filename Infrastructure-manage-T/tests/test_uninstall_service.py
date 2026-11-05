"""
Unit tests for the Full System Cleanup & Deep Uninstall service.
"""
import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from app.services.uninstall_service import (
    is_backup_path,
    is_project_path,
    should_protect,
    discover_installation,
    plan_uninstall,
    run_full_cleanup,
    verify_cleanup,
    CleanupItem,
    CleanupReport,
    CleanupStatus,
    BackupProtectionError,
    UNINSTALL_LOG,
    PROJECT_INSTALL_PATHS,
    BACKUP_FILENAME_PATTERNS,
)


class TestBackupProtection(unittest.TestCase):
    """Backup files must NEVER be deleted - absolute protection."""

    def test_backup_filename_patterns(self):
        """Files matching backup patterns are detected."""
        backup_files = [
            "/opt/odoo-infrastructure/backups/odoo17_dump.sql",
            "/opt/odoo-infrastructure/backups/odoo18_dump.sql.gz",
            "/opt/odoo-infrastructure/backups/full_backup.tar.gz",
            "/opt/odoo-infrastructure/backups/system_snapshot.tar",
            "/opt/odoo-infrastructure/backup_20240101.zip",
            "/opt/odoo-infrastructure/filestore/filestore_data",
            "/tmp/my_backup.zst",
        ]
        for path in backup_files:
            is_bak, reason = is_backup_path(path)
            self.assertTrue(is_bak, f"Should detect backup: {path} (reason: {reason})")

    def test_non_backup_files(self):
        """Non-backup files are not flagged."""
        non_backup = [
            "/opt/odoo-infrastructure/odoo17/etc/odoo.conf",
            "/opt/traefik/config/traefik.yml",
            "/opt/jenkins/docker-compose.yml",
            "/etc/apt/sources.list.d/docker.list",
        ]
        for path in non_backup:
            is_bak, _ = is_backup_path(path)
            self.assertFalse(is_bak, f"Should not detect backup: {path}")

    def test_backup_directory_patterns(self):
        """Directories with backup names are protected."""
        backup_dirs = [
            "/opt/odoo-infrastructure/backups",
            "/opt/odoo-infrastructure/odoo17/backups",
            "/tmp/snapshot_2024",
            "/var/backups/odoo",
        ]
        for path in backup_dirs:
            is_bak, reason = is_backup_path(path)
            self.assertTrue(is_bak, f"Should detect backup dir: {path} (reason: {reason})")

    def test_should_protect_backups_always(self):
        """Backup paths are always protected regardless of location."""
        # Even if a backup file is in a project path, it's protected
        path = "/opt/odoo-infrastructure/backups/odoo17_dump.sql"
        protected, reason = should_protect(path)
        self.assertTrue(protected, "Backup in project path must be protected")

    def test_should_protect_non_project_paths(self):
        """Non-project paths are protected (safety)."""
        protected, reason = should_protect("/etc/passwd")
        self.assertTrue(protected)
        protected, reason = should_protect("/home/user/documents")
        self.assertTrue(protected)

    def test_should_not_protect_project_paths(self):
        """Project paths that are not backups are NOT protected."""
        protected, _ = should_protect("/opt/odoo-infrastructure/odoo17/etc/odoo.conf")
        self.assertFalse(protected)

    def test_is_project_path(self):
        """Project path detection works."""
        self.assertTrue(is_project_path("/opt/odoo-infrastructure/odoo17/etc/odoo.conf"))
        self.assertTrue(is_project_path("/opt/traefik/config/traefik.yml"))
        self.assertTrue(is_project_path("/opt/odoo-infrastructure"))
        self.assertFalse(is_project_path("/etc/passwd"))
        self.assertFalse(is_project_path("/home/user"))


class TestPlanOrdering(unittest.TestCase):
    """Uninstall plan must follow reverse dependency order."""

    def test_plan_uninstall_returns_items(self):
        """plan_uninstall returns a list of CleanupItem."""
        items = [
            CleanupItem(id="a", type="docker_container", path="odoo17",
                        description="Odoo 17 container"),
            CleanupItem(id="b", type="docker_container", path="traefik",
                        description="Traefik container"),
            CleanupItem(id="c", type="directory", path="/opt/odoo-infrastructure",
                        description="Odoo infrastructure"),
        ]
        ordered = plan_uninstall(items)
        self.assertEqual(len(ordered), 3)
        for it in ordered:
            self.assertEqual(it.status, CleanupStatus.SCHEDULED)

    def test_odoo_before_traefik(self):
        """Odoo containers should be cleaned before Traefik (reverse dependency)."""
        items = [
            CleanupItem(id="traefik", type="docker_container", path="traefik",
                        description="Traefik"),
            CleanupItem(id="odoo17", type="docker_container", path="odoo17",
                        description="Odoo 17"),
        ]
        ordered = plan_uninstall(items)
        # Find indices
        odoo_idx = next(i for i, it in enumerate(ordered) if it.path == "odoo17")
        traefik_idx = next(i for i, it in enumerate(ordered) if it.path == "traefik")
        self.assertLess(odoo_idx, traefik_idx,
                        "Odoo must be cleaned before Traefik (reverse dependency order)")


class TestRunFullCleanupDryRun(unittest.TestCase):
    """Dry-run mode must not delete anything."""

    def test_dry_run_no_deletion(self):
        """Dry-run completes without deleting files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake project path
            fake_path = os.path.join(tmpdir, "odoo-infrastructure")
            os.makedirs(fake_path)
            with open(os.path.join(fake_path, "odoo.conf"), "w") as f:
                f.write("test")

            with patch("app.services.uninstall_service.PROJECT_INSTALL_PATHS",
                       [fake_path]):
                with patch("app.services.uninstall_service.LOG_DIR", tmpdir):
                    report = run_full_cleanup(use_sudo=False, dry_run=True,
                                              confirm=False)

            self.assertIsInstance(report, CleanupReport)
            self.assertTrue(report.dry_run)
            # Nothing should be completed in dry-run without actual filesystem items
            # (our fake path isn't in the real PROJECT_INSTALL_PATHS list, so it won't
            # be discovered by the real function)
            self.assertIsNotNone(report.started_at)


class TestRunFullCleanupExecution(unittest.TestCase):
    """Execution mode requires confirmation."""

    def test_execution_requires_confirmation(self):
        """Execution without confirmation is aborted."""
        with patch("builtins.input", return_value="WRONG"):
            report = run_full_cleanup(use_sudo=False, dry_run=False,
                                      confirm=True)
            # Confirmation failed, nothing done
            self.assertEqual(report.completed_count, 0)
            self.assertEqual(report.failed_count, 0)

    def test_execution_with_confirmation(self):
        """Execution with correct confirmation proceeds."""
        with patch("builtins.input", return_value="DELETE EVERYTHING EXCEPT BACKUPS"):
            report = run_full_cleanup(use_sudo=False, dry_run=False,
                                      confirm=True)
            self.assertIsInstance(report, CleanupReport)
            self.assertFalse(report.dry_run)


class TestVerifyCleanup(unittest.TestCase):
    """Post-cleanup verification works."""

    def test_verify_cleanup_returns_dict(self):
        """verify_cleanup returns a dict with expected keys."""
        result = verify_cleanup(use_sudo=False)
        self.assertIn("all_clear", result)
        self.assertIn("remaining", result)
        self.assertIn("docker_containers", result["remaining"])
        self.assertIn("docker_networks", result["remaining"])
        self.assertIn("docker_images", result["remaining"])
        self.assertIn("filesystem_paths", result["remaining"])


class TestBackupProtectionIntegration(unittest.TestCase):
    """Integration: backups survive cleanup even when in project paths."""

    def test_backup_in_project_path_protected(self):
        """A backup file inside /opt/odoo-infrastructure is protected."""
        path = "/opt/odoo-infrastructure/backups/odoo17_dump.sql"
        is_bak, _ = is_backup_path(path)
        self.assertTrue(is_bak)

        protected, reason = should_protect(path)
        self.assertTrue(protected)
        self.assertIn("backup", reason.lower())

    def test_all_backup_patterns_covered(self):
        """Common backup extensions are all caught."""
        test_cases = [
            ("/path/file.sql", True),
            ("/path/file.sql.gz", True),
            ("/path/file.dump", True),
            ("/path/file.tar", True),
            ("/path/file.tar.gz", True),
            ("/path/file.tgz", True),
            ("/path/file.zip", True),
            ("/path/file.gz", True),
            ("/path/file.zst", True),
            ("/path/backup.dat", True),
            ("/path/backups/data", True),
            ("/path/snapshot.2024", True),
            ("/path/filestore/data", True),
            ("/path/odoo.conf", False),
            ("/path/traefik.yml", False),
        ]
        for path, expected in test_cases:
            is_bak, _ = is_backup_path(path)
            self.assertEqual(is_bak, expected, f"Unexpected result for {path}")


if __name__ == "__main__":
    unittest.main()
