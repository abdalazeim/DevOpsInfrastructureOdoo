"""
Ansible automation service for baseline Ubuntu server configuration.
"""
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
    """فحص حالة أنsible على النظام (مثبت / مفقود / خطأ)."""
    if not shutil.which('ansible-playbook'):
        return {'status': 'missing', 'version': None, 'error': 'أنsible غير مثبت على النظام.'}
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
    """بناء خطة تثبيت أنsible (إنشاء السكربت وتشغيله)."""
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
        '# تحديث النظام\n'
        'apt-get update\n'
        'apt-get upgrade -y\n'
        '\n'
        '# تثبيت المتطلبات\n'
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
        '# إعداد pipx\n'
        'USER_HOME=$(getent passwd "${SUDO_USER:-$USER}" | cut -d: -f6)\n'
        'USER_NAME="${SUDO_USER:-$USER}"\n'
        '\n'
        'if [ -z "$USER_HOME" ]; then\n'
        '    USER_HOME="/root"\n'
        'fi\n'
        '\n'
        '# تثبيت Ansible باستخدام pipx\n'
        'sudo -u "$USER_NAME" -H pipx ensurepath\n'
        'sudo -u "$USER_NAME" -H pipx install --include-deps ansible\n'
        '\n'
        '# إنشاء مجلدات المشروع\n'
        f'mkdir -p {ANSIBLE_DIR}/{{inventory,playbooks,roles,group_vars,host_vars,files,templates}}\n'
        f'chown -R "$USER_NAME":"$USER_NAME" {ANSIBLE_DIR}\n'
        '\n'
        '# إنشاء ملف الإعدادات\n'
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
        '# إعداد Inventory محلي\n'
        f'cat > {ANSIBLE_HOSTS_FILE} <<\'EOF\'\n'
        '[local]\n'
        'localhost ansible_connection=local\n'
        '\n'
        '[all:vars]\n'
        'ansible_python_interpreter=/usr/bin/python3\n'
        'EOF\n'
        '\n'
        '# إنشاء Playbook للاختبار\n'
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
        '# تثبيت Collections\n'
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
    return [
        prefix + ['tee', '/tmp/install-ansible.sh'],
        prefix + ['chmod', '+x', '/tmp/install-ansible.sh'],
        prefix + ['bash', '/tmp/install-ansible.sh'],
    ]


def install_ansible(dry_run=False, use_sudo=False):
    """تنصيب أنsible إن لم يكن مثبتًا. إذا مثبت، لا يُنفذ أي تغيير."""
    try:
        if platform.system() != 'Linux':
            raise ValueError('هذا المثبت مخصص لنظام Linux.')
        report = inspect_ansible(use_sudo=use_sudo)
        if report['status'] == 'installed':
            print(f'أنsible مثبت بالفعل: {report["version"]}. لن يعاد التثبيت.')
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
            print(f'تثبيت أنsible اكتمل لكن التحقق من الإصدار فشل: {version}')
            return False
        print(f'تم تثبيت أنsible بنجاح: {version.splitlines()[0]}')
        print(f'المشروع: {ANSIBLE_DIR}')
        print('الخطوة التالية: تسجيل الخروج والدخول مرة أخرى، ثم تشغيل:')
        f'  cd {ANSIBLE_DIR}\n'
        f'  ansible --version\n'
        f'  ansible local -m ping\n'
        f'  ansible-playbook playbooks/site.yml\n'
        return True
    except (OSError, ValueError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
        print(f'توقف تثبيت أنsible: {exc}. لم تُحذف بيانات أو حاويات قائمة؛ راجع المخرجات.')
        return False


ANSIBLE_ISSUE_NOT_INSTALLED = 'ansible_not_installed'
ANSIBLE_ISSUE_DIR_MISSING = 'ansible_dir_missing'
ANSIBLE_ISSUE_CFG_MISSING = 'ansible_cfg_missing'
ANSIBLE_ISSUE_INVENTORY_MISSING = 'ansible_inventory_missing'


def ansible_diagnose(use_sudo=False):
    """تشخيص أخطاء أنsible المحتملة وقائمة بالإصلاحات المقترحة."""
    issues = []
    repairs = []

    if not shutil.which('ansible-playbook'):
        issues.append({
            'id': ANSIBLE_ISSUE_NOT_INSTALLED,
            'component': 'Ansible',
            'title': 'أنsible غير مثبت',
            'description': 'أمر ansible-playbook غير موجود في PATH.',
            'severity': 'critical',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'ثبت أنsible عبر خيار التثبيت في القائمة.',
        })
        return issues, repairs

    # فحص مجلدات المشروع
    for path, issue_id, title, desc, fix_cmd, fix_desc in (
        (ANSIBLE_DIR, ANSIBLE_ISSUE_DIR_MISSING, 'مجلد /opt/ansible غير موجود', 'مجلد مشروع أنsible غير موجود.', ['mkdir', '-p', ANSIBLE_DIR], 'إنشاء مجلد /opt/ansible.'),
        (ANSIBLE_CFG_FILE, ANSIBLE_ISSUE_CFG_MISSING, 'ملف ansible.cfg غير موجود', 'ملف الإعدادات الأساسي مفقود.', None, ' أعد تشغيل تثبيت أنsible لإنشاء ملف الإعدادات.'),
        (ANSIBLE_HOSTS_FILE, ANSIBLE_ISSUE_INVENTORY_MISSING, 'ملف inventory/hosts.ini غير موجود', 'ملف الجرد غير موجود.', None, ' أعد تشغيل تثبيت أنsible لإنشاء ملف الجرد.'),
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

    # فحص متغيرات البيئة
    if not os.path.expanduser('~/.local/bin/ansible-playbook'):
        issues.append({
            'id': 'ansible_path_missing',
            'component': 'Ansible',
            'title': 'أنsible ليس في PATH المستخدم',
            'description': 'قد يحتاج المستخدم إلى تسجيل الخروج والدخول لتفعيل PATH.',
            'severity': 'low',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'سجل الخروج والدخول مرة أخرى أو أضف ~/.local/bin إلى PATH.',
        })

    return issues, repairs


def ansible_repair(issue, use_sudo=False):
    """تنفيذ إصلاح واحد لمشكلة أنsible."""
    fix_cmd = issue.get('fix_command')
    if not fix_cmd:
        return False, 'لا يوجد أمر إصلاح تلقائي لهذه المشكلة.'
    try:
        run_step(fix_cmd)
        return True, 'تم التنفيذ بنجاح.'
    except Exception as exc:
        return False, str(exc)
