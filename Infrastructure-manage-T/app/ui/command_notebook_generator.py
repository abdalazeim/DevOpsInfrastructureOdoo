"""
Dynamic Odoo Docker Installation Command Generator for the Command Notebook.

Pure data/config generation only:
- NO subprocess, shell execution, Ansible, Docker SDK, or Jenkins calls.
- Reads project/profile configuration only through explicit, read-only inputs.
- Produces editable command records and optional Docker Compose text.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

ODOO_PG_DEFAULTS = {"17": "16", "18": "17", "19": "18"}
ODOO_HTTP_DEFAULTS = {"17": 10017, "18": 10018, "19": 10019}
ODOO_LP_DEFAULTS = {"17": 20017, "18": 20018, "19": 20019}
SUPPORTED_RESTART_POLICIES = ("no", "on-failure", "on-failure:5", "always", "unless-stopped")
SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,62}$")


@dataclass
class OdooGeneratorConfig:
    """User-selected configuration for generating Odoo Docker commands."""

    odoo_version: str = "19"
    odoo_image: str = ""
    postgres_image: str = ""
    http_host_port: int = 0
    http_internal_port: int = 8069
    longpolling_host_port: int = 0
    longpolling_internal_port: int = 8072
    deployment_dir: str = "/opt/odoo/odoo19"
    compose_project_name: str = "odoo19-one"
    odoo_container_name: str = ""
    db_container_name: str = ""
    docker_network: str = "proxy"
    restart_policy: str = "unless-stopped"
    addons_dir: str = "addons"
    config_dir: str = "etc"
    postgres_data_dir: str = "postgresql"
    deployment_mode: str = "local"  # local | domain
    domain: str = ""

    def normalized(self) -> "OdooGeneratorConfig":
        v = str(self.odoo_version)
        http = int(self.http_host_port or ODOO_HTTP_DEFAULTS.get(v, 10019))
        lp = int(self.longpolling_host_port or ODOO_LP_DEFAULTS.get(v, 20019))
        pg = ODOO_PG_DEFAULTS.get(v, "18")
        odoo_image = (self.odoo_image or f"odoo:{v}").strip()
        postgres_image = (self.postgres_image or f"postgres:{pg}").strip()
        project = (self.compose_project_name or f"odoo{v}-one").strip()
        deploy_dir = (self.deployment_dir or f"/opt/odoo/odoo{v}").strip()
        odoo_container = (self.odoo_container_name or f"{project}-odoo").strip()
        db_container = (self.db_container_name or f"{project}-db").strip()
        return OdooGeneratorConfig(
            odoo_version=v,
            odoo_image=odoo_image,
            postgres_image=postgres_image,
            http_host_port=http,
            http_internal_port=int(self.http_internal_port or 8069),
            longpolling_host_port=lp,
            longpolling_internal_port=int(self.longpolling_internal_port or 8072),
            deployment_dir=deploy_dir,
            compose_project_name=project,
            odoo_container_name=odoo_container,
            db_container_name=db_container,
            docker_network=(self.docker_network or "proxy").strip(),
            restart_policy=(self.restart_policy or "unless-stopped").strip(),
            addons_dir=(self.addons_dir or "addons").strip(),
            config_dir=(self.config_dir or "etc").strip(),
            postgres_data_dir=(self.postgres_data_dir or "postgresql").strip(),
            deployment_mode=(self.deployment_mode or "local").strip().lower(),
            domain=(self.domain or "").strip(),
        )

    def to_metadata(self) -> Dict[str, Any]:
        return asdict(self.normalized())

    @staticmethod
    def from_profile(profile: Any, odoo_version: Optional[str] = None) -> "OdooGeneratorConfig":
        """Build config from a read-only profile-like object (duck-typed)."""
        v = str(odoo_version or "19")
        cfg = OdooGeneratorConfig(odoo_version=v)
        if profile is None:
            return cfg.normalized()
        try:
            inst = getattr(profile, f"odoo{v}", None)
            if inst:
                cfg.odoo_image = getattr(inst, "image", cfg.odoo_image) or cfg.odoo_image
                db = getattr(inst, "database", None)
                if db and getattr(db, "engine", None):
                    cfg.postgres_image = db.engine
                domain = getattr(inst, "domain", "") or ""
                if domain and "localhost" not in domain:
                    cfg.deployment_mode = "domain"
                    cfg.domain = domain
            paths = getattr(profile, "paths", None)
            if paths and getattr(paths, "data_root", None):
                cfg.deployment_dir = f"{paths.data_root}/odoo{v}"
            net = getattr(profile, "network", None)
            if net and getattr(net, "proxy_network_name", None):
                cfg.docker_network = net.proxy_network_name
        except Exception:
            pass
        return cfg.normalized()


def validate_config(
    config: OdooGeneratorConfig,
    used_host_ports: Optional[Dict[int, str]] = None,
) -> Tuple[bool, List[str], List[str]]:
    """Validate config. Returns (ok, errors, warnings). Never touches the network."""
    cfg = config.normalized()
    errors: List[str] = []
    warnings: List[str] = []
    used_host_ports = used_host_ports or {}

    if cfg.odoo_version not in ODOO_PG_DEFAULTS:
        errors.append(f"Unsupported Odoo version: {cfg.odoo_version} (supported: 17, 18, 19)")

    def _port(label: str, value: int) -> None:
        if not (1 <= int(value) <= 65535):
            errors.append(f"{label} must be between 1 and 65535 (got {value})")

    _port("HTTP host port", cfg.http_host_port)
    _port("Longpolling host port", cfg.longpolling_host_port)
    _port("HTTP internal port", cfg.http_internal_port)
    _port("Longpolling internal port", cfg.longpolling_internal_port)

    if cfg.http_host_port == cfg.longpolling_host_port:
        errors.append("HTTP host port and longpolling host port must be different")
    if cfg.http_internal_port != 8069:
        warnings.append("Odoo internal HTTP port is usually 8069; custom values require matching Odoo config")
    if cfg.longpolling_internal_port != 8072:
        warnings.append("Odoo longpolling internal port is usually 8072; custom values require matching config/proxy")

    expected_pg = ODOO_PG_DEFAULTS.get(cfg.odoo_version)
    if expected_pg and f"postgres:{expected_pg}" not in cfg.postgres_image and expected_pg not in cfg.postgres_image:
        warnings.append(
            f"PostgreSQL image '{cfg.postgres_image}' differs from the common default for Odoo {cfg.odoo_version} (postgres:{expected_pg}). Verify compatibility."
        )

    if cfg.restart_policy not in SUPPORTED_RESTART_POLICIES:
        errors.append(f"Unsupported restart policy: {cfg.restart_policy}")

    for label, value in (
        ("Compose project name", cfg.compose_project_name),
        ("Odoo container name", cfg.odoo_container_name),
        ("DB container name", cfg.db_container_name),
        ("Docker network", cfg.docker_network),
    ):
        if not SAFE_NAME_RE.match(value):
            errors.append(f"{label} contains unsafe characters: '{value}'")

    if not cfg.deployment_dir or cfg.deployment_dir.strip() in ("/", ""):
        errors.append("Deployment directory must be an explicit non-root path")
    if ".." in cfg.deployment_dir.replace("\\", "/"):
        errors.append("Deployment directory must not contain '..'")

    for rel in (cfg.addons_dir, cfg.config_dir, cfg.postgres_data_dir):
        if rel.startswith("/") or rel.startswith("\\") or ".." in rel:
            errors.append(f"Directory must be project-relative and safe: '{rel}'")

    if cfg.deployment_mode == "domain" and not cfg.domain:
        warnings.append("Domain mode selected but no domain provided; generated routing remains local/manual")

    for p in (cfg.http_host_port, cfg.longpolling_host_port):
        if p in used_host_ports:
            errors.append(f"Host port {p} is already assigned in configuration ({used_host_ports[p]})")

    # Static availability hint (no socket bind). Real availability must be checked on target host.
    warnings.append("Port availability cannot be guaranteed from this notebook; verify on the target host before deployment.")

    return (len(errors) == 0, errors, warnings)


def _cmd(
    name: str,
    command: str,
    description: str,
    risk: str,
    group: str,
    number: int,
    cfg: OdooGeneratorConfig,
) -> Dict[str, Any]:
    return {
        "name": name,
        "title": name,
        "command": command.rstrip(),
        "description": description,
        "risk_level": risk,
        "risk_classification": risk,
        "group": group,
        "group_number": number,
        "odoo_version": cfg.odoo_version,
        "required_parameters": [f"ODOO_VERSION={cfg.odoo_version}", f"HTTP_PORT={cfg.http_host_port}"],
        "source": "generated",
        "generator": "odoo_docker_installation",
        "generated_config": cfg.to_metadata(),
    }


def generate_odoo_commands(config: OdooGeneratorConfig) -> Tuple[bool, List[Dict[str, Any]], List[str], List[str], str]:
    """Generate grouped Odoo Docker commands for a validated config."""
    cfg = config.normalized()
    ok, errors, warnings = validate_config(cfg)
    if not ok:
        return False, [], errors, warnings, ""
    d = cfg.deployment_dir
    v = cfg.odoo_version
    cmds: List[Dict[str, Any]] = []
    n = 0

    def add(*args: Any) -> None:
        nonlocal n
        n += 1
        cmds.append(_cmd(args[0], args[1], args[2], args[3], args[4], n, cfg))

    # Group 01
    add("01.01 Update package lists", "sudo apt-get update",
        "Refresh package indexes on Ubuntu. Review output before upgrading.", "MODERATE", "System Preparation")
    add("01.02 Install required dependencies", "sudo apt-get install -y curl ca-certificates gnupg lsb-release",
        "Install common prerequisites used by Docker and deployment scripts.", "MODERATE", "System Preparation")
    add("01.03 Verify Docker Engine", "docker --version\ndocker info --format '{{.ServerVersion}}'",
        "Check Docker CLI and daemon availability (read-only).", "SAFE", "System Preparation")
    add("01.04 Verify Docker Compose V2", "docker compose version",
        "Verify Docker Compose V2 plugin. Use docker-compose V1 only when the target environment requires it.", "SAFE", "System Preparation")
    add("01.05 Verify available disk space", "df -h /\ndf -h .",
        "Check disk space before creating persistent volumes and images.", "SAFE", "System Preparation")
    add("01.06 Verify Docker service status", "systemctl is-active docker || true\nsystemctl status docker --no-pager -l | head -n 40 || true",
        "Inspect Docker service state on systemd hosts (read-only).", "SAFE", "System Preparation")

    # Group 02
    add("02.01 Create deployment directory",
        f"sudo mkdir -p '{d}'\nsudo chown \"$(id -u):$(id -g)\" '{d}'\ncd '{d}'",
        "Create the deployment directory and set ownership to the deploying user. Do not use chmod 777.", "MODERATE", "Project Preparation")
    add("02.02 Create required folders",
        f"cd '{d}'\nmkdir -p '{cfg.addons_dir}' '{cfg.config_dir}' '{cfg.postgres_data_dir}'\nls -la",
        "Create addons/config/postgresql directories with least-privilege defaults.", "MODERATE", "Project Preparation")
    add("02.03 Verify folder ownership and permissions",
        f"cd '{d}'\nstat -c '%n %U:%G %a' '{cfg.addons_dir}' '{cfg.config_dir}' '{cfg.postgres_data_dir}'",
        "Verify ownership/mode. Adjust only if required by the container user and host policy.", "SAFE", "Project Preparation")
    add("02.04 Prepare Odoo configuration file",
        f"cd '{d}'\ncat > '{cfg.config_dir}/odoo.conf' <<'EOF'\n[options]\naddons_path = /mnt/extra-addons\n; admin_passwd is intentionally omitted.\n; Store master password in protected credential storage and inject securely.\n; db_host, db_port, db_user, db_password are provided by container environment.\nlogfile = /var/log/odoo/odoo-server.log\nEOF\nls -la '{cfg.config_dir}/odoo.conf'",
        "Create a minimal odoo.conf without hardcoded admin password. Use secure credential storage for secrets.", "MODERATE", "Project Preparation")

    # Group 03 - external script (review-first, not assumed)
    add("03.01 Review external deployment script (optional/reference)",
        "# External script reference from request (DO NOT assume it exists or is safe):\n"
        "# compose/master/run.sh | bash -s odoo-one 10017 20017\n\n"
        "# Required before using any external script:\n"
        "# 1. Verify repository/script source and integrity.\n"
        "# 2. Download and review it locally before execution.\n"
        "# 3. Confirm it supports: project name, HTTP host port, longpolling host port.\n"
        "# 4. Prefer the generated Docker Compose project in Group 04 as the primary path.\n"
        "curl -fsSLo ./run.sh '<VERIFIED_SCRIPT_URL>'\nless ./run.sh\n# After review only:\n# bash ./run.sh " + f"'{cfg.compose_project_name}' {cfg.http_host_port} {cfg.longpolling_host_port}",
        "Reference only. External scripts must be verified, downloaded, and reviewed before execution. Prefer generated Compose.", "HIGH", "Odoo Docker Deployment")

    # Group 04
    compose_file = f"{d}/docker-compose.odoo{v}.yml"
    add("04.01 Validate Docker Compose config",
        f"cd '{d}'\ndocker compose -f '{compose_file}' -p '{cfg.compose_project_name}' config",
        "Validate generated Compose before starting services (read-only).", "SAFE", "Docker Compose Commands")
    add("04.02 Start Odoo stack",
        f"cd '{d}'\ndocker compose -f '{compose_file}' -p '{cfg.compose_project_name}' up -d",
        "Start PostgreSQL and Odoo in detached mode.", "HIGH", "Docker Compose Commands")
    add("04.03 Show Compose services",
        f"cd '{d}'\ndocker compose -f '{compose_file}' -p '{cfg.compose_project_name}' ps",
        "Show container state for the project (read-only).", "SAFE", "Docker Compose Commands")
    add("04.04 Tail Compose logs",
        f"cd '{d}'\ndocker compose -f '{compose_file}' -p '{cfg.compose_project_name}' logs --tail 100",
        "Inspect recent logs for Odoo/PostgreSQL (read-only).", "SAFE", "Docker Compose Commands")
    add("04.05 Restart Compose services",
        f"cd '{d}'\ndocker compose -f '{compose_file}' -p '{cfg.compose_project_name}' restart",
        "Restart services. Affects availability.", "HIGH", "Docker Compose Commands")
    add("04.06 Stop Compose services (keeps containers/volumes defined)",
        f"cd '{d}'\ndocker compose -f '{compose_file}' -p '{cfg.compose_project_name}' stop",
        "Stop containers without removing them. Safer than down for routine maintenance.", "HIGH", "Docker Compose Commands")

    # Group 05
    add("05.01 Port mapping reference",
        f"# Docker Compose port mapping (host:container)\nports:\n  - \"{cfg.http_host_port}:{cfg.http_internal_port}\"   # Odoo HTTP\n  - \"{cfg.longpolling_host_port}:{cfg.longpolling_internal_port}\"   # Odoo longpolling/gevent\n\n# Verify host ports before use:\nss -tuln | grep -E ':{cfg.http_host_port}|:{cfg.longpolling_host_port}' || echo 'Selected host ports appear free (static check)'",
        "Host ports come from the selected configuration. Do not reuse the same host port for multiple instances.", "SAFE", "Docker Port Configuration")

    # Group 06
    add("06.01 Restart policy reference",
        "restart: unless-stopped  # default\n\n"
        "# Supported policies:\n"
        "# no            - never restart automatically\n"
        "# on-failure    - restart only on non-zero exit\n"
        "# on-failure:5  - restart on failure, max 5 attempts\n"
        "# always        - always restart (including after daemon restart/manual stop behavior varies)\n"
        "# unless-stopped - restart unless explicitly stopped (recommended default)",
        "Restart policy is applied in generated Compose. Default is unless-stopped.", "SAFE", "Restart Policy")

    # Group 07
    add("07.01 Check inotify watches (optional)",
        "cat /proc/sys/fs/inotify/max_user_watches\nsysctl fs.inotify.max_user_watches 2>/dev/null || true",
        "Read current inotify watch limit (read-only). Useful when running many Odoo/dev instances.", "SAFE", "Linux System Configuration")
    add("07.02 Increase inotify watches with backup (optional, host-level)",
        "# OPTIONAL and host-level. Requires explicit confirmation before applying.\n"
        "sudo cp /etc/sysctl.conf /etc/sysctl.conf.bak.$(date +%Y%m%d%H%M%S)\n"
        "if grep -qF \"fs.inotify.max_user_watches\" /etc/sysctl.conf; then\n"
        "  echo \"inotify configuration already exists; review before changing\"\n"
        "else\n"
        "  echo \"fs.inotify.max_user_watches = 524288\" | sudo tee -a /etc/sysctl.conf\n"
        "fi\n"
        "sudo sysctl -p",
        "Optional host kernel parameter change. Backs up sysctl.conf, avoids duplicates, and requires confirmation. Not an Odoo app setting.", "MODERATE", "Linux System Configuration")

    # Group 08
    add("08.01 Odoo configuration and data paths reference",
        f"cd '{d}'\n# Files/directories:\n# {cfg.config_dir}/odoo.conf        - Odoo server options (no hardcoded admin password)\n"
        f"# {cfg.config_dir}/odoo-server.log   - log file path if configured/mounted\n"
        f"# {cfg.addons_dir}/                 - custom addons mount\n"
        f"# {cfg.postgres_data_dir}/          - PostgreSQL persistent data (protect/back up carefully)\n"
        f"find '{cfg.config_dir}' '{cfg.addons_dir}' '{cfg.postgres_data_dir}' -maxdepth 2 -ls",
        "Review configuration and persistent paths. Never place plaintext production passwords in generated command text.", "SAFE", "Odoo Configuration")

    # Group 09
    add("09.01 Start Odoo stack",
        f"cd '{d}'\ndocker compose -f '{compose_file}' -p '{cfg.compose_project_name}' up -d",
        "Start services.", "HIGH", "Odoo Container Management")
    add("09.02 Restart Odoo stack",
        f"cd '{d}'\ndocker compose -f '{compose_file}' -p '{cfg.compose_project_name}' restart",
        "Restart services; causes brief downtime.", "HIGH", "Odoo Container Management")
    add("09.03 Stop Odoo stack",
        f"cd '{d}'\ndocker compose -f '{compose_file}' -p '{cfg.compose_project_name}' stop",
        "Stop containers but keep them/volumes. Use when you want a reversible stop.", "HIGH", "Odoo Container Management")
    add("09.04 Remove containers (preserves named/bound data unless volumes removed)",
        f"cd '{d}'\ndocker compose -f '{compose_file}' -p '{cfg.compose_project_name}' down\n# NEVER use as default: docker compose down -v  (can delete persistent volumes/database data)",
        "down removes containers/network for the project. It does NOT imply data backup. Never use -v by default.", "DESTRUCTIVE", "Odoo Container Management")

    # Group 10
    add("10.01 Verify Compose status",
        f"cd '{d}'\ndocker compose -f '{compose_file}' -p '{cfg.compose_project_name}' ps",
        "Container state is necessary but not sufficient for application readiness.", "SAFE", "Odoo Verification")
    add("10.02 Verify logs",
        f"cd '{d}'\ndocker compose -f '{compose_file}' -p '{cfg.compose_project_name}' logs --tail 100 --no-color",
        "Inspect Odoo/PostgreSQL startup and runtime errors.", "SAFE", "Odoo Verification")
    add("10.03 Inspect containers",
        f"docker inspect '{cfg.odoo_container_name}' --format '{{{{.Name}}}} {{{{.State.Status}}}} {{{{.RestartCount}}}}'\n"
        f"docker inspect '{cfg.db_container_name}' --format '{{{{.Name}}}} {{{{.State.Status}}}} {{{{.RestartCount}}}}'",
        "Inspect runtime status and restart count (read-only).", "SAFE", "Odoo Verification")
    add("10.04 Verify PostgreSQL readiness",
        f"docker exec '{cfg.db_container_name}' pg_isready -U \"${{POSTGRES_USER:-odoo}}\" -d \"${{POSTGRES_DB:-postgres}}\" || echo 'Check DB readiness and credentials'",
        "Checks PostgreSQL readiness inside the DB container. Uses env vars; no hardcoded secrets.", "SAFE", "Odoo Verification")
    add("10.05 Verify HTTP response (localhost/local port)",
        f"curl -I --max-time 10 'http://localhost:{cfg.http_host_port}/' || true\n"
        f"curl -fsS --max-time 10 'http://localhost:{cfg.http_host_port}/web/login' -o /dev/null -w 'HTTP %{{http_code}}\\n' || true",
        "HTTP check uses the configured host port. A container running state alone does not prove Odoo is ready.", "SAFE", "Odoo Verification")
    add("10.06 Verify persistent mounts",
        f"docker inspect '{cfg.odoo_container_name}' --format '{{{{json .Mounts}}}}'\n"
        f"docker inspect '{cfg.db_container_name}' --format '{{{{json .Mounts}}}}'",
        "Confirm addons/config/filestore/data mounts are present (read-only).", "SAFE", "Odoo Verification")

    if cfg.deployment_mode == "domain":
        add("10.07 Traefik routing note (domain mode, no Nginx)",
            f"# This project uses Traefik (not Nginx). Configure routing only when required.\n"
            f"# Domain: {cfg.domain or '<set-domain>'}\n"
            f"# Odoo service internal port: {cfg.http_internal_port}\n"
            f"# Longpolling/gevent: {cfg.longpolling_internal_port} (route /websocket or longpolling paths per your Traefik/Odoo setup)\n"
            f"# Validate DNS/TLS and Traefik labels/file provider before enabling production routing.",
            "Domain mode guidance only. Traefik config is generated separately by the infrastructure stack when applicable.", "SAFE", "Odoo Verification")

    compose_text = generate_compose_yaml(cfg)
    return True, cmds, errors, warnings, compose_text


def generate_compose_yaml(config: OdooGeneratorConfig) -> str:
    """Generate a Docker Compose YAML text for the selected Odoo config (no file writes)."""
    cfg = config.normalized()
    pg_major = ODOO_PG_DEFAULTS.get(cfg.odoo_version, "18")
    pg_data = f"/var/lib/postgresql/{pg_major}/docker" if cfg.odoo_version == "19" else "/var/lib/postgresql/data"
    # Use env placeholders; never embed real secrets.
    return f"""# Generated Odoo Docker Compose (reference)
