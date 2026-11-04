"""Odoo 17/18/19 discovery, diagnosis, and installation on the local Linux Docker Engine."""
import json
import os
import platform
import shutil
import socket
import subprocess
from typing import Dict, List, Optional, Tuple

from app.services.runtime_inspector import probe
from app.services.docker_installer import run_step

DOCKER = ['docker', '--host', 'unix:///var/run/docker.sock']

ODOO_VERSIONS = ('17', '18', '19')
ODOO_IMAGES = {'17': 'odoo:17', '18': 'odoo:18', '19': 'odoo:19'}
PG_IMAGES = {'17': 'postgres:16', '18': 'postgres:17', '19': 'postgres:18'}
ODOO_HTTP_PORTS = {'17': 10017, '18': 10018, '19': 10019}
ODOO_CHAT_PORTS = {'17': 20017, '18': 20018, '19': 20019}
ODOO_INTERNAL_NETWORKS = {'17': 'odoo17_internal', '18': 'odoo18_internal', '19': 'odoo19_internal'}


def docker_command(use_sudo=False):
    return (['sudo', '-n'] if use_sudo and not (hasattr(os, 'geteuid') and os.geteuid() == 0) else []) + DOCKER


def inspect_odoo(version: str, use_sudo=False):
    """Check status of a specific Odoo version (installed / missing / conflict / error)."""
    if version not in ODOO_VERSIONS:
        return {'status': 'error', 'containers': [], 'error': f'Unsupported version: {version}'}
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
            names = item.get('Names', '')
            image = item.get('Image', '')
            is_odoo = f'odoo{version}' in names or image.startswith(ODOO_IMAGES[version])
            is_db = f'odoo{version}-db' in names or image.startswith(PG_IMAGES[version])
            if is_odoo or is_db:
                containers.append(item)
                collision |= not (is_odoo or is_db)
    except (ValueError, AttributeError):
        return {'status': 'error', 'containers': [], 'error': 'Failed to read Docker response.'}
    return {'status': 'conflict' if collision else 'installed' if containers else 'missing',
            'containers': containers, 'error': ''}


def odoo_diagnose(version: str, use_sudo=False):
    """Diagnose potential Odoo errors and list suggested fixes."""
    issues = []
    repairs = []

    if version not in ODOO_VERSIONS:
        issues.append({
            'id': 'odoo_invalid_version',
            'component': f'Odoo {version}',
            'title': 'Unsupported Odoo version',
            'description': f'Version {version} is not supported. Supported versions: 17, 18, 19.',
            'severity': 'critical',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'Select a supported version (17 or 18 or 19).',
        })
        return issues, repairs

    if not shutil.which('docker'):
        issues.append({
            'id': f'odoo{version}_docker_missing',
            'component': f'Odoo {version}',
            'title': 'Docker Engine is not installed',
            'description': 'Odoo cannot run without Docker Engine.',
            'severity': 'critical',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'Install Docker Engine first from the menu.',
        })
        return issues, repairs

    report = inspect_odoo(version, use_sudo=use_sudo)

    if report['status'] == 'error':
        issues.append({
            'id': f'odoo{version}_daemon_error',
            'component': f'Odoo {version}',
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
            'id': f'odoo{version}_name_conflict',
            'component': f'Odoo {version}',
            'title': 'Odoo container name conflict',
            'description': f'Container name odoo{version} or odoo{version}-db is used by another container.',
            'severity': 'high',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'Rename the other container or remove it before installing.',
        })
        return issues, repairs

    # Check container status
    odoo_running = False
    db_running = False
    for c in report['containers']:
        names = c.get('Names', '')
        status = c.get('Status', '')
        if f'odoo{version}-db' in names:
            if 'Exited' in status or 'Created' in status:
                issues.append({
                    'id': f'odoo{version}_db_not_running',
                    'component': f'Odoo {version}',
                    'title': f'PostgreSQL container {PG_IMAGES[version].split(":")[1]} not running',
                    'description': f'Container status: {status}',
                    'severity': 'high',
                    'auto_fix': True,
                    'fix_command': ['start', f'odoo{version}-db'],
                    'fix_description': f'Start Odoo {version} database container.',
                })
                repairs.append((f'Start Odoo {version} database', ['docker', 'start', f'odoo{version}-db']))
            else:
                db_running = True
        if f'odoo{version}' in names and '-db' not in names:
            if 'Exited' in status or 'Created' in status:
                issues.append({
                    'id': f'odoo{version}_container_not_running',
                    'component': f'Odoo {version}',
                    'title': f'Odoo {version} container not running',
                    'description': f'Container status: {status}',
                    'severity': 'high',
                    'auto_fix': True,
                    'fix_command': ['start', f'odoo{version}'],
                    'fix_description': f'Start Odoo {version} container.',
                })
                repairs.append((f'Start Odoo {version}', ['docker', 'start', f'odoo{version}']))
            else:
                odoo_running = True

    # Check ports
    http_port = ODOO_HTTP_PORTS[version]
    chat_port = ODOO_CHAT_PORTS[version]
    for port, issue_id, title, desc in (
        (http_port, f'odoo{version}_port_http_in_use', f'Port {http_port} (Odoo HTTP) in use', f'Port {http_port} is bound by another process.'),
        (chat_port, f'odoo{version}_port_chat_in_use', f'Port {chat_port} (Odoo Livechat) in use', f'Port {chat_port} is bound by another process.'),
    ):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            if s.connect_ex(('127.0.0.1', port)) == 0:
                issues.append({
                    'id': issue_id,
                    'component': f'Odoo {version}',
                    'title': title,
                    'description': desc,
                    'severity': 'medium',
                    'auto_fix': False,
                    'fix_command': None,
                    'fix_description': 'Stop the service on the port or choose another port.',
                })

    # Check installation directory
    destination = f'/opt/odoo-infrastructure/odoo{version}'
    if not os.path.exists(destination):
        issues.append({
            'id': f'odoo{version}_dir_missing',
            'component': f'Odoo {version}',
            'title': f'Odoo {version} installation directory not found',
            'description': f'Directory {destination} not found.',
            'severity': 'medium',
            'auto_fix': True,
            'fix_command': ['mkdir', '-p', destination],
            'fix_description': f'Create installation directory {destination}.',
        })
        repairs.append((f'Create directory {destination}', ['mkdir', '-p', destination]))

    # Check .env file
    env_file = f'{destination}/.env'
    if os.path.exists(destination) and not os.path.exists(env_file):
        issues.append({
            'id': f'odoo{version}_env_missing',
            'component': f'Odoo {version}',
            'title': f'Odoo {version} .env file not found',
            'description': 'Configuration instance .env file not found, reconfiguration needed.',
            'severity': 'medium',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'Re-run Odoo installation to create the configuration file.',
        })

    return issues, repairs


