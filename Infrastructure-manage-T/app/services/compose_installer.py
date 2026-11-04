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
        return {'status': 'docker_missing', 'path': '', 'details': 'عميل Docker غير موجود في PATH؛ جهّز Docker Engine أولًا.'}
    code, output = probe([docker, 'compose', 'version'])
    return {'status': 'installed' if code == 0 and output else 'unavailable',
            'path': docker, 'details': output or 'لم يرجع الأمر إصدارًا؛ الإضافة غير متاحة أو تعذر تشغيلها.'}


def install_compose(dry_run=False):
    report = inspect_compose()
    if report['status'] == 'installed':
        print(f"الإضافة مثبتة بالفعل: {report['details']}")
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
            raise ValueError('هذا المسار مخصص لـ Ubuntu.')
        for command in commands:
            run_step(command, dry_run=dry_run)
        if not dry_run:
            verified = inspect_compose()
            if verified['status'] != 'installed':
                print(f"لم ينجح التحقق بعد التثبيت: {verified['details']}")
                return False
            print(f"تم تثبيت الإضافة والتحقق منها: {verified['details']}")
        return True
    except (OSError, ValueError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
        print(f'توقف تثبيت Compose: {exc}. راجع توفر مستودع Docker الرسمي ومخرجات apt.')
        return False
