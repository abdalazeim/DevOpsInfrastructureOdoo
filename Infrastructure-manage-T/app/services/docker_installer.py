"""Install the local Ubuntu Engine using Docker's official apt repository."""
import os
import platform
import re
import subprocess

CONFLICTS = ('docker.io', 'docker-compose', 'docker-compose-v2', 'docker-doc',
             'docker-buildx', 'podman-docker', 'containerd', 'runc')


def installed_conflicts():
    result = subprocess.run(['dpkg', '--get-selections'], capture_output=True, text=True, check=True)
    return [parts[0] for line in result.stdout.splitlines()
            if len(parts := line.split()) == 2 and parts[1] in ('install', 'hold')
            and parts[0].split(':')[0] in CONFLICTS]


def repository_plan(codename, architecture, conflicts=(), privileged=False):
    if not re.fullmatch(r'[a-z][a-z0-9]*', codename) or not re.fullmatch(r'[a-z0-9]+', architecture):
        raise ValueError('Invalid Ubuntu codename or architecture')
    if any(package.split(':')[0] not in CONFLICTS for package in conflicts):
        raise ValueError('Unexpected conflicting package')
    prefix = [] if privileged else ['sudo']
    steps = []
    if conflicts:
        # Keep apt's removal confirmation visible, including dependency removals.
        steps.append((prefix + ['apt-get', 'remove', *conflicts], None))
    steps += [(prefix + command, None) for command in (
        ['apt-get', 'update'], ['apt-get', 'install', '-y', 'ca-certificates', 'curl'],
        ['install', '-m', '0755', '-d', '/etc/apt/keyrings'],
        ['curl', '-fsSL', 'https://download.docker.com/linux/ubuntu/gpg', '-o', '/etc/apt/keyrings/docker.asc'],
        ['chmod', 'a+r', '/etc/apt/keyrings/docker.asc'],
    )]
    source = ('Types: deb\nURIs: https://download.docker.com/linux/ubuntu\n'
              f'Suites: {codename}\nComponents: stable\nArchitectures: {architecture}\n'
              'Signed-By: /etc/apt/keyrings/docker.asc\n')
    steps += [(prefix + ['tee', '/etc/apt/sources.list.d/docker.sources'], source),
              (prefix + ['apt-get', 'update'], None)]
    return steps


def package_command(version='', privileged=False):
    if version and not re.fullmatch(r'[0-9][A-Za-z0-9.+:~_-]*', version):
        raise ValueError('Invalid Docker package version')
    suffix = f'={version}' if version else ''
    return ([] if privileged else ['sudo']) + [
        'apt-get', 'install', '-y', f'docker-ce{suffix}', f'docker-ce-cli{suffix}',
        'containerd.io', 'docker-buildx-plugin', 'docker-compose-plugin']


def run_step(command, content=None, dry_run=False):
    print(('** معاينة ** ' if dry_run else '==> ') + ' '.join(command), flush=True)
    if content:
        print(content)
    if not dry_run:
        subprocess.run(command, input=content, text=True, check=True)


def install_docker(dry_run=False, choose_version=False, hello_world=False, group_user=''):
    """Returns False on failure/cancellation; never switches the active Docker context."""
    try:
        privileged = hasattr(os, 'geteuid') and os.geteuid() == 0
        prefix = [] if privileged else ['sudo']
        if group_user and not re.fullmatch(r'[a-z_][a-z0-9_-]*[$]?', group_user):
            raise ValueError('اسم المستخدم غير صالح')
        release = platform.freedesktop_os_release()
        if release.get('ID') != 'ubuntu':
            raise ValueError('التثبيت المباشر متاح على Ubuntu فقط.')
        codename = release.get('UBUNTU_CODENAME') or release.get('VERSION_CODENAME', '')
        architecture = subprocess.run(['dpkg', '--print-architecture'], capture_output=True,
                                      text=True, check=True).stdout.strip()
        conflicts = installed_conflicts()
        steps = repository_plan(codename, architecture, conflicts, privileged)
        print('الحزم المتعارضة المكتشفة: ' + (', '.join(conflicts) or 'لا توجد'))
        if conflicts:
            print('إزالة الحزم قد توقف خدمات تستخدمها. سيعرض apt تفاصيل الإزالة ويطلب التأكيد.')
        for command, content in steps:
            run_step(command, content, dry_run=True)
        run_step(package_command(privileged=privileged), dry_run=True)
        print('بعد التثبيت: تشغيل الخدمة والتحقق من المحرك المحلي وCompose وBuildx.')
        if dry_run:
            if choose_version:
                print('سيتم عرض الإصدارات المتاحة واختيار إصدار لكل من docker-ce وdocker-ce-cli بعد إعداد المستودع.')
            if hello_world:
                print('اختبار hello-world: مفعّل')
            if group_user:
                print(f'إضافة المستخدم إلى docker: {group_user}')
            return True
        if input('تنفيذ خطة التثبيت على هذا الجهاز؟ [y/N]: ').strip().lower() != 'y':
            return False
        for command, content in steps:
            run_step(command, content)
        version = ''
        if choose_version:
            available = []
            for package in ('docker-ce', 'docker-ce-cli'):
                result = subprocess.run(['apt-cache', 'madison', package], capture_output=True,
                                        text=True, check=True)
                available.append({line.split('|')[1].strip() for line in result.stdout.splitlines() if '|' in line})
            versions = sorted(available[0] & available[1], reverse=True)
            if not versions:
                raise ValueError('لا توجد إصدارات مشتركة للمحرك والعميل في المستودع.')
            print('\n'.join(versions))
            version = input('انسخ VERSION_STRING المطلوب، أو 0 للإلغاء: ').strip()
            if version not in versions:
                print('ألغي تثبيت الحزم؛ إعداد المستودع تم بالفعل.')
                return False
        run_step(package_command(version, privileged))
        run_step(prefix + ['systemctl', 'start', 'docker'])
        run_step(prefix + ['systemctl', '--no-pager', '--full', 'status', 'docker'])
        # Explicit local socket prevents verification or hello-world on a remote context.
        docker = prefix + ['docker', '--host', 'unix:///var/run/docker.sock']
        run_step(docker + ['info'])
        run_step(docker + ['compose', 'version'])
        run_step(docker + ['buildx', 'version'])
        if hello_world:
            run_step(docker + ['run', '--rm', 'hello-world'])
        if group_user:
            run_step(prefix + ['usermod', '-aG', 'docker', group_user])
            print('سجل الخروج ثم الدخول لتفعيل عضوية المجموعة.')
        print('اكتمل تثبيت Docker Engine والتحقق من المحرك المحلي والإضافات.')
        return True
    except (OSError, ValueError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
        print(f'توقف التثبيت: {exc}. قد تكون بعض الخطوات نُفذت؛ راجع المخرجات.')
        return False
