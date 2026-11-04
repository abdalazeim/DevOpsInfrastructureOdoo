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
IMAGE = 'portainer/portainer-ce'

PORT_ISSUE_PORT_9000 = 'port_9000_in_use'
PORT_ISSUE_PORT_8000 = 'port_8000_in_use'
ISSUE_DOCKER_MISSING = 'docker_missing'
ISSUE_CONTAINER_NOT_RUNNING = 'container_not_running'
ISSUE_BIND_MOUNT_MISSING = 'bind_mount_missing'


def portainer_diagnose(use_sudo=False):
    """تشخيص أخطاء Portainer المحتملة وقائمة بالإصلاحات المقترحة."""
    issues = []
    repairs = []

    if not shutil.which('docker'):
        issues.append({
            'id': ISSUE_DOCKER_MISSING,
            'component': 'Portainer',
            'title': 'Docker Engine غير مثبت',
            'description': 'لا يمكن تشغيل Portainer دون Docker Engine.',
            'severity': 'critical',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'ثبت Docker Engine أولاً عبر القائمة.',
        })
        return issues, repairs

    report = inspect_portainer(use_sudo=use_sudo)

    if report['status'] == 'error':
        issues.append({
            'id': 'portainer_daemon_error',
            'component': 'Portainer',
            'title': 'خطأ في التواصل مع Docker daemon',
            'description': report.get('error', 'غير معلوم'),
            'severity': 'critical',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'تحقق من تشغيل Docker وصلاحيات المستخدم.',
        })
        return issues, repairs

    if report['status'] == 'conflict':
        issues.append({
            'id': 'portainer_name_conflict',
            'component': 'Portainer',
            'title': 'تضارب باسم الحاوية portainer',
            'description': 'اسم portainer مستخدم من حاوية أخرى.',
            'severity': 'high',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'غير اسم الحاوية الأخرى أو احذفها قبل التثبيت.',
        })
        return issues, repairs

    if report['status'] == 'installed':
        for c in report['containers']:
            status = c.get('Status', '')
            if 'Exited' in status or 'Created' in status:
                issues.append({
                    'id': 'portainer_container_not_running',
                    'component': 'Portainer',
                    'title': 'حاوية Portainer غير عاملة',
                    'description': f"حالة الحاوية: {status}",
                    'severity': 'high',
                    'auto_fix': True,
                    'fix_command': ['docker', 'start', 'portainer'],
                    'fix_description': 'تشغيل حاوية Portainer المتوقفة.',
                })
                repairs.append(('تشغيل حاوية Portainer', ['docker', 'start', 'portainer']))
            break

    # فحص المنافذ
    for port, issue_id, title in ((9000, PORT_ISSUE_PORT_9000, 'المنفذ 9000 مستخدم'),
                                   (8000, PORT_ISSUE_PORT_8000, 'المنفذ 8000 مستخدم')):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            if s.connect_ex(('127.0.0.1', port)) == 0:
                issues.append({
                    'id': issue_id,
                    'component': 'Portainer',
                    'title': title,
                    'description': f'المنفذ {port} مرتبط بعملية أخرى.',
                    'severity': 'medium',
                    'auto_fix': False,
                    'fix_command': None,
                    'fix_description': 'أوقف الخدمة القائمة على المنفذ أو اختر منفذاً آخر.',
                })

    # فحص مجلد البيانات
    if not os.path.exists('/srv/portainer'):
        issues.append({
            'id': 'portainer_bind_mount_missing',
            'component': 'Portainer',
            'title': 'مجلد البيانات /srv/portainer غير موجود',
            'description': 'سينشئ المثبت المجلد تلقائياً.',
            'severity': 'low',
            'auto_fix': True,
            'fix_command': ['mkdir', '-p', '/srv/portainer'],
            'fix_description': 'إنشاء مجلد البيانات لنجاح الربط.',
        })
        repairs.append(('إنشاء مجلد /srv/portainer', ['mkdir', '-p', '/srv/portainer']))

    return issues, repairs


def portainer_repair(issue, use_sudo=False):
    """تنفيذ إصلاح واحد لمشكلة Portainer."""
    fix_cmd = issue.get('fix_command')
    if not fix_cmd:
        return False, 'لا يوجد أمر إصلاح تلقائي لهذه المشكلة.'
    docker = docker_command(use_sudo)
    prefix = docker[:-len(DOCKER)]
    full_cmd = prefix + fix_cmd if fix_cmd[0] != 'docker' else fix_cmd
    try:
        run_step(full_cmd)
        return True, 'تم التنفيذ بنجاح.'
    except Exception as exc:
        return False, str(exc)


def docker_command(use_sudo=False):
    return (['sudo', '-n'] if use_sudo and not (hasattr(os, 'geteuid') and os.geteuid() == 0) else []) + DOCKER


def inspect_portainer(use_sudo=False):
    if not shutil.which('docker'):
        return {'status': 'docker_missing', 'containers': [], 'error': 'جهّز Docker Engine أولًا.'}
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
        return {'status': 'error', 'containers': [], 'error': 'تعذر قراءة استجابة Docker.'}
    return {'status': 'conflict' if collision else 'installed' if containers else 'missing',
            'containers': containers, 'error': ''}


def build_plan(port=9000, edge=True, use_sudo=False):
    if type(port) is not int or not 1 <= port <= 65535 or (edge and port == 8000):
        raise ValueError('منفذ HTTP غير صالح أو يتعارض مع منفذ Edge 8000.')
    docker = docker_command(use_sudo)
    prefix = docker[:-len(DOCKER)]
    command = docker + ['run', '-d', '-p', f'{port}:9000']
    if edge:
        command += ['-p', '8000:8000']
    command += ['--name', 'portainer', '--restart=always',
                '-v', '/var/run/docker.sock:/var/run/docker.sock',
                '-v', '/srv/portainer:/data', IMAGE]
    return [prefix + ['mkdir', '-p', '/srv/portainer'], command]


def install_portainer(port=9000, edge=True, dry_run=False, use_sudo=False):
    try:
        commands = build_plan(port, edge, use_sudo)
        if dry_run:
            for command in commands:
                run_step(command, dry_run=True)
            return True
        if platform.system() != 'Linux':
            raise ValueError('هذا المثبت مخصص لمحرك Docker المحلي على Linux.')
        report = inspect_portainer(use_sudo=use_sudo)
        if report['status'] != 'missing':
            print('لم يُنفذ التثبيت: توجد حاوية أو تعارض أو تعذر الفحص. لن تتم إزالة حاوية قائمة.')
            print(report['error'])
            return False
        for candidate in ([port, 8000] if edge else [port]):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('0.0.0.0', candidate))
        for command in commands:
            run_step(command)
        code, state = probe(docker_command(use_sudo) + ['inspect', '--format', '{{.State.Status}}', 'portainer'])
        if code or state != 'running':
            print(f'أُنشئت الحاوية لكن لم يؤكد الفحص تشغيلها: {state}. راجع docker logs portainer.')
            return False
        run_step(docker_command(use_sudo) + ['ps', '-a'])
        print(f'حاوية Portainer تعمل. افتح http://<SERVER-IP>:{port} لإكمال الإعداد الأولي.')
        print('هذا تحقق من تشغيل الحاوية؛ جاهزية واجهة HTTP لم تُختبر بعد.')
        print('قد تحتاج إلى رمز الإعداد من sudo docker logs portainer.')
        return True
    except (OSError, ValueError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
        print(f'توقف تثبيت Portainer: {exc}. لم تُحذف بيانات أو حاويات قائمة؛ راجع المخرجات.')
        return False
