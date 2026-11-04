"""Jenkins CI/CD discovery and installation on the local Linux Docker Engine."""
import json
import os
import platform
import shutil
import socket
import subprocess

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
JENKINS_DOMAIN = 'jenkins.devops-odoo.com'
JENKINS_TIMEZONE = 'Africa/Tripoli'
JENKINS_CERTSRESOLVER = 'letsencrypt'


def docker_command(use_sudo=False):
    return (['sudo', '-n'] if use_sudo and not (hasattr(os, 'geteuid') and os.geteuid() == 0) else []) + DOCKER


def inspect_jenkins(use_sudo=False):
    """فحص حالة جينكينز على المحرك المحلي (مثبت / مفقود / تضارب / خطأ)."""
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
            image = item.get('Image', '')
            is_jenkins = image.startswith('jenkins/')
            if is_jenkins or item.get('Names') == JENKINS_CONTAINER:
                containers.append(item)
                collision |= not is_jenkins
    except (ValueError, AttributeError):
        return {'status': 'error', 'containers': [], 'error': 'تعذر قراءة استجابة Docker.'}
    return {'status': 'conflict' if collision else 'installed' if containers else 'missing',
            'containers': containers, 'error': ''}


def system_preflight_check():
    """فحص مسبق للنظام قبل التثبيت (نظام، دوكرب، شبكة، تخزين، ذاكرة)."""
    results = {}
    try:
        res = subprocess.run(['lsb_release', '-a'], capture_output=True, text=True, check=False)
        results['os'] = res.stdout.strip() or res.stderr.strip()
    except FileNotFoundError:
        results['os'] = 'lsb_release غير متوفر'
    for cmd in (['docker', '--version'], ['docker', 'compose', 'version']):
        code, out = probe(cmd)
        results[cmd[0]] = out if code == 0 else f'خطأ: {out}'
    code, out = probe(['docker', 'ps'])
    results['docker_ps'] = out if code == 0 else f'خطأ: {out}'
    code, out = probe(['docker', 'network', 'ls'])
    results['network_ls'] = out if code == 0 else f'خطأ: {out}'
    for path in ('/opt', '/data'):
        try:
            st = os.stat(path)
            results[path] = f'موجود (UID: {st.st_uid}, GID: {st.st_gid})'
        except FileNotFoundError:
            results[path] = 'غير موجود'
    try:
        total, used, free = shutil.disk_usage('/')
        results['disk'] = f'المجموع: {total // (2**30)} GB، المستخدم: {used // (2**30)} GB، الحر: {free // (2**30)} GB'
    except Exception as exc:
        results['disk'] = f'خطأ في قراءة القرص: {exc}'
    return results


def build_jenkins_plan(use_sudo=False, domain=None, certsresolver=None):
    """بناء خطة إعداد وتثبيت جينكينز (mkdir, compose up).
    لا يربط مقبس Docker تلقائيًا بأمان (تجنب صلاحيات واسعة على المضيف).
    """
    domain = domain or JENKINS_DOMAIN
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
        f"      - {JENKINS_HOST_DATA_DIR}:{JENKINS_DIR}\n"
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


def _write_file(path, content, use_sudo=False):
    docker = docker_command(use_sudo)
    prefix = docker[:-len(DOCKER)]
    run_step(prefix + ['tee', path], content=content)


