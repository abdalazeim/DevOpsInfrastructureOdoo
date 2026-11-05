"""Jenkins CI/CD discovery and installation on the local Linux Docker Engine."""
import json
import os
import platform
import shutil
import socket
import subprocess

from app.config.hostname_config import get_config
from app.services.runtime_inspector import probe
from app.services.docker_installer import run_step

DOCKER = ['docker', '--host', 'unix:///var/run/docker.sock']
IMAGE = 'jenkins/jenkins:lts-jdk21'
JENKINS_HOST_DATA_DIR = '/data/jenkins'
JENKINS_HOST_CONFIG_DIR = '/opt/jenkins'
JENKINS_CONTAINER = 'jenkins'
JENKINS_HTTP_PORT = 8080
JENKINS_AGENT_PORT = 50000
JENKINS_NETWORK = 'proxy'
JENKINS_TIMEZONE = 'UTC'
JENKINS_CERTSRESOLVER = 'letsencrypt'


def get_jenkins_domain() -> str:
    """Get Jenkins domain from centralized hostname config."""
    try:
        return get_config().jenkins_domain
    except RuntimeError:
        return 'jenkins.localhost'


def docker_command(use_sudo=False):
    return (['sudo', '-n'] if use_sudo and not (hasattr(os, 'geteuid') and os.geteuid() == 0) else []) + DOCKER


def inspect_jenkins(use_sudo=False):
    """Check Jenkins status on the local engine (installed / missing / conflict / error)."""
    if not shutil.which('docker'):
        return {'status': 'docker_missing', 'containers': [], 'error': 'Docker Engine is not installed.'}
    code, output = probe(docker_command(use_sudo) + ['ps', '-a', '--format', '{{json .}}'])
    if code:
        return {'status': 'error', 'containers': [], 'error': output}
    containers = []
    collision = False
    try:
        for line in output.splitlines():
            item = json.loads(line)
            image = item.get('Image', '')
            is_jenkins = image.startswith('jenkins/')
            if is_jenkins or item.get('Names') == JENKINS_CONTAINER:
                containers.append(item)
                collision |= not is_jenkins
    except (ValueError, AttributeError):
        return {'status': 'error', 'containers': [], 'error': 'Failed to read Docker response.'}
    return {'status': 'conflict' if collision else 'installed' if containers else 'missing',
            'containers': containers, 'error': ''}


def system_preflight_check():
    """Pre-installation system check (OS, Docker, network, storage, memory)."""
    results = {}
    try:
        res = subprocess.run(['lsb_release', '-a'], capture_output=True, text=True, check=False)
        results['os'] = res.stdout.strip() or res.stderr.strip()
    except FileNotFoundError:
        results['os'] = 'lsb_release not available'
    for cmd in (['docker', '--version'], ['docker', 'compose', 'version']):
        code, out = probe(cmd)
        results[cmd[0]] = out if code == 0 else f'Error: {out}'
    code, out = probe(['docker', 'ps'])
    results['docker_ps'] = out if code == 0 else f'Error: {out}'
    code, out = probe(['docker', 'network', 'ls'])
    results['network_ls'] = out if code == 0 else f'Error: {out}'
    for path in ('/opt', '/data'):
        try:
            st = os.stat(path)
            results[path] = f'Exists (UID: {st.st_uid}, GID: {st.st_gid})'
        except FileNotFoundError:
            results[path] = 'Not found'
    try:
        total, used, free = shutil.disk_usage('/')
        results['disk'] = f'Total: {total // (2**30)} GB, used: {used // (2**30)} GB, free: {free // (2**30)} GB'
    except Exception as exc:
        results['disk'] = f'Disk read error: {exc}'
    return results


