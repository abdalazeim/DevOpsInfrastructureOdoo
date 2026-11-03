"""
Configuration validation engine for Odoo Infrastructure Manager profiles.
Ensures security, syntax correctness, port safety, and component compatibility.
"""
import re
from typing import List, Tuple, Dict, Any
from app.models.profile import InfrastructureProfile

DOMAIN_REGEX = re.compile(
    r'^(?:[a-zA-Z0-9]'
    r'(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+'
    r'[a-zA-Z]{2,63}$|^localhost$'
)

EMAIL_REGEX = re.compile(r'^[\w\.-]+@[\w\.-]+(\.\w+)*$')
CRON_REGEX = re.compile(r'^(\*|([0-9]|1[0-9]|2[0-9]|3[0-9]|4[0-9]|5[0-9])|\*\/[0-9]+)\s+(\*|([0-9]|1[0-9]|2[0-3])|\*\/[0-9]+)\s+(\*|([1-9]|1[0-9]|2[0-9]|3[0-1])|\*\/[0-9]+)\s+(\*|([1-9]|1[0-2])|\*\/[0-9]+)\s+(\*|([0-6])|\*\/[0-9]+)$')

class ConfigValidationResult:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, msg: str):
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

class ConfigValidator:
    """Validates InfrastructureProfile objects before execution."""

    @staticmethod
    def validate(profile: InfrastructureProfile) -> ConfigValidationResult:
        res = ConfigValidationResult()

        # 1. Profile Name
        if not profile.profile_name or not re.match(r'^[a-zA-Z0-9_-]+$', profile.profile_name):
            res.add_error(f"Invalid profile name '{profile.profile_name}'. Must contain only alphanumeric characters, dashes, and underscores.")

        # 2. Server Configuration
        if not profile.server.hostname:
            res.add_error("Server hostname cannot be empty.")
        if profile.server.ssh_port <= 0 or profile.server.ssh_port > 65535:
            res.add_error(f"Invalid SSH port: {profile.server.ssh_port}. Must be between 1 and 65535.")

        # 3. Path Security Validations
        dangerous_roots = ["", "/", "/bin", "/sbin", "/usr", "/etc", "/var", "/root", "/boot", "/sys", "/dev", "/proc"]
        data_root_clean = profile.paths.data_root.strip().rstrip("/")
        if data_root_clean in dangerous_roots or profile.paths.data_root.strip() in ["", "/"]:
            res.add_error(f"Critical Security Alert: data_root '{profile.paths.data_root}' cannot be a root system directory!")

        backup_root_clean = profile.paths.backup_root.strip().rstrip("/")
        if backup_root_clean in dangerous_roots or profile.paths.backup_root.strip() in ["", "/"]:
            res.add_error(f"Critical Security Alert: backup_root '{profile.paths.backup_root}' cannot be a root system directory!")

        # 4. Port Conflict Validations
        used_ports = {}
        if profile.traefik.enabled:
            for p_name, p_val in [("Traefik HTTP", profile.traefik.http_port), ("Traefik HTTPS", profile.traefik.https_port)]:
                if p_val <= 0 or p_val > 65535:
                    res.add_error(f"Invalid port for {p_name}: {p_val}")
                elif p_val in used_ports:
                    res.add_error(f"Port collision detected: Port {p_val} is used by both {used_ports[p_val]} and {p_name}.")
                else:
                    used_ports[p_val] = p_name

        # 5. Domain & TLS Checks
        if profile.traefik.enabled:
            if not DOMAIN_REGEX.match(profile.traefik.dashboard_domain):
                res.add_error(f"Invalid Traefik dashboard domain: '{profile.traefik.dashboard_domain}'")
            if not EMAIL_REGEX.match(profile.traefik.acme_email):
                res.add_error(f"Invalid ACME Let's Encrypt email: '{profile.traefik.acme_email}'")

        if profile.odoo17.enabled:
            if not DOMAIN_REGEX.match(profile.odoo17.domain):
                res.add_error(f"Invalid Odoo 17 domain: '{profile.odoo17.domain}'")
            if profile.traefik.enabled and profile.odoo17.domain == profile.traefik.dashboard_domain:
                res.add_error("Domain collision: Odoo 17 domain cannot be identical to Traefik dashboard domain.")

        if profile.odoo19.enabled:
            if not DOMAIN_REGEX.match(profile.odoo19.domain):
                res.add_error(f"Invalid Odoo 19 domain: '{profile.odoo19.domain}'")
            if profile.odoo17.enabled and profile.odoo19.domain == profile.odoo17.domain:
                res.add_error("Domain collision: Odoo 19 domain cannot be identical to Odoo 17 domain.")

        # 6. Database Compatibility Checks
        # Odoo 17 is officially compatible with PostgreSQL 12-16
        if profile.odoo17.enabled:
            pg17_image = profile.odoo17.database.engine.lower()
            if "17" in pg17_image or "18" in pg17_image:
                res.add_warning(f"Odoo 17 is tested primarily with PostgreSQL 13-16. Specified engine: '{profile.odoo17.database.engine}'. Verify compatibility.")
            if profile.odoo17.database.expose_public_port:
                res.add_warning("Security Warning: Odoo 17 PostgreSQL database port is exposed publicly. Recommended to keep internal only.")

        # Odoo 19 uses PostgreSQL 16-18
        if profile.odoo19.enabled:
            if profile.odoo19.database.expose_public_port:
                res.add_warning("Security Warning: Odoo 19 PostgreSQL database port is exposed publicly. Recommended to keep internal only.")

        # 7. Backup Policy Checks
        if profile.backup.enabled:
            if profile.backup.retention_count < 1:
                res.add_error(f"Backup retention_count must be at least 1 (provided: {profile.backup.retention_count})")
            if not CRON_REGEX.match(profile.backup.cron_schedule.strip()):
                res.add_warning(f"Cron expression '{profile.backup.cron_schedule}' may not be standard 5-part cron syntax.")

        # 8. Secret Hygiene Check
        for odoo_inst in [profile.odoo17, profile.odoo19]:
            if odoo_inst.enabled:
                if not odoo_inst.database.password_env_var.startswith("ODOO"):
                    res.add_warning(f"Environment variable name '{odoo_inst.database.password_env_var}' should follow standard naming convention.")

        return res
