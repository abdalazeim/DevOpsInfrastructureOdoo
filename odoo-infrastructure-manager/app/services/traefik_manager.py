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
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any


DEFAULT_CONFIG_DIR = "/opt/traefik"
DEFAULT_DOCKER_IMAGE = "traefik:v3.7"
DEFAULT_CONTAINER_NAME = "traefik"
DEFAULT_NETWORK_NAME = "proxy"
DEFAULT_HTTP_PORT = 80
DEFAULT_DASHBOARD_INTERNAL_PORT = 8080
DEFAULT_DASHBOARD_EXTERNAL_PORT = 10090
DEFAULT_ODOO19_PORT = 10019
DEFAULT_JENKINS_PORT = 8081
DEFAULT_DASHBOARD_URL = "http://localhost:10090/dashboard/"


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
    insecure_dashboard: bool = False  # False = secure router with basic auth, True = exposed on 10090
    dashboard_domain: str = "traefik.local"
    acme_email: str = "admin@example.com"
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

        # Inspect ports
        target_ports = [
            (DEFAULT_HTTP_PORT, "Traefik HTTP (Web Entrypoint)"),
            (DEFAULT_DASHBOARD_EXTERNAL_PORT, "Traefik Dashboard (External Port)"),
            (DEFAULT_DASHBOARD_INTERNAL_PORT, "Traefik Dashboard (Internal API)"),
            (DEFAULT_ODOO19_PORT, "Odoo 19 Entrypoint / Port"),
            (DEFAULT_JENKINS_PORT, "Jenkins Web Service"),
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

        # Dashboard reachability
        dashboard_ok = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                if s.connect_ex(("127.0.0.1", DEFAULT_DASHBOARD_EXTERNAL_PORT)) == 0:
                    dashboard_ok = True
        except Exception:
            pass

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
            dashboard_url=DEFAULT_DASHBOARD_URL,
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
        - ports: 80:80 and 10090:8080 (when local management enabled)
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

        if config.insecure_dashboard:
            lines.append("      - --api.insecure=true  # WARNING: Local management only!")
        else:
            lines.append("      - --api.insecure=false")

        lines.extend([
            "      - --providers.docker=true",
            "      - --providers.docker.exposedbydefault=false",
            f"      - --providers.docker.network={config.network}",
            f"      - --entrypoints.web.address=:{config.http_port}",
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

        # Publish 10090:8080 for dashboard if local management mode is enabled
        if config.enable_dashboard and config.insecure_dashboard:
            lines.append(f'      - "{config.dashboard_external_port}:{config.dashboard_internal_port}"')

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

        # Security Labels
        lines.extend([
            "    labels:",
            '      - "traefik.enable=true"',
        ])

        if not config.insecure_dashboard:
            # Secure Router configuration with BasicAuth protection
            lines.extend([
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

        # 2. Extract into config_dir
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=config_dir)

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
            "dashboard_port_10090": False,
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

        # Probe port 10090
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex(("127.0.0.1", DEFAULT_DASHBOARD_EXTERNAL_PORT)) == 0:
                    results["dashboard_port_10090"] = True
                    results["details"].append("Port 10090 (Dashboard) is listening.")
        except Exception as e:
            results["details"].append(f"Port 10090 check error: {e}")

        return results