def build_jenkins_plan(use_sudo=False, domain=None, certsresolver=None):
    """Build Jenkins setup and installation plan (mkdir, compose up).
    Does not bind the Docker socket automatically (avoid broad host permissions).
    """
    domain = domain or get_jenkins_domain()
    certsresolver = certsresolver or JENKINS_CERTSRESOLVER
    docker = docker_command(use_sudo)
    prefix = docker[:-len(DOCKER)]
    compose_content = (
        "services:\n"
        "  jenkins:\n"
        "    image: jenkins/jenkins:lts-jdk21\n"
        "    container_name: jenkins\n"
        "    restart: unless-stopped\n"
        "\n"
        "    expose:\n"
        "      - \"8080\"\n"
        "\n"
        "    volumes:\n"
        f"      - {JENKINS_HOST_DATA_DIR}:{JENKINS_HOST_DATA_DIR}\n"
        "\n"
        "    environment:\n"
        f"      TZ: {JENKINS_TIMEZONE}\n"
        "\n"
        "    networks:\n"
        f"      - {JENKINS_NETWORK}\n"
        "\n"
        "    labels:\n"
        "      - \"traefik.enable=true\"\n"
        f'      - "traefik.docker.network={JENKINS_NETWORK}"\n'
        f'      - "traefik.http.routers.jenkins.rule=Host(`{domain}`)"\n'
        '      - "traefik.http.routers.jenkins.entrypoints=websecure"\n'
        '      - "traefik.http.routers.jenkins.tls=true"\n'
        f'      - "traefik.http.routers.jenkins.tls.certresolver={certsresolver}"\n'
        f'      - "traefik.http.services.jenkins.loadbalancer.server.port={JENKINS_HTTP_PORT}"\n'
        "\n"
        "networks:\n"
        f"  {JENKINS_NETWORK}:\n"
        f"    external: true\n"
        f"    name: {JENKINS_NETWORK}\n"
    )
    return [
        prefix + ['mkdir', '-p', JENKINS_HOST_DATA_DIR],
        prefix + ['mkdir', '-p', JENKINS_HOST_CONFIG_DIR],
        prefix + ['chown', '-R', '1000:1000', JENKINS_HOST_DATA_DIR],
        (prefix + ['tee', f'{JENKINS_HOST_CONFIG_DIR}/docker-compose.yml'], compose_content),
    ]


def _write_file(command, content, use_sudo=False):
    run_step(command, content=content)


