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
    applications, databases = set(), set()
    conflict = False
    import re
    pattern = re.compile(rf"^odoo{re.escape(version)}(?:-instance[0-9]+)?(?:-db)?$")
    try:
        for line in output.splitlines():
            item = json.loads(line)
            name, image = item.get('Names', ''), item.get('Image', '')
            if not pattern.fullmatch(name):
                continue
            containers.append(item)
            database = name.endswith('-db')
            expected = PG_IMAGES[version] if database else ODOO_IMAGES[version]
            valid_image = re.match(r'^' + re.escape(expected) + r'(?:[.:-]|$)', image) is not None
            if not valid_image:
                conflict = True
            elif database:
                databases.add(name[:-3])
            else:
                applications.add(name)
    except (ValueError, AttributeError, TypeError):
        return {'status': 'error', 'containers': [], 'error': 'Failed to read Docker response.'}
    status = ('conflict' if conflict else 'installed' if applications and applications == databases
              else 'partial' if containers else 'missing')
    return {'status': status, 'containers': containers,
            'error': 'Container image/name conflict' if conflict else ''}


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

    if report['status'] == 'partial':
        issues.append({
            'id': f'odoo{version}_partial_install',
            'component': f'Odoo {version}',
            'title': f'Odoo {version} partially installed',
            'description': 'Only one of the Odoo or PostgreSQL containers is present. Reinstallation is needed.',
            'severity': 'high',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'Remove existing containers and re-run installation.',
        })
        return issues, repairs

    # Check container status
    odoo_running = False
    db_running = False
    for c in report['containers']:
        names = c.get('Names', '')
        status = c.get('Status', '')
        # N02: docker ps Status is "Up X hours", "Exited (0)...", "Restarting..." — not "running"
        is_running = status.lower().startswith("up") and not any(x in status.lower() for x in ("paused", "unhealthy"))
        if f'odoo{version}-db' in names:
            if not is_running:
                issues.append({
                    'id': f'odoo{version}_db_not_running',
                    'component': f'Odoo {version}',
                    'title': f'PostgreSQL container {PG_IMAGES[version].split(":")[1]} not running',
                    'description': f'Container status: {status}',
                    'severity': 'high',
                    'auto_fix': True,
                    'fix_command': ['docker', 'start', names],
                    'fix_description': f'Start Odoo {version} database container.',
                })
                repairs.append((f'Start Odoo {version} database', ['docker', 'start', f'odoo{version}-db']))
            else:
                db_running = True
        if f'odoo{version}' in names and '-db' not in names:
            if not is_running:
                issues.append({
                    'id': f'odoo{version}_container_not_running',
                    'component': f'Odoo {version}',
                    'title': f'Odoo {version} container not running',
                    'description': f'Container status: {status}',
                    'severity': 'high',
                    'auto_fix': True,
                    'fix_command': ['docker', 'start', names],
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
    full_cmd = docker + fix_cmd[1:] if fix_cmd[0] == 'docker' else prefix + fix_cmd
    try:
        run_step(full_cmd)
        return True, 'Executed successfully.'
    except Exception as exc:
        return False, str(exc)


def build_odoo_install_plan(profile, version: str, use_sudo=False, with_traefik=False):
    import sys
    from pathlib import Path
    from dataclasses import asdict
    if version not in ODOO_VERSIONS:
        raise ValueError('Unsupported version')
    script = str(Path(__file__).with_name('managed_stack.py'))
    prefix = ['sudo', '-n'] if use_sudo and not (hasattr(os, 'geteuid') and os.geteuid() == 0) else []
    return [prefix + [sys.executable, script, '--profile-json', json.dumps(asdict(profile)), '--version', version]]


def install_odoo(profile, version, dry_run=False, use_sudo=False, with_traefik=False):
    from copy import deepcopy
    profile = deepcopy(profile)
    profile.deployment_mode = 'domain' if with_traefik else 'local'
    getattr(profile, 'odoo' + version).enabled = True
    try:
        for command in build_odoo_install_plan(profile, version, use_sudo, with_traefik):
            run_step(command, dry_run=dry_run)
        print('Deployment plan only; not verified.' if dry_run else 'Odoo and PostgreSQL health verified.')
        return True
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'Deployment failed: {exc}')
        return False
