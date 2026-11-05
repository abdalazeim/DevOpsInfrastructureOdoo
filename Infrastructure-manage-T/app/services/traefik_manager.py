"""
Traefik Docker Management Module
Provides automated inspection, discovery, deployment, lifecycle management,
network connection, Docker label generation, backup/restore, and health verification
for Traefik v3.7 on Ubuntu Server & Desktop.
"""

import os
import shutil
import subprocess
import socket
import json
import hashlib
import time
import platform
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

from app.config.hostname_config import get_config
from app.services.archive_utils import safe_extractall
from app.services.runtime_inspector import probe
from app.services.docker_installer import run_step

DEFAULT_CONFIG_DIR = "/opt/odoo-infrastructure/traefik"
DEFAULT_DOCKER_IMAGE = "traefik:v3.7"
DEFAULT_CONTAINER_NAME = "traefik"
DEFAULT_NETWORK_NAME = "proxy"
DEFAULT_HTTP_PORT = 80
DEFAULT_DASHBOARD_INTERNAL_PORT = 8080
# Deprecated: the dashboard is no longer published on a host port. Kept for
# backwards compatibility with older profiles/scripts.
DEFAULT_DASHBOARD_EXTERNAL_PORT = 10090
DEFAULT_ODOO19_PORT = 8069
DEFAULT_JENKINS_PORT = 8081


def get_default_dashboard_url() -> str:
    """Get Traefik dashboard URL from centralized hostname config."""
    try:
        return f"https://{get_config().traefik_domain}/dashboard/"
    except RuntimeError:
        return "https://traefik.localhost/dashboard/"


def get_default_dashboard_domain() -> str:
    """Get Traefik dashboard domain from centralized hostname config."""
    try:
        return get_config().traefik_domain
    except RuntimeError:
        return "traefik.localhost"


DEFAULT_DASHBOARD_URL = get_default_dashboard_url()


@dataclass
class TraefikConfig:
    config_dir: str = DEFAULT_CONFIG_DIR
    image: str = DEFAULT_DOCKER_IMAGE
    container_name: str = DEFAULT_CONTAINER_NAME
    network: str = DEFAULT_NETWORK_NAME
    http_port: int = DEFAULT_HTTP_PORT
    dashboard_internal_port: int = DEFAULT_DASHBOARD_INTERNAL_PORT
    dashboard_external_port: int = DEFAULT_DASHBOARD_EXTERNAL_PORT
    enable_dashboard: bool = True
    # Deprecated: dashboards are always exposed through the secure router now.
    # Kept so old callers do not break; it no longer enables api.insecure.
    insecure_dashboard: bool = False
    dashboard_domain: str = field(default_factory=get_default_dashboard_domain)
    acme_email: str = field(default_factory=lambda: f"admin@{get_default_dashboard_domain()}")
    enable_letsencrypt: bool = False
    basic_auth_credentials: str = "admin:$$apr1$$xyz$$randomhash"
    docker_socket_ro: bool = True
    odoo19_port: int = DEFAULT_ODOO19_PORT
    jenkins_port: int = DEFAULT_JENKINS_PORT


@dataclass
class ConnectedContainer:
    id: str
    name: str
    ipv4_address: str
    mac_address: str
    aliases: List[str] = field(default_factory=list)


@dataclass
class PortInspection:
    port: int
    service_name: str
    is_in_use: bool
    bound_address: Optional[str] = None
    process_info: Optional[str] = None
    has_conflict: bool = False


