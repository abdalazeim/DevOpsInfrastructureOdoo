"""Portainer CE discovery and installation on the local Linux Docker Engine."""
import json
import os
import platform
import shutil
import socket
import subprocess

from app.services.runtime_inspector import probe
from app.services.docker_installer import run_step

DOCKER = ['docker', '--host', 'unix:///var/run/docker.sock']
IMAGE = 'portainer/portainer-ce:latest'

PORT_ISSUE_PORT_9443 = 'port_9443_in_use'
PORT_ISSUE_PORT_8000 = 'port_8000_in_use'
ISSUE_DOCKER_MISSING = 'docker_missing'
ISSUE_CONTAINER_NOT_RUNNING = 'container_not_running'
ISSUE_BIND_MOUNT_MISSING = 'bind_mount_missing'


def docker_command(use_sudo=False):
    return (['sudo', '-n'] if use_sudo and not (hasattr(os, 'geteuid') and os.geteuid() == 0) else []) + DOCKER


def inspect_portainer(use_sudo=False):
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
            repository = item.get('Image', '').split('@')[0].split(':')[0]
            is_portainer = repository in ('portainer/portainer-ce', 'portainer/portainer-ee', 'portainer/portainer')
            if is_portainer or item.get('Names') == 'portainer':
                containers.append(item)
                collision |= not is_portainer
    except (ValueError, AttributeError):
        return {'status': 'error', 'containers': [], 'error': 'Failed to read Docker response.'}
    return {'status': 'conflict' if collision else 'installed' if containers else 'missing',
            'containers': containers, 'error': ''}


def portainer_diagnose(use_sudo=False):
    """Diagnose potential Portainer errors and list suggested fixes."""
    issues = []
    repairs = []

    if not shutil.which('docker'):
        issues.append({
            'id': ISSUE_DOCKER_MISSING,
            'component': 'Portainer',
            'title': 'Docker Engine is not installed',
            'description': 'Portainer cannot run without Docker Engine.',
            'severity': 'critical',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'Install Docker Engine first from the menu.',
        })
        return issues, repairs

    report = inspect_portainer(use_sudo=use_sudo)

    if report['status'] == 'error':
        issues.append({
            'id': 'portainer_daemon_error',
            'component': 'Portainer',
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
            'id': 'portainer_name_conflict',
            'component': 'Portainer',
            'title': 'Container name conflict portainer',
            'description': 'Name portainer is used by another container.',
            'severity': 'high',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'Rename the other container or remove it before installing.',
        })
        return issues, repairs

    if report['status'] == 'installed':
        for c in report['containers']:
            status = c.get('Status', '')
            if not status.startswith('Up ') or '(Paused)' in status or '(unhealthy)' in status:
                issues.append({
                    'id': 'portainer_container_not_running',
                    'component': 'Portainer',
                    'title': 'Portainer container not running',
                    'description': f'Container status: {status}',
                    'severity': 'high',
                    'auto_fix': True,
                    'fix_command': ['docker', 'start', c['Names']],
                    'fix_description': 'Start the stopped Portainer container.',
                })
                repairs.append(('Start Portainer container', ['docker', 'start', c['Names']]))
            break

    if report['status'] == 'installed':
        return issues, repairs

    # Check ports only before installation; owned listening ports are not conflicts.
    for port, issue_id, title in ((9443, PORT_ISSUE_PORT_9443, 'Port 9443 in use'),
                                   (8000, PORT_ISSUE_PORT_8000, 'Port 8000 in use')):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            if s.connect_ex(('127.0.0.1', port)) == 0:
                issues.append({
                    'id': issue_id,
                    'component': 'Portainer',
                    'title': title,
                    'description': f'Port {port} is bound by another process.',
                    'severity': 'medium',
                    'auto_fix': False,
                    'fix_command': None,
                    'fix_description': 'Stop the service on the port or choose another port.',
                })

    return issues, repairs


def portainer_repair(issue, use_sudo=False):
    """Execute a single fix for a Portainer issue."""
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


def build_plan(port=9443, edge=True, use_sudo=False):
    if type(port) is not int or not 1 <= port <= 65535 or (edge and port == 8000):
        raise ValueError('Invalid HTTPS port or conflicts with Edge port 8000.')
    docker = docker_command(use_sudo)
    prefix = docker[:-len(DOCKER)]
    command = docker + ['run', '-d', '-p', f'{port}:9443']
    if edge:
        command += ['-p', '8000:8000']
    command += ['--name', 'portainer', '--restart=always',
                '-v', '/var/run/docker.sock:/var/run/docker.sock',
                '-v', 'portainer_data:/data', IMAGE]
    return [docker + ['volume', 'create', 'portainer_data'], command]


def install_portainer(port=9443, edge=True, dry_run=False, use_sudo=False):
    try:
        commands = build_plan(port, edge, use_sudo)
        if dry_run:
            for command in commands:
                run_step(command, dry_run=True)
            return True
        if platform.system() != 'Linux':
            raise ValueError('This installer is for the local Docker engine on Linux.')
        report = inspect_portainer(use_sudo=use_sudo)
        if report['status'] != 'missing':
            print('Installation not executed: a container or conflict exists or inspection failed. No existing container will be removed.')
            print(report['error'])
            return False
        for candidate in ([port, 8000] if edge else [port]):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('0.0.0.0', candidate))
        for command in commands:
            run_step(command)
        code, state = probe(docker_command(use_sudo) + ['inspect', '--format', '{{.State.Status}}', 'portainer'])
        if code or state != 'running':
            print(f'Container created but status check did not confirm running: {state}. Check docker logs portainer.')
            return False
        run_step(docker_command(use_sudo) + ['ps', '-a'])
        print(f'Portainer container is running. Open https://<SERVER-IP>:{port} to complete initial setup.')
        print('This verifies container is running; HTTP UI readiness has not been tested yet.')
        print('You may need a setup code from sudo docker logs portainer.')
        return True
    except (OSError, ValueError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
        print(f'Portainer installation stopped: {exc}. No existing data or containers were deleted; check output.')
        return False
