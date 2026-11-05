"""
Profile configuration dataclass models for Odoo Infrastructure Manager.
Domain defaults are populated from the centralized HostnameConfig at runtime.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import re

from app.config.hostname_config import get_config, HostnameConfig


def _default_domain() -> str:
    """Get primary domain from centralized config, or empty string if not configured."""
    try:
        return get_config().primary_domain
    except RuntimeError:
        return ""


def _default_acme_email() -> str:
    """Get ACME email from centralized config domain."""
    try:
        return f"admin@{get_config().primary_domain}"
    except RuntimeError:
        return "admin@localhost"


def _default_traefik_domain() -> str:
    """Get traefik subdomain from centralized config."""
    try:
        return get_config().traefik_domain
    except RuntimeError:
        return "traefik.localhost"


def _default_odoo_domain(version: str, instance: str) -> str:
    """Get Odoo instance subdomain from centralized config."""
    try:
        cfg = get_config()
        if version == "17" and instance == "1":
            return cfg.odoo17_instance1_domain
        if version == "17" and instance == "2":
            return cfg.odoo17_instance2_domain
        if version == "18" and instance == "1":
            return cfg.odoo18_instance1_domain
        if version == "18" and instance == "2":
            return cfg.odoo18_instance2_domain
        if version == "19" and instance == "1":
            return cfg.odoo19_instance1_domain
        if version == "19" and instance == "2":
            return cfg.odoo19_instance2_domain
    except RuntimeError:
        pass
    return f"{version}-{instance}.localhost"


@dataclass
class ServerConfig:
    hostname: str = "devops-odoo"
    ip_or_host: str = "127.0.0.1"
    timezone: str = "UTC"
    ssh_user: str = "ubuntu"
    ssh_port: int = 22

@dataclass
class PathsConfig:
    project_root: str = "/opt/odoo-infrastructure-manager"
    data_root: str = "/opt/odoo-infrastructure"
    backup_root: str = "/opt/odoo-infrastructure/backups"

@dataclass
class NetworkConfig:
    proxy_network_name: str = "proxy"
    proxy_subnet: str = "172.28.0.0/16"
    enable_ipv6: bool = False

@dataclass
class TraefikConfig:
    enabled: bool = True
    image: str = "traefik:v3.7"
    dashboard_enabled: bool = True
    dashboard_domain: str = field(default_factory=_default_traefik_domain)
    acme_email: str = field(default_factory=_default_acme_email)
    acme_challenge: str = "http"
    http_port: int = 80
    https_port: int = 443

@dataclass
class DatabaseConfig:
    engine: str = "postgres:16-alpine"
    name: str = "odoo17_prod"
    user: str = "odoo"
    password_env_var: str = "ODOO17_DB_PASSWORD"
    admin_password_env_var: str = "ODOO17_ADMIN_PASSWORD"
    internal_port: int = 5432
    expose_public_port: bool = False

@dataclass
class OdooInstanceConfig:
    enabled: bool = True
    version: str = "17"
    domain: str = field(default_factory=_default_domain)
    image: str = "odoo:17.0"
    workers: int = 3
    http_port: int = 0
    memory_limit_soft: str = "2147483648"
    memory_limit_hard: str = "2684354560"
    database: DatabaseConfig = field(default_factory=DatabaseConfig)

@dataclass
class BackupConfig:
    enabled: bool = True
    cron_schedule: str = "0 2 * * *"
    retention_count: int = 7
    include_filestore: bool = True
    compression: str = "gzip"
    verify_checksum: bool = True

@dataclass
class SecurityConfig:
    strict_file_permissions: bool = True
    acme_mode_600: bool = True
    isolate_postgres_network: bool = True
    enforce_https: bool = True

@dataclass
class InfrastructureProfile:
    profile_name: str
    deployment_mode: str = "local"
    jenkins_enabled: bool = False
    description: str = ""
    version: str = "1.0.0"
    server: ServerConfig = field(default_factory=ServerConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    traefik: TraefikConfig = field(default_factory=TraefikConfig)
    odoo17: OdooInstanceConfig = field(default_factory=lambda: OdooInstanceConfig(
        version="17",
        domain=_default_odoo_domain("17", "1"),
        image="odoo:17.0",
        database=DatabaseConfig(engine="postgres:16-alpine", name="odoo17_prod", password_env_var="ODOO17_DB_PASSWORD")
    ))
    odoo18: OdooInstanceConfig = field(default_factory=lambda: OdooInstanceConfig(
        version="18",
        domain=_default_odoo_domain("18", "1"),
        image="odoo:18.0",
        database=DatabaseConfig(engine="postgres:17-alpine", name="odoo18_prod", password_env_var="ODOO18_DB_PASSWORD")
    ))
    odoo19: OdooInstanceConfig = field(default_factory=lambda: OdooInstanceConfig(
        version="19",
        domain=_default_odoo_domain("19", "1"),
        image="odoo:19.0",
        database=DatabaseConfig(engine="postgres:18-alpine", name="odoo19_prod", password_env_var="ODOO19_DB_PASSWORD")
    ))
    backup: BackupConfig = field(default_factory=BackupConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InfrastructureProfile":
        server_data = data.get("server", {})
        server = ServerConfig(
            hostname=server_data.get("hostname", "devops-odoo"),
            ip_or_host=server_data.get("ip_or_host", "127.0.0.1"),
            timezone=server_data.get("timezone", "UTC"),
            ssh_user=server_data.get("ssh_user", "ubuntu"),
            ssh_port=int(server_data.get("ssh_port", 22)),
        )

        paths_data = data.get("paths", {})
        paths = PathsConfig(
            project_root=paths_data.get("project_root", "/opt/odoo-infrastructure-manager"),
            data_root=paths_data.get("data_root", "/opt/odoo-infrastructure"),
            backup_root=paths_data.get("backup_root", "/opt/odoo-infrastructure/backups"),
        )

        net_data = data.get("network", {})
        network = NetworkConfig(
            proxy_network_name=net_data.get("proxy_network_name", "proxy"),
            proxy_subnet=net_data.get("proxy_subnet", "172.28.0.0/16"),
            enable_ipv6=bool(net_data.get("enable_ipv6", False)),
        )

        tr_data = data.get("traefik", {})
        traefik = TraefikConfig(
            enabled=bool(tr_data.get("enabled", True)),
            image=tr_data.get("image", "traefik:v3.7"),
            dashboard_enabled=bool(tr_data.get("dashboard_enabled", True)),
            dashboard_domain=tr_data.get("dashboard_domain", _default_traefik_domain()),
            acme_email=tr_data.get("acme_email", _default_acme_email()),
            acme_challenge=tr_data.get("acme_challenge", "http"),
            http_port=int(tr_data.get("http_port", 80)),
            https_port=int(tr_data.get("https_port", 443)),
        )

        o17_data = data.get("odoo17", {})
        o17_db_data = o17_data.get("database", {})
        odoo17 = OdooInstanceConfig(
            enabled=bool(o17_data.get("enabled", True)),
            version="17",
            http_port=int(o17_data.get("http_port", 10017)),
            domain=o17_data.get("domain", _default_odoo_domain("17", "1")),
            image=o17_data.get("image", "odoo:17.0"),
            workers=int(o17_data.get("workers", 3)),
            memory_limit_soft=str(o17_data.get("memory_limit_soft", "2147483648")),
            memory_limit_hard=str(o17_data.get("memory_limit_hard", "2684354560")),
            database=DatabaseConfig(
                engine=o17_db_data.get("engine", "postgres:16-alpine"),
                name=o17_db_data.get("name", "odoo17_prod"),
                user=o17_db_data.get("user", "odoo"),
                password_env_var=o17_db_data.get("password_env_var", "ODOO17_DB_PASSWORD"),
                admin_password_env_var=o17_db_data.get("admin_password_env_var", "ODOO17_ADMIN_PASSWORD"),
                internal_port=int(o17_db_data.get("internal_port", 5432)),
                expose_public_port=bool(o17_db_data.get("expose_public_port", False)),
            )
        )

        o18_data = data.get("odoo18", {})
        o18_db_data = o18_data.get("database", {})
        odoo18 = OdooInstanceConfig(
            enabled=bool(o18_data.get("enabled", True)),
            version="18",
            http_port=int(o18_data.get("http_port", 10018)),
            domain=o18_data.get("domain", _default_odoo_domain("18", "1")),
            image=o18_data.get("image", "odoo:18.0"),
            workers=int(o18_data.get("workers", 3)),
            memory_limit_soft=str(o18_data.get("memory_limit_soft", "2147483648")),
            memory_limit_hard=str(o18_data.get("memory_limit_hard", "2684354560")),
            database=DatabaseConfig(
                engine=o18_db_data.get("engine", "postgres:17-alpine"),
                name=o18_db_data.get("name", "odoo18_prod"),
                user=o18_db_data.get("user", "odoo"),
                password_env_var=o18_db_data.get("password_env_var", "ODOO18_DB_PASSWORD"),
                admin_password_env_var=o18_db_data.get("admin_password_env_var", "ODOO18_ADMIN_PASSWORD"),
                internal_port=int(o18_db_data.get("internal_port", 5432)),
                expose_public_port=bool(o18_db_data.get("expose_public_port", False)),
            )
        )

        o19_data = data.get("odoo19", {})
        o19_db_data = o19_data.get("database", {})
        odoo19 = OdooInstanceConfig(
            enabled=bool(o19_data.get("enabled", True)),
            version="19",
            http_port=int(o19_data.get("http_port", 10019)),
            domain=o19_data.get("domain", _default_odoo_domain("19", "1")),
            image=o19_data.get("image", "odoo:19.0"),
            workers=int(o19_data.get("workers", 3)),
            memory_limit_soft=str(o19_data.get("memory_limit_soft", "2684354560")),
            memory_limit_hard=str(o19_data.get("memory_limit_hard", "3221225472")),
            database=DatabaseConfig(
                engine=o19_db_data.get("engine", "postgres:18-alpine"),
                name=o19_db_data.get("name", "odoo19_prod"),
                user=o19_db_data.get("user", "odoo"),
                password_env_var=o19_db_data.get("password_env_var", "ODOO19_DB_PASSWORD"),
                admin_password_env_var=o19_db_data.get("admin_password_env_var", "ODOO19_ADMIN_PASSWORD"),
                internal_port=int(o19_db_data.get("internal_port", 5432)),
                expose_public_port=bool(o19_db_data.get("expose_public_port", False)),
            )
        )

        b_data = data.get("backup", {})
        backup = BackupConfig(
            enabled=bool(b_data.get("enabled", True)),
            cron_schedule=b_data.get("cron_schedule", "0 2 * * *"),
            retention_count=int(b_data.get("retention_count", 7)),
            include_filestore=bool(b_data.get("include_filestore", True)),
            compression=b_data.get("compression", "gzip"),
            verify_checksum=bool(b_data.get("verify_checksum", True)),
        )

        s_data = data.get("security", {})
        security = SecurityConfig(
            strict_file_permissions=bool(s_data.get("strict_file_permissions", True)),
            acme_mode_600=bool(s_data.get("acme_mode_600", True)),
            isolate_postgres_network=bool(s_data.get("isolate_postgres_network", True)),
            enforce_https=bool(s_data.get("enforce_https", True)),
        )

        return cls(
            deployment_mode=data.get("deployment_mode", "local"),
            jenkins_enabled=bool(data.get("jenkins_enabled", False)),
            profile_name=data.get("profile_name", "unnamed-profile"),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            server=server,
            paths=paths,
            network=network,
            traefik=traefik,
            odoo17=odoo17,
            odoo18=odoo18,
            odoo19=odoo19,
            backup=backup,
            security=security,
        )