def odoo_repair(issue: Dict, use_sudo=False):
    """Execute a single fix for an Odoo issue."""
    fix_cmd = issue.get('fix_command')
    if not fix_cmd:
        return False, 'No automatic repair command for this issue.'
    docker = docker_command(use_sudo)
    prefix = docker[:-len(DOCKER)]
    full_cmd = prefix + fix_cmd if fix_cmd[0] != 'docker' else fix_cmd
    try:
        run_step(full_cmd)
        return True, 'Executed successfully.'
    except Exception as exc:
        return False, str(exc)


def build_odoo_install_plan(profile, version: str, use_sudo=False, with_traefik: bool = False):
    """Build Odoo installation plan (run install-odoo.sh)."""
    destination = f"{profile.paths.data_root}/odoo{version}"
    command = [
        "bash",
        "automation/scripts/install-odoo.sh",
        version,
        "--destination",
        destination,
    ]
    if with_traefik:
        command.append("--with-traefik")
    prefix = [] if (hasattr(os, 'geteuid') and os.geteuid() == 0) else ['sudo']
    return [
        prefix + ['mkdir', '-p', destination],
        prefix + command,
    ]


def install_odoo(profile, version: str, dry_run: bool = False, use_sudo: bool = False,
                 with_traefik: bool = False):
    """Install Odoo version if not installed. If installed, no changes are made."""
    try:
        if platform.system() != 'Linux':
            raise ValueError('This installer is for Linux systems only.')
        if version not in ODOO_VERSIONS:
            raise ValueError(f'Unsupported version: {version}')

        report = inspect_odoo(version, use_sudo=use_sudo)
        if report['status'] == 'installed':
            print(f'Odoo {version} is already installed. Container status shown above. Will not reinstall.')
            return True
        if report['status'] == 'conflict':
            print(f'Odoo {version} container name is used by another container. No changes made.')
            return False
        if report['status'] == 'error':
            print(report['error'])
            return False

        # Check ports before installation
        http_port = ODOO_HTTP_PORTS[version]
        chat_port = ODOO_CHAT_PORTS[version]
        for port in (http_port, chat_port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('0.0.0.0', port))

        if dry_run:
            print(f'[DRY-RUN] Will install Odoo {version} with PostgreSQL {PG_IMAGES[version].split(":")[1]}')
            print(f'[DRY-RUN] Directory: {profile.paths.data_root}/odoo{version}')
            print(f'[DRY-RUN] HTTP port: {http_port} | Chat port: {chat_port}')
            print(f'[DRY-RUN] Internal network: {ODOO_INTERNAL_NETWORKS[version]}')
            print(f'[DRY-RUN] With Traefik: {"yes" if with_traefik else "no"}')
            return True

        commands = build_odoo_install_plan(profile, version, use_sudo=use_sudo, with_traefik=with_traefik)
        for command in commands:
            run_step(command)

        # Check container status after installation
        code, state = probe(docker_command(use_sudo) + ['inspect', '--format', '{{.State.Status}}', f'odoo{version}'])
        if code or state != 'running':
            print(f'Odoo {version} container created but not in running state: {state}. Check logs.')
            return False
        code, db_state = probe(docker_command(use_sudo) + ['inspect', '--format', '{{.State.Status}}', f'odoo{version}-db'])
        if code or db_state != 'running':
            print(f'Odoo {version} database container created but not in running state: {db_state}. Check logs.')
            return False

        run_step(docker_command(use_sudo) + ['ps', '-a'])
        print(f'Odoo {version} running successfully with PostgreSQL {PG_IMAGES[version].split(":")[1]}.')
        print(f'Address: http://localhost:{http_port} (or via Traefik on HTTPS)')
        print(f'Data: {profile.paths.data_root}/odoo{version}/postgresql')
        print(f'Config: {profile.paths.data_root}/odoo{version}/etc/odoo.conf')
        return True
    except (OSError, ValueError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
        print(f'Odoo {version} installation stopped: {exc}. No existing data or containers were deleted; check output.')
        return False