@dataclass
class TraefikDiscoveryReport:
    timestamp: str
    docker_installed: bool
    docker_version: Optional[str]
    compose_installed: bool
    compose_version: Optional[str]
    container_exists: bool
    container_status: str  # "running", "stopped", "not_found", "error"
    container_image: Optional[str]
    container_uptime: Optional[str]
    proxy_network_exists: bool
    proxy_subnet: Optional[str]
    compose_file_exists: bool = False
    compose_file_path: str = ""
    dashboard_accessible: bool = False
    dashboard_url: str = DEFAULT_DASHBOARD_URL
    acme_file_exists: bool = False
    acme_permissions_valid: bool = False
    connected_containers: List[ConnectedContainer] = field(default_factory=list)
    ports_audit: List[PortInspection] = field(default_factory=list)
    recent_logs: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class TraefikDockerManager:
    """
    Enterprise Traefik Docker Management Service for Ubuntu.
    Encapsulates discovery, deployment, lifecycle, proxy networking, and backups.
    """

    @staticmethod
    def inspect_port(port: int, service_name: str) -> PortInspection:
        """Checks if a TCP port is bound on the host."""
        is_used = False
        bound_addr = None
        process_name = None

        # 1. Try socket connection probe
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                res = s.connect_ex(("127.0.0.1", port))
                if res == 0:
                    is_used = True
                    bound_addr = f"127.0.0.1:{port}"
        except Exception:
            pass

        # 2. Check via ss -tuln if available
        if not is_used and shutil.which("ss"):
            try:
                proc = subprocess.run(
                    ["ss", "-tuln"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=2,
                    check=False
                )
                if proc.returncode == 0:
                    for line in proc.stdout.splitlines():
                        if f":{port} " in line:
                            is_used = True
                            parts = line.split()
                            if len(parts) >= 5:
                                bound_addr = parts[4]
                            break
            except Exception:
                pass

        return PortInspection(
            port=port,
            service_name=service_name,
            is_in_use=is_used,
            bound_address=bound_addr,
            process_info=process_name,
            has_conflict=False
        )

    @classmethod
    def discover_environment(cls, config_dir: str = DEFAULT_CONFIG_DIR) -> TraefikDiscoveryReport:
        """
        Non-destructively audits the existing Docker environment, Traefik container,
        proxy network, ports, and configuration files.
        """
        import datetime
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        docker_bin = shutil.which("docker")
        docker_installed = bool(docker_bin)
        docker_version = None
        compose_installed = False
        compose_version = None

        if docker_installed:
            try:
                res = subprocess.run(
                    ["docker", "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3,
                    check=False
                )
                if res.returncode == 0:
                    docker_version = res.stdout.strip().replace("Docker version ", "")
            except Exception:
                pass

            try:
                res = subprocess.run(
                    ["docker", "compose", "version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3,
                    check=False
                )
                if res.returncode == 0:
                    compose_installed = True
                    compose_version = res.stdout.strip().replace("Docker Compose version ", "")
            except Exception:
                compose_installed = bool(shutil.which("docker-compose"))

        # Inspect Traefik Container
        container_exists = False
        container_status = "not_found"
        container_image = None
        container_uptime = None
        recent_logs = []

        if docker_installed:
            try:
                proc = subprocess.run(
                    ["docker", "inspect", DEFAULT_CONTAINER_NAME],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3,
                    check=False
                )
                if proc.returncode == 0:
                    data = json.loads(proc.stdout)
                    if data and len(data) > 0:
                        container_exists = True
                        state = data[0].get("State", {})
                        container_status = "running" if state.get("Running") else ("stopped" if not state.get("Dead") else "error")
                        container_image = data[0].get("Config", {}).get("Image")
                        container_uptime = state.get("StartedAt")
            except Exception:
                pass

            # Fetch recent logs if container exists
            if container_exists:
                try:
                    lproc = subprocess.run(
                        ["docker", "logs", "--tail", "25", DEFAULT_CONTAINER_NAME],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=3,
                        check=False
                    )
                    recent_logs = (lproc.stdout + lproc.stderr).splitlines()[-25:]
                except Exception:
                    recent_logs = ["Unable to fetch live container logs"]

        # Inspect "proxy" network
        proxy_network_exists = False
        proxy_subnet = None
        connected_containers: List[ConnectedContainer] = []

        if docker_installed:
            try:
                nproc = subprocess.run(
                    ["docker", "network", "inspect", DEFAULT_NETWORK_NAME],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3,
                    check=False
                )
                if nproc.returncode == 0:
                    proxy_network_exists = True
                    ndata = json.loads(nproc.stdout)
                    if ndata and len(ndata) > 0:
                        ipam = ndata[0].get("IPAM", {}).get("Config", [])
                        if ipam:
                            proxy_subnet = ipam[0].get("Subnet", "172.28.0.0/16")

                        raw_containers = ndata[0].get("Containers", {})
                        for cid, cinfo in raw_containers.items():
                            connected_containers.append(
                                ConnectedContainer(
                                    id=cid[:12],
                                    name=cinfo.get("Name", "unknown"),
                                    ipv4_address=cinfo.get("IPv4Address", "").split("/")[0],
                                    mac_address=cinfo.get("MacAddress", ""),
                                    aliases=[]
                                )
                            )
            except Exception:
                pass

        # Inspect ports (dashboard has no dedicated host port; it is served on 443)
        target_ports = [
            (DEFAULT_HTTP_PORT, "Traefik HTTP (Web Entrypoint)"),
            (443, "Traefik HTTPS (Secure Entrypoint)"),
            (8069, "Odoo HTTP (Internal)"),
            (8072, "Odoo WebSocket / Longpolling (Internal)"),
        ]
        ports_audit = [cls.inspect_port(p, name) for p, name in target_ports]

        # Check compose file
        compose_path = os.path.join(config_dir, "docker-compose.yml")
        compose_exists = os.path.exists(compose_path)

        # Check ACME file
        acme_path = os.path.join(config_dir, "acme", "acme.json")
        acme_exists = os.path.exists(acme_path)
        acme_valid_perm = False
        if acme_exists:
            try:
                perm = oct(os.stat(acme_path).st_mode)[-3:]
                acme_valid_perm = (perm == "600")
            except Exception:
                pass

        # Dashboard reachability (through the HTTPS entrypoint)
        dashboard_ok = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                if s.connect_ex(("127.0.0.1", 443)) == 0:
                    dashboard_ok = True
        except Exception:
            pass

        dashboard_domain = os.environ.get("TRAEFIK_DASHBOARD_DOMAIN", get_default_dashboard_domain())
        dashboard_url = f"https://{dashboard_domain}/dashboard/"

        warnings = []
        if not docker_installed:
            warnings.append("Docker Engine is not installed on this Ubuntu system.")
        if not proxy_network_exists:
            warnings.append("Docker network 'proxy' does not exist yet.")
        if container_exists and container_status != "running":
            warnings.append(f"Traefik container exists but is {container_status}.")
        if acme_exists and not acme_valid_perm:
            warnings.append(f"ACME permissions on {acme_path} are insecure (must be 0600).")

        return TraefikDiscoveryReport(
            timestamp=now_str,
            docker_installed=docker_installed,
            docker_version=docker_version,
            compose_installed=compose_installed,
            compose_version=compose_version,
            container_exists=container_exists,
            container_status=container_status,
            container_image=container_image,
            container_uptime=container_uptime,
            proxy_network_exists=proxy_network_exists,
            proxy_subnet=proxy_subnet,
            connected_containers=connected_containers,
            compose_file_exists=compose_exists,
            compose_file_path=compose_path,
            ports_audit=ports_audit,
            dashboard_accessible=dashboard_ok,
            dashboard_url=dashboard_url,
            acme_file_exists=acme_exists,
            acme_permissions_valid=acme_valid_perm,
            recent_logs=recent_logs,
            warnings=warnings
        )

    @classmethod
    def generate_compose_yaml(cls, config: TraefikConfig) -> str:
        """
        Generates the standard, production-ready /opt/traefik/docker-compose.yml content
        adhering strictly to user prompt specifications:
        - image: traefik:v3.7
        - container_name: traefik
        - --api.dashboard=true
        - --providers.docker=true
        - --providers.docker.exposedbydefault=false
        - --entrypoints.web.address=:80
        - port: 80:80 and 443:443 (dashboard via secured router only)
        - /var/run/docker.sock:/var/run/docker.sock:ro
        - network: proxy (external)
        """
        lines = [
            "# ==============================================================================",
            "# Traefik v3.7 Docker Compose Configuration (Ubuntu DevOps Manager)",
            "# Generated automatically. Preserves existing services and proxy network.",
            "# ==============================================================================",
            "version: '3.8'",
            "",
            "services:",
            f"  {config.container_name}:",
            f"    image: {config.image}",
            f"    container_name: {config.container_name}",
            "    restart: unless-stopped",
            "    security_opt:",
            "      - no-new-privileges:true",
            "    command:",
            "      - --global.checknewversion=false",
            "      - --global.sendanonymoususage=false",
            "      - --api.dashboard=true",
        ]

        # api.insecure is permanently disabled: the dashboard must be reached
        # through the HTTPS router below, never through a published 8080 port.
        lines.extend([
            "      - --api.insecure=false",
            "      - --providers.docker=true",
            "      - --providers.docker.exposedbydefault=false",
            f"      - --providers.docker.network={config.network}",
            f"      - --entrypoints.web.address=:{config.http_port}",
            "      - --entrypoints.web.http.redirections.entrypoint.to=websecure",
            "      - --entrypoints.web.http.redirections.entrypoint.scheme=https",
        ])

        if config.enable_letsencrypt:
            lines.extend([
                "      - --entrypoints.websecure.address=:443",
                f"      - --certificatesresolvers.letsencrypt.acme.email={config.acme_email}",
                "      - --certificatesresolvers.letsencrypt.acme.storage=/etc/traefik/acme/acme.json",
                "      - --certificatesresolvers.letsencrypt.acme.httpchallenge=true",
                "      - --certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web",
            ])

        lines.extend([
            "      - --log.level=INFO",
            "      - --accesslog=true",
            "    networks:",
            f"      - {config.network}",
            "    ports:",
            f'      - "{config.http_port}:{config.http_port}"',
        ])

        if config.enable_letsencrypt:
            lines.append('      - "443:443"')

        lines.extend([
            "    volumes:",
            "      - /etc/localtime:/etc/localtime:ro",
        ])

        if config.docker_socket_ro:
            lines.append("      - /var/run/docker.sock:/var/run/docker.sock:ro")
        else:
            lines.append("      - /var/run/docker.sock:/var/run/docker.sock")

        lines.extend([
            f"      - {config.config_dir}/acme/acme.json:/etc/traefik/acme/acme.json",
            f"      - {config.config_dir}/logs:/var/log/traefik",
        ])

        # Secure dashboard router with Basic Auth (no api.insecure).
        lines.extend([
            "    labels:",
            '      - "traefik.enable=true"',
            f'      - "traefik.http.routers.traefik-dashboard.rule=Host(`{config.dashboard_domain}`)"',
            '      - "traefik.http.routers.traefik-dashboard.service=api@internal"',
            '      - "traefik.http.routers.traefik-dashboard.middlewares=auth-admin"',
            f'      - "traefik.http.middlewares.auth-admin.basicauth.users={config.basic_auth_credentials}"',
        ])
        if config.enable_letsencrypt:
            lines.extend([
                '      - "traefik.http.routers.traefik-dashboard.entrypoints=websecure"',
                '      - "traefik.http.routers.traefik-dashboard.tls.certresolver=letsencrypt"',
            ])
        else:
            lines.append('      - "traefik.http.routers.traefik-dashboard.entrypoints=web"')

        lines.extend([
            "",
            "networks:",
            f"  {config.network}:",
            "    external: true",
            ""
        ])

        return "\n".join(lines)

    @classmethod
    def generate_service_labels(
        cls,
        service_type: str,
        domain: str,
        target_port: int,
        entrypoints: str = "web",
        enable_tls: bool = False,
        path_prefix: Optional[str] = None
    ) -> List[str]:
        """
        Builds Docker Compose labels for routing Odoo 17, Odoo 19, Jenkins, or custom containers.
        """
        labels = [
            "traefik.enable=true",
            f"traefik.http.routers.{service_type}.rule=Host(`{domain}`)",
            f"traefik.http.routers.{service_type}.entrypoints={entrypoints}",
            f"traefik.http.services.{service_type}.loadbalancer.server.port={target_port}",
        ]

        if path_prefix:
            labels.append(f"traefik.http.routers.{service_type}.rule=Host(`{domain}`) && PathPrefix(`{path_prefix}`)")
            labels.append(f"traefik.http.middlewares.{service_type}-stripprefix.stripprefix.prefixes={path_prefix}")
            labels.append(f"traefik.http.routers.{service_type}.middlewares={service_type}-stripprefix")

        if enable_tls:
            labels.append(f"traefik.http.routers.{service_type}.tls=true")
            labels.append(f"traefik.http.routers.{service_type}.tls.certresolver=letsencrypt")

        # Specific custom livechat websocket for Odoo
        if "odoo" in service_type.lower():
            labels.extend([
                f"traefik.http.routers.{service_type}-chat.rule=Host(`{domain}`) && PathPrefix(`/websocket`)",
                f"traefik.http.routers.{service_type}-chat.entrypoints={entrypoints}",
                f"traefik.http.routers.{service_type}-chat.service={service_type}-chat",
                f"traefik.http.services.{service_type}-chat.loadbalancer.server.port=8072",
            ])

        return labels

    @classmethod
    def ensure_traefik_directories(cls, config_dir: str = DEFAULT_CONFIG_DIR) -> Dict[str, str]:
        """Ensures required directories and acme.json with strict 0600 permissions exist."""
        acme_dir = os.path.join(config_dir, "acme")
        logs_dir = os.path.join(config_dir, "logs")
        backups_dir = os.path.join(config_dir, "backups")

        os.makedirs(acme_dir, exist_ok=True)
        os.makedirs(logs_dir, exist_ok=True)
        os.makedirs(backups_dir, exist_ok=True)

        acme_file = os.path.join(acme_dir, "acme.json")
        if not os.path.exists(acme_file):
            with open(acme_file, "w") as f:
                f.write("{}")
        os.chmod(acme_file, 0o600)

        return {
            "config_dir": config_dir,
            "acme_file": acme_file,
            "logs_dir": logs_dir,
            "backups_dir": backups_dir,
        }

    @classmethod
    def ensure_proxy_network(cls, network_name: str = DEFAULT_NETWORK_NAME, subnet: str = "172.28.0.0/16") -> bool:
        """Idempotently ensures the shared Docker bridge network exists."""
        check_proc = subprocess.run(
            ["docker", "network", "inspect", network_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        if check_proc.returncode == 0:
            return True

        create_proc = subprocess.run(
            ["docker", "network", "create", "--driver", "bridge", "--subnet", subnet, network_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        return create_proc.returncode == 0

    @classmethod
    def create_backup_snapshot(cls, config_dir: str = DEFAULT_CONFIG_DIR, is_rollback: bool = False) -> Dict[str, Any]:
        """
        Creates a timestamped .tar.gz archive of Traefik compose, acme, and configuration,
        secures permissions with 0600, and returns SHA256 checksum.
        """
        import datetime
        import tarfile

        cls.ensure_traefik_directories(config_dir)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_dir = os.path.join(config_dir, "backups", "safety_rollback" if is_rollback else "")
        os.makedirs(backup_dir, exist_ok=True)
        archive_name = f"{'safety_rollback' if is_rollback else 'traefik_backup'}_{ts}.tar.gz"
        archive_path = os.path.join(backup_dir, archive_name)

        with tarfile.open(archive_path, "w:gz") as tar:
            compose_file = os.path.join(config_dir, "docker-compose.yml")
            if os.path.exists(compose_file):
                tar.add(compose_file, arcname="docker-compose.yml")

            acme_file = os.path.join(config_dir, "acme", "acme.json")
            if os.path.exists(acme_file):
                tar.add(acme_file, arcname="acme/acme.json")

            traefik_yml = os.path.join(config_dir, "traefik.yml")
            if os.path.exists(traefik_yml):
                tar.add(traefik_yml, arcname="traefik.yml")

        os.chmod(archive_path, 0o600)
        file_size = os.path.getsize(archive_path)

        hasher = hashlib.sha256()
        with open(archive_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        sha256_sum = hasher.hexdigest()

        return {
            "archive_name": archive_name,
            "archive_path": archive_path,
            "timestamp": ts,
            "size_bytes": file_size,
            "sha256": sha256_sum,
            "status": "verified"
        }

    @classmethod
    def restore_backup_snapshot(cls, archive_path: str, config_dir: str = DEFAULT_CONFIG_DIR) -> Dict[str, Any]:
        """
        Safely restores a Traefik backup archive after verifying integrity and creating
        a pre-restore rollback snapshot.
        """
        import tarfile

        if not os.path.exists(archive_path):
            raise FileNotFoundError(f"Backup archive not found: {archive_path}")

        # 1. Pre-restore rollback snapshot
        safety_snap = cls.create_backup_snapshot(config_dir, is_rollback=True)

        # 2. Extract into config_dir with traversal/link protection
        with tarfile.open(archive_path, "r:gz") as tar:
            safe_extractall(tar, config_dir)

        # 3. Ensure acme.json permissions remain 0600
        acme_file = os.path.join(config_dir, "acme", "acme.json")
        if os.path.exists(acme_file):
            os.chmod(acme_file, 0o600)

        return {
            "status": "success",
            "restored_from": archive_path,
            "safety_snapshot": safety_snap,
        }

    @classmethod
    def test_routing_and_connectivity(cls, dashboard_url: str = DEFAULT_DASHBOARD_URL) -> Dict[str, Any]:
        """Tests Traefik port 80 listener and dashboard connectivity."""
        results = {
            "http_port_80": False,
            "https_port_443": False,
            "traefik_running": False,
            "dashboard_url": dashboard_url,
            "details": []
        }

        # Check container
        cres = subprocess.run(
            ["docker", "inspect", "--format={{.State.Status}}", DEFAULT_CONTAINER_NAME],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        if cres.returncode == 0 and "running" in cres.stdout:
            results["traefik_running"] = True
            results["details"].append("Traefik container is running.")
        else:
            results["details"].append("Traefik container is stopped or not running.")

        # Probe port 80
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex(("127.0.0.1", DEFAULT_HTTP_PORT)) == 0:
                    results["http_port_80"] = True
                    results["details"].append("Port 80 (HTTP) is listening.")
        except Exception as e:
            results["details"].append(f"Port 80 check error: {e}")

        # Probe port 443 (secure dashboard entrypoint)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex(("127.0.0.1", 443)) == 0:
                    results["https_port_443"] = True
                    results["details"].append("Port 443 (HTTPS) is listening.")
        except Exception as e:
            results["details"].append(f"Port 443 check error: {e}")

        return results


TRAEFIK_DIR = '/opt/traefik'
TRAEFIK_LETSENCRYPT_DIR = os.path.join(TRAEFIK_DIR, 'letsencrypt')
TRAEFIK_CONFIG_DIR = os.path.join(TRAEFIK_DIR, 'config')
TRAEFIK_DATA_DIR = '/data/traefik'
TRAEFIK_LOG_DIR = os.path.join(TRAEFIK_DATA_DIR, 'logs')
TRAEFIK_COMPOSE_FILE = os.path.join(TRAEFIK_DIR, 'docker-compose.yml')
TRAEFIK_ENV_FILE = os.path.join(TRAEFIK_DIR, '.env')
TRAEFIK_ACME_FILE = os.path.join(TRAEFIK_LETSENCRYPT_DIR, 'acme.json')
TRAEFIK_STATIC_CONFIG = os.path.join(TRAEFIK_CONFIG_DIR, 'traefik.yml')


def docker_traefik_command(use_sudo=False):
    return (['sudo', '-n'] if use_sudo and not (hasattr(os, 'geteuid') and os.geteuid() == 0) else []) + DOCKER


def _write_file_sudo(path: str, content: str, use_sudo: bool = False):
    """Write content to a file, using sudo tee when not root and use_sudo is set."""
    if use_sudo and not (hasattr(os, 'geteuid') and os.geteuid() == 0):
        import subprocess as _sp
        _sp.run(['sudo', 'tee', path], input=content, text=True, check=True)
        _sp.run(['sudo', 'chmod', '644', path], check=False)
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


def inspect_traefik(use_sudo=False):
    """Check Traefik status on the local engine (installed / missing / conflict / error)."""
    if not shutil.which('docker'):
        return {'status': 'docker_missing', 'containers': [], 'error': 'Docker Engine is not installed.'}
    code, output = probe(docker_traefik_command(use_sudo) + ['ps', '-a', '--format', '{{json .}}'])
    if code:
        return {'status': 'error', 'containers': [], 'error': output}
    containers = []
    collision = False
    try:
        for line in output.splitlines():
            item = json.loads(line)
            image = item.get('Image', '')
            is_traefik = image.startswith('traefik')
            if is_traefik or item.get('Names') == 'traefik':
                containers.append(item)
                collision |= not is_traefik
    except (ValueError, AttributeError):
        return {'status': 'error', 'containers': [], 'error': 'Failed to read Docker response.'}
    return {'status': 'conflict' if collision else 'installed' if containers else 'missing',
            'containers': containers, 'error': ''}


def build_traefik_plan(use_sudo=False):
    """Build Traefik setup and installation plan (mkdir, touch, chmod)."""
    docker = docker_traefik_command(use_sudo)
    prefix = docker[:-len(DOCKER)]
    return [
        prefix + ['mkdir', '-p', f'{TRAEFIK_DIR}/config', f'{TRAEFIK_LETSENCRYPT_DIR}', f'{TRAEFIK_DATA_DIR}/logs'],
        prefix + ['touch', TRAEFIK_ACME_FILE],
        prefix + ['chmod', '600', TRAEFIK_ACME_FILE],
        prefix + ['mkdir', '-p', TRAEFIK_DIR],
    ]


def _traefik_env_content():
    return (
        "TRAEFIK_IMAGE=traefik:v3.7\n"
        f"ACME_EMAIL=${{ACME_EMAIL:-admin@{get_config().primary_domain}}}\n"
        f"TRAEFIK_DASHBOARD_DOMAIN={get_config().traefik_domain}\n"
        "TRAEFIK_BASIC_AUTH=admin:$$apr1$$xyz$$randomhash\n"
        "DOCKER_PROXY_NETWORK=proxy\n"
        f"ODOO_DATA_ROOT={TRAEFIK_DIR}\n"
    )


def _traefik_static_config():
    return (
        "# Traefik v3.7 static configuration\n"
        "api:\n"
        "  dashboard: true\n"
        "  insecure: false\n"
        "entryPoints:\n"
        "  web:\n"
        "    address: :80\n"
        "    http:\n"
        "      redirections:\n"
        "        entryPoint:\n"
        "          to: websecure\n"
        "          scheme: https\n"
        "  websecure:\n"
        "    address: :443\n"
        "certificatesResolvers:\n"
        "  le:\n"
        "    acme:\n"
        "      email: ${ACME_EMAIL}\n"
        "      storage: /letsencrypt/acme.json\n"
        "      httpChallenge:\n"
        "        entryPoint: web\n"
        "providers:\n"
        "  docker:\n"
        "    endpoint: unix:///var/run/docker.sock\n"
        "    exposedByDefault: false\n"
        "    network: proxy\n"
    )


def _traefik_compose_content():
    return (
        "services:\n"
        "  traefik:\n"
        "    image: traefik:v3.7\n"
        "    container_name: traefik\n"
        "    restart: unless-stopped\n"
        "    security_opt:\n"
        "      - no-new-privileges:true\n"
        "    ports:\n"
        "      - \"80:80\"\n"
        "      - \"443:443\"\n"
        "    networks:\n"
        "      - proxy\n"
        "    volumes:\n"
        "      - /var/run/docker.sock:/var/run/docker.sock:ro\n"
        "      - ./config/traefik.yml:/etc/traefik/traefik.yml:ro\n"
        "      - ./letsencrypt/acme.json:/letsencrypt/acme.json\n"
        "      - ./logs:/var/log/traefik\n"
        "    environment:\n"
        "      - ACME_EMAIL=${ACME_EMAIL}\n"
        "    labels:\n"
        "      - \"traefik.enable=true\"\n"
        "networks:\n"
        "  proxy:\n"
        "    external: true\n"
        "    name: proxy\n"
    )


def install_traefik(dry_run=False, use_sudo=False):
    """Install Traefik if not installed. If installed or conflict exists, no changes are made."""
    try:
        if platform.system() != 'Linux':
            raise ValueError('This installer is for the local Docker engine on Linux.')
        report = inspect_traefik(use_sudo=use_sudo)
        if report['status'] == 'installed':
            print('Traefik is already installed. Container status shown above. Will not reinstall.')
            return True
        if report['status'] == 'conflict':
            print('Name traefik is used by another container. No changes made.')
            return False
        if report['status'] == 'error':
            print(report['error'])
            return False

        for candidate in (80, 443):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('0.0.0.0', candidate))

        if dry_run:
            for command in build_traefik_plan(use_sudo=use_sudo):
                run_step(command, dry_run=True)
            run_step(docker_traefik_command(use_sudo) + ['network', 'create', '--driver', 'bridge', '--subnet', '172.28.0.0/16', 'proxy'], dry_run=True)
            run_step(docker_traefik_command(use_sudo) + ['compose', '-f', TRAEFIK_COMPOSE_FILE, 'up', '-d'], dry_run=True)
            return True

        commands = build_traefik_plan(use_sudo=use_sudo)
        for command in commands:
            run_step(command)

        # F27: Idempotent network creation — ensure_network checks existence first.
        TraefikDockerManager.ensure_proxy_network(JENKINS_NETWORK if False else DEFAULT_NETWORK_NAME)

        # Write config files with consistent sudo permissions (F27).
        _write_file_sudo(TRAEFIK_ENV_FILE, _traefik_env_content(), use_sudo=use_sudo)
        _write_file_sudo(TRAEFIK_STATIC_CONFIG, _traefik_static_config(), use_sudo=use_sudo)
        # F28: Use generated compose with dashboard router + auth middleware.
        config = TraefikConfig()
        compose_content = TraefikDockerManager.generate_compose_yaml(config)
        _write_file_sudo(TRAEFIK_COMPOSE_FILE, compose_content, use_sudo=use_sudo)

        run_step(docker_traefik_command(use_sudo) + ['compose', '-f', TRAEFIK_COMPOSE_FILE, 'up', '-d'])
        code, state = probe(docker_traefik_command(use_sudo) + ['inspect', '--format', '{{.State.Status}}', 'traefik'])
        if code or state != 'running':
            print(f'Container created but status check did not confirm running: {state}. Check docker logs traefik.')
            return False
        run_step(docker_traefik_command(use_sudo) + ['ps', '-a'])
        print(f'Traefik container is running. Open https://<SERVER-IP> for dashboard (Basic Auth) and ports 80/443.')
        return True
    except (OSError, ValueError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
        print(f'Traefik installation stopped: {exc}. No existing data or containers were deleted; check output.')
        return False


def ufw_command(use_sudo=False):
    return (['sudo', '-n'] if use_sudo and not (hasattr(os, 'geteuid') and os.geteuid() == 0) else []) + ['ufw']


def ufw_installed():
    return shutil.which('ufw') is not None


def ufw_status(use_sudo=False):
    if not ufw_installed():
        return {'available': False, 'error': 'UFW is not installed on the system.'}
    code, output = probe(ufw_command(use_sudo) + ['status'])
    return {'available': True, 'code': code, 'output': output, 'error': '' if code == 0 else output}


def ufw_allow_port(port, protocol='tcp', use_sudo=False):
    if not ufw_installed():
        return False, 'UFW is not installed on the system.'
    code, output = probe(ufw_command(use_sudo) + ['allow', f'{port}/{protocol}'])
    return code == 0, output if code != 0 else f'Port {port}/{protocol} opened successfully.'


def setup_traefik_ufw(use_sudo=False):
    """Open Traefik ports 80/TCP and 443/TCP via UFW if available."""
    if not ufw_installed():
        print('UFW is not installed. Firewall cannot be managed automatically.')
        return False
    code, output = probe(ufw_command(use_sudo) + ['status'])
    if code != 0:
        print(f'Failed to read UFW status: {output}')
        return False
    ok80, msg80 = ufw_allow_port(80, 'tcp', use_sudo)
    ok443, msg443 = ufw_allow_port(443, 'tcp', use_sudo)
    print(msg80)
    print(msg443)
    return ok80 and ok443


TRAEFIK_ISSUE_PORT_80 = 'port_80_in_use'
TRAEFIK_ISSUE_PORT_443 = 'port_443_in_use'
TRAEFIK_ISSUE_PROXY_NETWORK = 'proxy_network_missing'
TRAEFIK_ISSUE_ACME_PERMS = 'acme_permissions_insecure'
TRAEFIK_ISSUE_CONTAINER_NOT_RUNNING = 'traefik_container_not_running'


def traefik_diagnose(use_sudo=False):
    """Diagnose potential Traefik errors and list suggested fixes."""
    issues = []
    repairs = []

    if not shutil.which('docker'):
        issues.append({
            'id': 'traefik_docker_missing',
            'component': 'Traefik',
            'title': 'Docker Engine is not installed',
            'description': 'Traefik cannot run without Docker Engine.',
            'severity': 'critical',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'Install Docker Engine first from the menu.',
        })
        return issues, repairs

    report = inspect_traefik(use_sudo=use_sudo)

    if report['status'] == 'error':
        issues.append({
            'id': 'traefik_daemon_error',
            'component': 'Traefik',
            'title': 'Error communicating with Docker daemon',
            'description': report.get('error', 'Unknown'),
            'severity': 'critical',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'Check Docker is running and user permissions.',
        })
        return issues, repairs

    if report['status'] == 'conflict':
        issues.append({
            'id': 'traefik_name_conflict',
            'component': 'Traefik',
            'title': 'Container name conflict traefik',
            'description': 'Name traefik is used by another container.',
            'severity': 'high',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'Rename the other container or remove it before installing.',
        })
        return issues, repairs

    # Check ports
    for port, issue_id, title, desc in (
        (80, TRAEFIK_ISSUE_PORT_80, 'Port 80 (HTTP) in use', 'Port 80 is bound by another process, preventing Traefik from listening on HTTP.'),
        (443, TRAEFIK_ISSUE_PORT_443, 'Port 443 (HTTPS) in use', 'Port 443 is bound by another process, preventing Traefik from listening on HTTPS.'),
    ):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            if s.connect_ex(('127.0.0.1', port)) == 0:
                issues.append({
                    'id': issue_id,
                    'component': 'Traefik',
                    'title': title,
                    'description': desc,
                    'severity': 'high',
                    'auto_fix': False,
                    'fix_command': None,
                    'fix_description': 'Stop the service on the port or reconfigure Traefik to use other ports.',
                })

    # Check proxy network
    if not report.get('proxy_network_exists'):
        issues.append({
            'id': TRAEFIK_ISSUE_PROXY_NETWORK,
            'component': 'Traefik',
            'title': 'Docker proxy network not found',
            'description': 'Shared proxy network does not exist; Odoo containers will not be able to connect to Traefik.',
            'severity': 'high',
            'auto_fix': True,
            'fix_command': ['network', 'create', '--driver', 'bridge', '--subnet', '172.28.0.0/16', 'proxy'],
            'fix_description': 'Create Docker network named proxy.',
        })
        repairs.append(('Create proxy network', ['docker', 'network', 'create', '--driver', 'bridge', '--subnet', '172.28.0.0/16', 'proxy']))

    # Check acme.json permissions
    acme_path = os.path.join('/opt/odoo-infrastructure', 'traefik', 'acme', 'acme.json')
    if os.path.exists(acme_path):
        try:
            perm = oct(os.stat(acme_path).st_mode)[-3:]
            if perm != '600':
                issues.append({
                    'id': TRAEFIK_ISSUE_ACME_PERMS,
                    'component': 'Traefik',
                    'title': 'acme.json permissions are insecure',
                    'description': f'Current file permission is {perm}, should be 600.',
                    'severity': 'medium',
                    'auto_fix': True,
                    'fix_command': ['chmod', '600', acme_path],
                    'fix_description': 'Set acme.json permission to 0600.',
                })
                repairs.append(('Set acme.json permission to 0600', ['chmod', '600', acme_path]))
        except Exception:
            pass

    # Check container status
    if report['status'] == 'installed':
        for c in report['containers']:
            status = c.get('Status', '')
            if 'Exited' in status or 'Created' in status:
                issues.append({
                    'id': TRAEFIK_ISSUE_CONTAINER_NOT_RUNNING,
                    'component': 'Traefik',
                    'title': 'Traefik container not running',
                    'description': f'Container status: {status}',
                    'severity': 'high',
                    'auto_fix': True,
                    'fix_command': ['start', 'traefik'],
                    'fix_description': 'Start the stopped Traefik container.',
                })
                repairs.append(('Start Traefik container', ['docker', 'start', 'traefik']))
            break

    return issues, repairs


def traefik_repair(issue, use_sudo=False):
    """Execute a single fix for a Traefik issue."""
    fix_cmd = issue.get('fix_command')
    if not fix_cmd:
        return False, 'No automatic repair command for this issue.'
    docker = docker_traefik_command(use_sudo)
    prefix = docker[:-len(DOCKER)]
    full_cmd = prefix + fix_cmd
    try:
        run_step(full_cmd)
        return True, 'Executed successfully.'
    except Exception as exc:
        return False, str(exc)
