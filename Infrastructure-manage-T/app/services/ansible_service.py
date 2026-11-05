"""Ansible automation service for baseline Ubuntu server configuration."""
import json
import os
import platform
import shutil
import socket
import subprocess
from typing import Dict, Any, List, Optional

from app.models.operation import WorkflowStep
from app.services.docker_installer import run_step


class AnsibleService:
    """Builds Ansible runner commands with idempotency and dry-run (--check) support."""

    @staticmethod
    def build_playbook_step(
        playbook_path: str = "automation/ansible/playbook.yml",
        inventory_path: str = "automation/ansible/inventory.ini",
        extra_vars: Optional[Dict[str, Any]] = None,
        check_mode: bool = False,
        tags: Optional[List[str]] = None,
        step_id: str = "ansible-baseline"
    ) -> WorkflowStep:
        cmd = ["ansible-playbook", "-i", inventory_path, playbook_path]

        if check_mode:
            cmd.append("--check")

        if tags:
            cmd.extend(["--tags", ",".join(tags)])

        if extra_vars:
            cmd.extend(["--extra-vars", json.dumps(extra_vars)])

        return WorkflowStep(
            id=step_id,
            name="Run Ansible Baseline Playbook",
            description=f"Applies server baseline tasks from {playbook_path} (Check mode: {check_mode})",
            command=cmd,
        )


ANSIBLE_DIR = '/opt/ansible'
ANSIBLE_INVENTORY_DIR = os.path.join(ANSIBLE_DIR, 'inventory')
ANSIBLE_PLAYBOOKS_DIR = os.path.join(ANSIBLE_DIR, 'playbooks')
ANSIBLE_ROLES_DIR = os.path.join(ANSIBLE_DIR, 'roles')
ANSIBLE_GROUP_VARS_DIR = os.path.join(ANSIBLE_DIR, 'group_vars')
ANSIBLE_HOST_VARS_DIR = os.path.join(ANSIBLE_DIR, 'host_vars')
ANSIBLE_FILES_DIR = os.path.join(ANSIBLE_DIR, 'files')
ANSIBLE_TEMPLATES_DIR = os.path.join(ANSIBLE_DIR, 'templates')
ANSIBLE_CFG_FILE = os.path.join(ANSIBLE_DIR, 'ansible.cfg')
ANSIBLE_HOSTS_FILE = os.path.join(ANSIBLE_INVENTORY_DIR, 'hosts.ini')
ANSIBLE_SITE_PLAYBOOK = os.path.join(ANSIBLE_PLAYBOOKS_DIR, 'site.yml')


def ansible_command(use_sudo=False):
    return (['sudo', '-n'] if use_sudo and not (hasattr(os, 'geteuid') and os.geteuid() == 0) else []) + ['ansible-playbook']


def inspect_ansible(use_sudo=False):
    """Check Ansible status on the system (installed / missing / error)."""
    if not shutil.which('ansible-playbook'):
        return {'status': 'missing', 'version': None, 'error': 'Ansible is not installed on the system.'}
    code, output = probe(['ansible-playbook', '--version'])
    if code:
        return {'status': 'error', 'version': None, 'error': output}
    version_line = output.splitlines()[0] if output else ''
    return {'status': 'installed', 'version': version_line, 'error': ''}