def install_jenkins(dry_run=False, use_sudo=False, domain=None, certsresolver=None):
    """تنصيب جينكينز إن لم يكن مثبتًا. إذا مثبت أو هناك تضارب، لا يُنفذ أي تغيير."""
    try:
        if platform.system() != 'Linux':
            raise ValueError('هذا المثبت مخصص لنظام Linux.')
        report = inspect_jenkins(use_sudo=use_sudo)
        if report['status'] == 'installed':
            print(f'جينكينز مثبت بالفعل. حالة الحاوية موضحة أعلاه. لن يعاد التثبيت.')
            return True
        if report['status'] == 'conflict':
            print('اسم jenkins مستخدم من حاوية أخرى. لم تُجرَ تغييرات.')
            return False
        if report['status'] == 'error':
            print(report['error'])
            return False

        for candidate in (JENKINS_HTTP_PORT, JENKINS_AGENT_PORT):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('0.0.0.0', candidate))

        if dry_run:
            print(f'[DRY-RUN] سيُنشئ المجلدات: {JENKINS_HOST_DATA_DIR}, {JENKINS_HOST_CONFIG_DIR}')
            print(f'[DRY-RUN] سيتم ضبط المالك: 1000:1000 على {JENKINS_HOST_DATA_DIR}')
            print(f'[DRY-RUN] سيتم كتابة ملف الإعدادات: {JENKINS_HOST_CONFIG_DIR}/docker-compose.yml')
            print(f'[DRY-RUN] سيتم التحقق من شبكة {JENKINS_NETWORK} وإنشاؤها إن لم تكن موجودة')
            print(f'[DRY-RUN] سيتم تشغيل docker compose up -d باستخدام الصورة {IMAGE}')
            print(f'[DRY-RUN] النطاق: {domain or JENKINS_DOMAIN} | مثبت الشهادة: {certsresolver or JENKINS_CERTSRESOLVER}')
            print(f'[DRY-RUN] الوصول عبر Traefik فقط (HTTPS)، لن يُنشر المنفذ 8080 للعامة')
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
            print(f'أُنشئت الحاوية لكن الفحص لم يؤكد تشغيلها: {state}. راجع docker logs jenkins.')
            return False
        run_step(docker_command(use_sudo) + ['ps', '-a'])
        print(f'حاوية جينكينز تعمل. الوصول عبر Traefik: https://{domain or JENKINS_DOMAIN}')
        print(f'بيانات جينكينز: {JENKINS_HOST_DATA_DIR}')
        print(f'ملف الإعدادات: {JENKINS_HOST_CONFIG_DIR}/docker-compose.yml')
        print('كلمة مرور المسؤول الأولية: sudo docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword')
        print('ملاحظة: مقبس Docker غير مرتبط بالحاوية لأسباب أمنية. استخدم وكيل بناء خارجي إذا لزم الأمر.')
        return True
    except (OSError, ValueError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
        print(f'توقف تثبيت جينكينز: {exc}. لم تُحذف بيانات أو حاويات قائمة؛ راجع المخرجات.')
        return False


JENKINS_ISSUE_NOT_INSTALLED = 'jenkins_not_installed'
JENKINS_ISSUE_PORT_8080 = 'jenkins_port_8080_in_use'
JENKINS_ISSUE_PORT_50000 = 'jenkins_port_50000_in_use'
JENKINS_ISSUE_CONTAINER_NOT_RUNNING = 'jenkins_container_not_running'
JENKINS_ISSUE_DATA_DIR_MISSING = 'jenkins_data_dir_missing'


def jenkins_diagnose(use_sudo=False):
    """تشخيص أخطاء جينكينز المحتملة وقائمة بالإصلاحات المقترحة."""
    issues = []
    repairs = []

    if not shutil.which('docker'):
        issues.append({
            'id': 'jenkins_docker_missing',
            'component': 'Jenkins',
            'title': 'Docker Engine غير مثبت',
            'description': 'لا يمكن تشغيل جينكينز دون Docker Engine.',
            'severity': 'critical',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'ثبت Docker Engine أولاً عبر القائمة.',
        })
        return issues, repairs

    report = inspect_jenkins(use_sudo=use_sudo)

    if report['status'] == 'error':
        issues.append({
            'id': 'jenkins_daemon_error',
            'component': 'Jenkins',
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
            'id': 'jenkins_name_conflict',
            'component': 'Jenkins',
            'title': 'تضارب باسم الحاوية jenkins',
            'description': 'اسم jenkins مستخدم من حاوية أخرى.',
            'severity': 'high',
            'auto_fix': False,
            'fix_command': None,
            'fix_description': 'غير اسم الحاوية الأخرى أو احذفها قبل التثبيت.',
        })
        return issues, repairs

    # فحص المنافذ
    for port, issue_id, title, desc in (
        (JENKINS_HTTP_PORT, JENKINS_ISSUE_PORT_8080, 'المنفذ 8080 (Jenkins HTTP) مستخدم', 'المنفذ 8080 مرتبط بعملية أخرى.'),
        (JENKINS_AGENT_PORT, JENKINS_ISSUE_PORT_50000, 'المنفذ 50000 (Jenkins Agent) مستخدم', 'المنفذ 50000 مرتبط بعملية أخرى.'),
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
                    'fix_description': 'أوقف الخدمة القائمة على المنفذ أو اختر منفذاً آخر.',
                })

    # فحص مجلد البيانات
    if not os.path.exists(JENKINS_HOST_DATA_DIR):
        issues.append({
            'id': JENKINS_ISSUE_DATA_DIR_MISSING,
            'component': 'Jenkins',
            'title': 'مجلد بيانات جينكينز غير موجود',
            'description': f'المجلد {JENKINS_HOST_DATA_DIR} غير موجود.',
            'severity': 'medium',
            'auto_fix': True,
            'fix_command': ['mkdir', '-p', JENKINS_HOST_DATA_DIR],
            'fix_description': f'إنشاء مجلد {JENKINS_HOST_DATA_DIR}.',
        })
        repairs.append((f'إنشاء مجلد {JENKINS_HOST_DATA_DIR}', ['mkdir', '-p', JENKINS_HOST_DATA_DIR]))

    # فحص حالة الحاوية
    if report['status'] == 'installed':
        for c in report['containers']:
            status = c.get('Status', '')
            if 'Exited' in status or 'Created' in status:
                issues.append({
                    'id': JENKINS_ISSUE_CONTAINER_NOT_RUNNING,
                    'component': 'Jenkins',
                    'title': 'حاوية جينكينز غير عاملة',
                    'description': f"حالة الحاوية: {status}",
                    'severity': 'high',
                    'auto_fix': True,
                    'fix_command': ['start', 'jenkins'],
                    'fix_description': 'تشغيل حاوية جينكينز المتوقفة.',
                })
                repairs.append(('تشغيل حاوية جينكينز', ['docker', 'start', 'jenkins']))
            break

    return issues, repairs


def jenkins_repair(issue, use_sudo=False):
    """تنفيذ إصلاح واحد لمشكلة جينكينز."""
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
