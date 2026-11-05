"""
Unit tests for configuration and system validators.
"""
import unittest
from app.models.profile import (
    InfrastructureProfile, ServerConfig, PathsConfig, TraefikConfig,
    OdooInstanceConfig, DatabaseConfig, BackupConfig
)
from app.validators.config_validator import ConfigValidator
from app.validators.system_validator import SystemValidator

class TestConfigValidator(unittest.TestCase):
    def setUp(self):
        self.valid_profile = InfrastructureProfile(
            profile_name="test-profile",
            server=ServerConfig(hostname="devops-odoo", ip_or_host="192.168.1.100"),
            paths=PathsConfig(data_root="/opt/odoo-data", backup_root="/opt/odoo-backups"),
            traefik=TraefikConfig(dashboard_domain="traefik.localhost", acme_email="admin@localhost"),
            odoo17=OdooInstanceConfig(domain="odoo17-1.localhost"),
            odoo19=OdooInstanceConfig(domain="odoo19-1.localhost"),
        )

    def test_valid_profile_passes(self):
        res = ConfigValidator.validate(self.valid_profile)
        self.assertTrue(res.is_valid)
        self.assertEqual(len(res.errors), 0)

    def test_invalid_profile_name(self):
        self.valid_profile.profile_name = "invalid name with spaces!"
        res = ConfigValidator.validate(self.valid_profile)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("Invalid profile name" in err for err in res.errors))

    def test_dangerous_root_path_rejected(self):
        self.valid_profile.paths.data_root = "/"
        res = ConfigValidator.validate(self.valid_profile)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("Critical Security Alert" in err for err in res.errors))

    def test_port_collision_detected(self):
        self.valid_profile.traefik.http_port = 443
        self.valid_profile.traefik.https_port = 443
        res = ConfigValidator.validate(self.valid_profile)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("Port collision" in err for err in res.errors))

    def test_domain_collision_detected(self):
        self.valid_profile.odoo19.domain = self.valid_profile.odoo17.domain
        res = ConfigValidator.validate(self.valid_profile)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("Domain collision" in err for err in res.errors))

    def test_invalid_email_format(self):
        self.valid_profile.traefik.acme_email = "invalid-email-no-domain"
        res = ConfigValidator.validate(self.valid_profile)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("Invalid ACME" in err for err in res.errors))

    def test_invalid_retention_count(self):
        self.valid_profile.backup.retention_count = 0
        res = ConfigValidator.validate(self.valid_profile)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("retention_count" in err for err in res.errors))

class TestSystemValidator(unittest.TestCase):
    def test_check_port_free_returns_object(self):
        item = SystemValidator.check_port_free(59999)
        self.assertIsNotNone(item.name)
        self.assertTrue(isinstance(item.passed, bool))

    def test_check_disk_space_returns_valid_reading(self):
        item = SystemValidator.check_disk_space("/")
        self.assertIsNotNone(item.name)
        self.assertIn("GB", item.message)

if __name__ == "__main__":
    unittest.main()