def install_jenkins(dry_run=False, use_sudo=False, domain=None, certsresolver=None):
    """Install Jenkins if not installed. If installed or conflict exists, no changes are made."""
    try:
        if platform.system() != 'Linux':
            raise ValueError('This installer is for Linux systems only.')
        report = inspect_jenkins(use_sudo=use_sudo)
        if report['status'] == 'installed':
            print(f'Jenkins is already installed. Container status shown above. Will not reinstall.')
            return True
        if report['status'] == 'conflict':
            print('Name jenkins is used by another container. No changes made.')
            return False
        if report['status'] == 'error':
            print(report['error'])
            return False

        for candidate in (JENKINS_HTTP_PORT, JENKINS_AGENT_PORT):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('0.0.0.0', candidate))

        if dry_run:
            print(f'[DRY-RUN] Will create directories: {JENKINS_HOST_DATA_DIR}, {JENKINS_HOST_CONFIG_DIR}')
            print(f'[DRY-RUN] Will set owner: 1000:1000 on {JENKINS_HOST_DATA_DIR}')
            print(f'[DRY-RUN] Will write config file: {JENKINS_HOST_CONFIG_DIR}/docker-compose.yml')
            print(f'[DRY-RUN] Will verify network {JENKINS_NETWORK} and create if missing')
            print(f'[DRY-RUN] Will run docker compose up -d using image {IMAGE}')
            print(f'[DRY-RUN] Domain: {domain or get_jenkins_domain()} | Certificate resolver: {certsresolver or JENKINS_CERTSRESOLVER}')
            print(f'[DRY-RUN] Access via Traefik only (HTTPS), port 8080 will not be published publicly')
            return True

        commands = build_jenkins_plan(use_sudo=use_sudo, domain=domain, certsresolver=certsresolver)
        for command in commands:
            if isinstance(command, tuple) and len(command) == 2:
                _write_file(command[0], command[1], use_sudo=use_sudo)
            else:
                run_step(command)

        net_check = subprocess.run(
            docker_command(use_sudo) + ['network', 'inspect', JENKINS_NETWORK],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False
        )
        if net_check.returncode != 0:
            run_step(docker_command(use_sudo) + ['network', 'create', '--driver', 'bridge', JENKINS_NETWORK])

        run_step(docker_command(use_sudo) + ['compose', '-f', f'{JENKINS_HOST_CONFIG_DIR}/docker-compose.yml', 'up', '-d'])
        code, state = probe(docker_command(use_sudo) + ['inspect', '--format', '{{.State.Status}}', JENKINS_CONTAINER])
        if code or state != 'running':
            print(f'Container created but status check did not confirm running: {state}. Check docker logs jenkins.')
            return False
        run_step(docker_command(use_sudo) + ['ps', '-a'])
        print(f'Jenkins container is running. Access via Traefik: https://{domain or get_jenkins_domain()}')
        print(f'Jenkins data: {JENKINS_HOST_DATA_DIR}')
        print(f'Config file: {JENKINS_HOST_CONFIG_DIR}/docker-compose.yml')
        print('Initial admin password: sudo docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword')
        print('Note: Docker socket is not mounted into the container for security reasons. Use an external build agent if needed.')
        return True
    except (OSError, ValueError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
        print(f'Jenkins installation stopped: {exc}. No existing data or containers were deleted; check output.')
        return False


JENKINS_ISSUE_NOT_INSTALLED = 'jenkins_not_installed'
JENKINS_ISSUE_PORT_8080 = 'jenkins_port_8080_in_use'
JENKINS_ISSUE_PORT_50000 = 'jenkins_port_50000_in_use'
JENKINS_ISSUE_CONTAINER_NOT_RUNNING = 'jenkins_container_not_running'
JENKINS_ISSUE_DATA_DIR_MISSING = 'jenkins_data_dir_missing'


def jenkins_diagnose(use_sudo=False):
    """Diagnose potential Jenkins errors and list suggested fixes."""
    issues = []
    repairs = []

    if not shutil.which('docker'):
        issues.append({
            'id': 'jenkins_docker_missing',
            'component': 'Jenkins',
            'title': 'Docker Engine is not installed',
            'description': 'Jenkins cannot run without Docker Engine.',
            'severity': 'critical',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'Install Docker Engine first from the menu.',
        })
        return issues, repairs

    report = inspect_jenkins(use_sudo=use_sudo)

    if report['status'] == 'error':
        issues.append({
            'id': 'jenkins_daemon_error',
            'component': 'Jenkins',
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
            'id': 'jenkins_name_conflict',
            'component': 'Jenkins',
            'title': 'Container name conflict jenkins',
            'description': 'Name jenkins is used by another container.',
            'severity': 'high',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'Rename the other container or remove it before installing.',
        })
        return issues, repairs

    # Check ports
    for port, issue_id, title, desc in (
        (JENKINS_HTTP_PORT, JENKINS_ISSUE_PORT_8080, 'Port 8080 (Jenkins HTTP) in use', 'Port 8080 is bound by another process.'),
        (JENKINS_AGENT_PORT, JENKINS_ISSUE_PORT_50000, 'Port 50000 (Jenkins Agent) in use', 'Port 50000 is bound by another process.'),
    ):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            if s.connect_ex(('127.0.0.1', port)) == 0:
                issues.append({
                    'id': issue_id,
                    'component': 'Jenkins',
                    'title': title,
                    'description': desc,
                    'severity': 'medium',
                    'auto_fix': False,
                    'fix_command': None,
                    'fix_description': 'Stop the service on the port or choose another port.',
                })

    # Check data directory
    if not os.path.exists(JENKINS_HOST_DATA_DIR):
        issues.append({
            'id': JENKINS_ISSUE_DATA_DIR_MISSING,
            'component': 'Jenkins',
            'title': 'Jenkins data directory not found',
            'description': f'Directory {JENKINS_HOST_DATA_DIR} not found.',
            'severity': 'medium',
            'auto_fix': True,
            'fix_command': ['mkdir', '-p', JENKINS_HOST_DATA_DIR],
            'fix_description': f'Create directory {JENKINS_HOST_DATA_DIR}.',
        })
        repairs.append((f'Create directory {JENKINS_HOST_DATA_DIR}', ['mkdir', '-p', JENKINS_HOST_DATA_DIR]))

    # Check container status
    if report['status'] == 'installed':
        for c in report['containers']:
            status = c.get('Status', '')
            # N02: docker ps Status is "Up X hours", not "running"
            if not status.lower().startswith("up"):
                issues.append({
                    'id': JENKINS_ISSUE_CONTAINER_NOT_RUNNING,
                    'component': 'Jenkins',
                    'title': 'Jenkins container not running',
                    'description': f'Container status: {status}',
                    'severity': 'high',
                    'auto_fix': True,
                    'fix_command': ['docker', 'start', 'jenkins'],
                    'fix_description': 'Start the stopped Jenkins container.',
                })
                repairs.append(('Start Jenkins container', ['docker', 'start', 'jenkins']))
            break

    return issues, repairs


def jenkins_repair(issue, use_sudo=False):
    """Execute a single fix for a Jenkins issue."""
    fix_cmd = issue.get('fix_command')
    if not fix_cmd:
        return False, 'No automatic repair command for this issue.'
    docker = docker_command(use_sudo)
    prefix = docker[:-len(DOCKER)]
    full_cmd = prefix + fix_cmd
    try:
        run_step(full_cmd)
        return True, 'Executed successfully.'
    except Exception as exc:
        return False, str(exc)
