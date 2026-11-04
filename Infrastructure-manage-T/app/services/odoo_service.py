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
    """فحص حالة إصدار أودو معين (مثبت / مفقود / تضارب / خطأ)."""
    if version not in ODOO_VERSIONS:
        return {'status': 'error', 'containers': [], 'error': f'إصدار غير مدعوم: {version}'}
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
            names = item.get('Names', '')
            image = item.get('Image', '')
            is_odoo = f'odoo{version}' in names or image.startswith(ODOO_IMAGES[version])
            is_db = f'odoo{version}-db' in names or image.startswith(PG_IMAGES[version])
            if is_odoo or is_db:
                containers.append(item)
                collision |= not (is_odoo or is_db)
    except (ValueError, AttributeError):
        return {'status': 'error', 'containers': [], 'error': 'تعذر قراءة استجابة Docker.'}
    return {'status': 'conflict' if collision else 'installed' if containers else 'missing',
            'containers': containers, 'error': ''}


def odoo_diagnose(version: str, use_sudo=False):
    """تشخيص أخطاء أودو المحتملة وقائمة بالإصلاحات المقترحة."""
    issues = []
    repairs = []

    if version not in ODOO_VERSIONS:
        issues.append({
            'id': 'odoo_invalid_version',
            'component': f'Odoo {version}',
            'title': 'إصدار أودو غير مدعوم',
            'description': f'الإصدار {version} غير مدعوم. الإصدارات المدعومة: 17، 18، 19.',
            'severity': 'critical',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'اختر إصداراً مدعوماً (17 أو 18 أو 19).',
        })
        return issues, repairs

    if not shutil.which('docker'):
        issues.append({
            'id': f'odoo{version}_docker_missing',
            'component': f'Odoo {version}',
            'title': 'Docker Engine غير مثبت',
            'description': 'لا يمكن تشغيل أودو دون Docker Engine.',
            'severity': 'critical',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'ثبت Docker Engine أولاً عبر القائمة.',
        })
        return issues, repairs

    report = inspect_odoo(version, use_sudo=use_sudo)

    if report['status'] == 'error':
        issues.append({
            'id': f'odoo{version}_daemon_error',
            'component': f'Odoo {version}',
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
            'id': f'odoo{version}_name_conflict',
            'component': f'Odoo {version}',
            'title': 'تضارب باسم حاوية أودو',
            'description': f'اسم حاوية odoo{version} أو odoo{version}-db مستخدم من حاوية أخرى.',
            'severity': 'high',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'غير اسم الحاوية الأخرى أو احذفها قبل التثبيت.',
        })
        return issues, repairs

    # فحص حالة الحاويات
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
                    'title': f'حاوية PostgreSQL {PG_IMAGES[version].split(":")[1]} غير عاملة',
                    'description': f"حالة الحاوية: {status}",
                    'severity': 'high',
                    'auto_fix': True,
                    'fix_command': ['start', f'odoo{version}-db'],
                    'fix_description': f'تشغيل حاوية قاعدة بيانات أودو {version}.',
                })
                repairs.append((f'تشغيل قاعدة بيانات أودو {version}', ['docker', 'start', f'odoo{version}-db']))
            else:
                db_running = True
        if f'odoo{version}' in names and '-db' not in names:
            if 'Exited' in status or 'Created' in status:
                issues.append({
                    'id': f'odoo{version}_container_not_running',
                    'component': f'Odoo {version}',
                    'title': f'حاوية أودو {version} غير عاملة',
                    'description': f"حالة الحاوية: {status}",
                    'severity': 'high',
                    'auto_fix': True,
                    'fix_command': ['start', f'odoo{version}'],
                    'fix_description': f'تشغيل حاوية أودو {version}.',
                })
                repairs.append((f'تشغيل أودو {version}', ['docker', 'start', f'odoo{version}']))
            else:
                odoo_running = True

    # فحص المنافذ
    http_port = ODOO_HTTP_PORTS[version]
    chat_port = ODOO_CHAT_PORTS[version]
    for port, issue_id, title, desc in (
        (http_port, f'odoo{version}_port_http_in_use', f'المنفذ {http_port} (Odoo HTTP) مستخدم', f'المنفذ {http_port} مرتبط بعملية أخرى.'),
        (chat_port, f'odoo{version}_port_chat_in_use', f'المنفذ {chat_port} (Odoo Livechat) مستخدم', f'المنفذ {chat_port} مرتبط بعملية أخرى.'),
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
                    'fix_description': 'أوقف الخدمة القائمة على المنفذ أو اختر منفذاً آخر.',
                })

    # فحص مجلد المثبت
    destination = f'/opt/odoo-infrastructure/odoo{version}'
    if not os.path.exists(destination):
        issues.append({
            'id': f'odoo{version}_dir_missing',
            'component': f'Odoo {version}',
            'title': f'مجلد تثبيت أودو {version} غير موجود',
            'description': f'المجلد {destination} غير موجود.',
            'severity': 'medium',
            'auto_fix': True,
            'fix_command': ['mkdir', '-p', destination],
            'fix_description': f'إنشاء مجلد التثبيت {destination}.',
        })
        repairs.append((f'إنشاء مجلد {destination}', ['mkdir', '-p', destination]))

    # فحص ملف .env
    env_file = f'{destination}/.env'
    if os.path.exists(destination) and not os.path.exists(env_file):
        issues.append({
            'id': f'odoo{version}_env_missing',
            'component': f'Odoo {version}',
            'title': f'ملف .env لأودو {version} غير موجود',
            'description': 'ملف الإعدادات(instance .env) غير موجود، يحتاج إلى إعادة التكوين.',
            'severity': 'medium',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'أعد تشغيل تثبيت أودو لإنشاء ملف الإعدادات.',
        })

    return issues, repairs