def probe(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        return result.returncode, (result.stdout or result.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return -1, str(exc)


def build_ansible_install_plan(use_sudo=False):
    """Build Ansible installation plan (write script and run it)."""
    docker = ['sudo'] if use_sudo and not (hasattr(os, 'geteuid') and os.geteuid() == 0) else []
    prefix = docker
    install_script = '/tmp/install-ansible.sh'
    script_content = (
        '#!/bin/bash\n'
        'set -euo pipefail\n'
        '\n'
        'echo "======================================"\n'
        'echo " Installing Ansible on Ubuntu Server"\n'
        'echo "======================================"\n'
        '\n'
        '# Update system\n'
        'apt-get update\n'
        'apt-get upgrade -y\n'
        '\n'
        '# Install requirements\n'
        'apt-get install -y \\\n'
        '    python3 \\\n'
        '    python3-pip \\\n'
        '    pipx \\\n'
        '    openssh-client \\\n'
        '    sshpass \\\n'
        '    git \\\n'
        '    curl \\\n'
        '    nano \\\n'
        '    rsync\n'
        '\n'
        '# Setup pipx\n'
        'USER_HOME=$(getent passwd "${SUDO_USER:-$USER}" | cut -d: -f6)\n'
        'USER_NAME="${SUDO_USER:-$USER}"\n'
        '\n'
        'if [ -z "$USER_HOME" ]; then\n'
        '    USER_HOME="/root"\n'
        'fi\n'
        '\n'
        '# Install Ansible using pipx\n'
        'sudo -u "$USER_NAME" -H pipx ensurepath\n'
        'sudo -u "$USER_NAME" -H pipx install --include-deps ansible\n'
        '\n'
        '# Create project directories\n'
        f'mkdir -p {ANSIBLE_DIR}/{{inventory,playbooks,roles,group_vars,host_vars,files,templates}}\n'
        f'chown -R "$USER_NAME":"$USER_NAME" {ANSIBLE_DIR}\n'
        '\n'
        '# Create config file\n'
        f'cat > {ANSIBLE_CFG_FILE} <<\'EOF\'\n'
        '[defaults]\n'
        f'inventory = {ANSIBLE_INVENTORY_DIR}/hosts.ini\n'
        f'roles_path = {ANSIBLE_ROLES_DIR}\n'
        'host_key_checking = True\n'
        'retry_files_enabled = False\n'
        'timeout = 30\n'
        'interpreter_python = auto_silent\n'
        '\n'
        '[privilege_escalation]\n'
        'become = True\n'
        'become_method = sudo\n'
        'become_ask_pass = False\n'
        'EOF\n'
        '\n'
        '# Setup local Inventory\n'
        f'cat > {ANSIBLE_HOSTS_FILE} <<\'EOF\'\n'
        '[local]\n'
        'localhost ansible_connection=local\n'
        '\n'
        '[all:vars]\n'
        'ansible_python_interpreter=/usr/bin/python3\n'
        'EOF\n'
        '\n'
        '# Create test Playbook\n'
        f'cat > {ANSIBLE_SITE_PLAYBOOK} <<\'EOF\'\n'
        '---\n'
        '- name: Verify Ubuntu server\n'
        '  hosts: local\n'
        '  become: true\n'
        '  gather_facts: true\n'
        '\n'
        '  tasks:\n'
        '    - name: Display server hostname\n'
        '      ansible.builtin.debug:\n'
        '        msg: "Server: {{ ansible_hostname }}"\n'
        '\n'
        '    - name: Check Docker service\n'
        '      ansible.builtin.service_facts:\n'
        '\n'
        '    - name: Display Docker service status\n'
        '      ansible.builtin.debug:\n'
        '        msg: "Docker service information collected"\n'
        'EOF\n'
        '\n'
        '# Install Collections\n'
        f'sudo -u "$USER_NAME" -H ansible-galaxy collection install \\\n'
        '    community.docker ansible.posix\n'
        '\n'
        'echo "======================================"\n'
        'echo " Ansible installation completed"\n'
        'echo "======================================"\n'
        f'echo "Project: {ANSIBLE_DIR}"\n'
        'echo "Next: Log out and log in again, then run:"\n'
        '  cd /opt/ansible\n'
        '  ansible --version\n'
        '  ansible local -m ping\n'
        '  ansible-playbook playbooks/site.yml\n'
    )
    # F21: Write the script content to disk so tee is not left waiting on stdin.
    with open(install_script, "w", encoding="utf-8") as f:
        f.write(script_content)
    os.chmod(install_script, 0o755)
    return [
        prefix + ['bash', install_script],
    ]


def install_ansible(dry_run=False, use_sudo=False):
    """Install Ansible if not installed. If installed, no changes are made."""
    try:
        if platform.system() != 'Linux':
            raise ValueError('This installer is for Linux systems only.')
        report = inspect_ansible(use_sudo=use_sudo)
        if report['status'] == 'installed':
            print(f'Ansible is already installed: {report["version"]}. Will not reinstall.')
            return True
        if report['status'] == 'error':
            print(report['error'])
            return False

        if dry_run:
            script_content = (
                'pipx ensurepath\n'
                'pipx install --include-deps ansible\n'
                f'mkdir -p {ANSIBLE_DIR}/{{inventory,playbooks,roles,group_vars,host_vars,files,templates}}\n'
                f'cat > {ANSIBLE_CFG_FILE}\n'
                f'cat > {ANSIBLE_HOSTS_FILE}\n'
                f'cat > {ANSIBLE_SITE_PLAYBOOK}\n'
                'ansible-galaxy collection install community.docker ansible.posix\n'
            )
            print(f'[DRY-RUN] Would install Ansible via pipx into {ANSIBLE_DIR}')
            print(script_content)
            return True

        commands = build_ansible_install_plan(use_sudo=use_sudo)
        for command in commands:
            run_step(command)

        code, version = probe(['ansible-playbook', '--version'])
        if code:
            print(f'Ansible installation completed but version check failed: {version}')
            return False
        print(f'Ansible installed successfully: {version.splitlines()[0]}')
        print(f'Project: {ANSIBLE_DIR}')
        print('Next step: Log out and log in again, then run:')
        print(f'  cd {ANSIBLE_DIR}')
        print('  ansible --version')
        print('  ansible local -m ping')
        print('  ansible-playbook playbooks/site.yml')
        return True
    except (OSError, ValueError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
        print(f'Ansible installation stopped: {exc}. No existing data or containers were deleted; check output.')
        return False


ANSIBLE_ISSUE_NOT_INSTALLED = 'ansible_not_installed'
ANSIBLE_ISSUE_DIR_MISSING = 'ansible_dir_missing'
ANSIBLE_ISSUE_CFG_MISSING = 'ansible_cfg_missing'
ANSIBLE_ISSUE_INVENTORY_MISSING = 'ansible_inventory_missing'


def ansible_diagnose(use_sudo=False):
    """Diagnose potential Ansible errors and list suggested fixes."""
    issues = []
    repairs = []

    if not shutil.which('ansible-playbook'):
        issues.append({
            'id': ANSIBLE_ISSUE_NOT_INSTALLED,
            'component': 'Ansible',
            'title': 'Ansible is not installed',
            'description': 'ansible-playbook command not found in PATH.',
            'severity': 'critical',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'Install Ansible via the installation menu option.',
        })
        return issues, repairs

    # Check project directories
    for path, issue_id, title, desc, fix_cmd, fix_desc in (
        (ANSIBLE_DIR, ANSIBLE_ISSUE_DIR_MISSING, 'Directory /opt/ansible not found', 'Ansible project directory is missing.', ['mkdir', '-p', ANSIBLE_DIR], 'Create directory /opt/ansible.'),
        (ANSIBLE_CFG_FILE, ANSIBLE_ISSUE_CFG_MISSING, 'File ansible.cfg not found', 'Main config file is missing.', None, ' Run Ansible installation again to create the config file.'),
        (ANSIBLE_HOSTS_FILE, ANSIBLE_ISSUE_INVENTORY_MISSING, 'File inventory/hosts.ini not found', 'Inventory file is missing.', None, ' Run Ansible installation again to create the inventory file.'),
    ):
        if not os.path.exists(path):
            issues.append({
                'id': issue_id,
                'component': 'Ansible',
                'title': title,
                'description': desc,
                'severity': 'medium',
                'auto_fix': fix_cmd is not None,
                'fix_command': fix_cmd,
                'fix_description': fix_desc,
            })
            if fix_cmd:
                repairs.append((title, fix_cmd))

    # Check environment variables
    if not os.path.expanduser('~/.local/bin/ansible-playbook'):
        issues.append({
            'id': 'ansible_path_missing',
            'component': 'Ansible',
            'title': 'Ansible not in user PATH',
            'description': 'User may need to log out and back in to activate PATH.',
            'severity': 'low',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'Log out and log in again, or add ~/.local/bin to PATH.',
        })

    return issues, repairs


def ansible_repair(issue, use_sudo=False):
    """Execute a single fix for an Ansible issue."""
    fix_cmd = issue.get('fix_command')
    if not fix_cmd:
        return False, 'No automatic repair command for this issue.'
    try:
        run_step(fix_cmd)
        return True, 'Executed successfully.'
    except Exception as exc:
        return False, str(exc)