# Project: {cfg.compose_project_name}
# Odoo: {cfg.odoo_image} | PostgreSQL: {cfg.postgres_image}
# Save path suggestion: {cfg.deployment_dir}/docker-compose.odoo{cfg.odoo_version}.yml
# Validate before start: docker compose -f docker-compose.odoo{cfg.odoo_version}.yml -p {cfg.compose_project_name} config

name: {cfg.compose_project_name}

services:
  db:
    image: {cfg.postgres_image}
    container_name: {cfg.db_container_name}
    restart: {cfg.restart_policy}
    environment:
      POSTGRES_DB: ${{POSTGRES_DB:-postgres}}
      POSTGRES_USER: ${{POSTGRES_USER:-odoo}}
      POSTGRES_PASSWORD: ${{POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in a protected .env or secret store}}
    volumes:
      - ./{cfg.postgres_data_dir}:{pg_data}
    networks:
      - odoo_internal
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${{POSTGRES_USER:-odoo}} -d $${{POSTGRES_DB:-postgres}}"]
      interval: 10s
      timeout: 5s
      retries: 10

  odoo:
    image: {cfg.odoo_image}
    container_name: {cfg.odoo_container_name}
    restart: {cfg.restart_policy}
    depends_on:
      db:
        condition: service_healthy
    environment:
      HOST: db
      PORT: "5432"
      USER: ${{POSTGRES_USER:-odoo}}
      PASSWORD: ${{POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in a protected .env or secret store}}
    ports:
      - "{cfg.http_host_port}:{cfg.http_internal_port}"
      - "{cfg.longpolling_host_port}:{cfg.longpolling_internal_port}"
    volumes:
      - ./{cfg.addons_dir}:/mnt/extra-addons
      - ./{cfg.config_dir}:/etc/odoo
      - odoo_filestore:/var/lib/odoo
    networks:
      - odoo_internal
      - {cfg.docker_network}
    healthcheck:
      test: ["CMD-SHELL", "curl -fsS http://127.0.0.1:{cfg.http_internal_port}/web/login >/dev/null || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 10
      start_period: 60s

networks:
  odoo_internal:
    driver: bridge
  {cfg.docker_network}:
    external: true
    name: {cfg.docker_network}

volumes:
  odoo_filestore:
"""


def diff_text(old: str, new: str, fromfile: str = "saved", tofile: str = "generated") -> str:
    old_lines = (old or "").splitlines(keepends=True)
    new_lines = (new or "").splitlines(keepends=True)
    return "".join(difflib.unified_diff(old_lines, new_lines, fromfile=fromfile, tofile=tofile))


def config_signature(config: OdooGeneratorConfig) -> str:
    payload = json.dumps(config.to_metadata(), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