def odoo_repair(issue: Dict, use_sudo=False):
    """تنفيذ إصلاح واحد لمشكلة أودو."""
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


def build_odoo_install_plan(profile, version: str, use_sudo=False, with_traefik: bool = False):
    """بناء خطة تثبيت أودو (تشغيل install-odoo.sh)."""
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
    """تنصيب إصدار أودو إن لم يكن مثبتًا. إذا مثبت، لا يُنفذ أي تغيير."""
    try:
        if platform.system() != 'Linux':
            raise ValueError('هذا المثبت مخصص لنظام Linux.')
        if version not in ODOO_VERSIONS:
            raise ValueError(f'إصدار غير مدعوم: {version}')

        report = inspect_odoo(version, use_sudo=use_sudo)
        if report['status'] == 'installed':
            print(f'أودو {version} مثبت بالفعل. حالة الحاويات موضحة أعلاه. لن يعاد التثبيت.')
            return True
        if report['status'] == 'conflict':
            print(f'اسم حاوية أودو {version} مستخدم من حاوية أخرى. لم تُجرَ تغييرات.')
            return False
        if report['status'] == 'error':
            print(report['error'])
            return False

        # فحص المنافذ قبل التثبيت
        http_port = ODOO_HTTP_PORTS[version]
        chat_port = ODOO_CHAT_PORTS[version]
        for port in (http_port, chat_port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('0.0.0.0', port))

        if dry_run:
            print(f'[DRY-RUN] سيُثبت أودو {version} مع PostgreSQL {PG_IMAGES[version].split(":")[1]}')
            print(f'[DRY-RUN] المجلد: {profile.paths.data_root}/odoo{version}')
            print(f'[DRY-RUN] المنفذ HTTP: {http_port} | منفذ الدردشة: {chat_port}')
            print(f'[DRY-RUN] شبكة داخلية: {ODOO_INTERNAL_NETWORKS[version]}')
            print(f'[DRY-RUN] مع ترافيك: {"نعم" if with_traefik else "لا"}')
            return True

        commands = build_odoo_install_plan(profile, version, use_sudo=use_sudo, with_traefik=with_traefik)
        for command in commands:
            run_step(command)

        # التحقق من حالة الحاويات بعد التثبيت
        code, state = probe(docker_command(use_sudo) + ['inspect', '--format', '{{.State.Status}}', f'odoo{version}'])
        if code or state != 'running':
            print(f'تم إنشاء حاوية أودو {version} لكنها ليست في حالة running: {state}. راجع السجلات.')
            return False
        code, db_state = probe(docker_command(use_sudo) + ['inspect', '--format', '{{.State.Status}}', f'odoo{version}-db'])
        if code or db_state != 'running':
            print(f'تم إنشاء حاوية قاعدة بيانات أودو {version} لكنها ليست في حالة running: {db_state}. راجع السجلات.')
            return False

        run_step(docker_command(use_sudo) + ['ps', '-a'])
        print(f'أودو {version} يعمل بنجاح مع PostgreSQL {PG_IMAGES[version].split(":")[1]}.')
        print(f'العنوان: http://localhost:{http_port} (أو عبر ترافيك على HTTPS)')
        print(f'البيانات: {profile.paths.data_root}/odoo{version}/postgresql')
        print(f'الإعدادات: {profile.paths.data_root}/odoo{version}/etc/odoo.conf')
        return True
    except (OSError, ValueError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
        print(f'توقف تثبيت أودو {version}: {exc}. لم تُحذف بيانات أو حاويات قائمة؛ راجع المخرجات.')
        return False
