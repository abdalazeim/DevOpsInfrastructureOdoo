"""Inspect and install the Docker Compose plugin without changing the Engine."""
import os
import platform
import shutil
import subprocess

from app.services.runtime_inspector import probe
from app.services.docker_installer import run_step


def inspect_compose():
    docker = shutil.which('docker')
    if not docker:
        return {'status': 'docker_missing', 'path': '', 'details': 'Docker client not found in PATH; set up Docker Engine first.'}
    code, output = probe([docker, 'compose', 'version'])
    return {'status': 'installed' if code == 0 and output else 'unavailable',
            'path': docker, 'details': output or 'Command did not return a version; extension is unavailable or could not be run.'}


def install_compose(dry_run=False):
    report = inspect_compose()
    if report['status'] == 'installed':
        print(f"The extension is already installed: {report['details']}")
        return True
    if report['status'] == 'docker_missing':
        print(report['details'])
        return False
    prefix = [] if hasattr(os, 'geteuid') and os.geteuid() == 0 else ['sudo']
    commands = [prefix + ['apt-get', 'update'],
                prefix + ['apt-get', 'install', '-y', 'docker-compose-plugin'],
                [report['path'], 'compose', 'version']]
    try:
        if not dry_run and platform.freedesktop_os_release().get('ID') != 'ubuntu':
            raise ValueError('This path is for Ubuntu.')
        for command in commands:
            run_step(command, dry_run=dry_run)
        if not dry_run:
            verified = inspect_compose()
            if verified['status'] != 'installed':
                print(f"Verification failed after installation: {verified['details']}")
                return False
            print(f"Extension installed and verified: {verified['details']}")
        return True
    except (OSError, ValueError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
        print(f'Compose installation stopped: {exc}. Check Docker official repository availability and apt output.')
        return False
