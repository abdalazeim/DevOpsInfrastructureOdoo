"""Portable, checked Docker database/filestore backup and restore contract.

This module is also copied as a standalone script by Ansible. No project imports.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


def identifier(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}', value):
        raise ValueError('Invalid identifier: ' + value)
    return value


def docker(*args, **kwargs):
    return subprocess.run(['docker', *args], check=True, timeout=600, **kwargs)


def inspect(name):
    return json.loads(docker('inspect', name, capture_output=True, text=True).stdout)[0]


def environment(info):
    return dict(entry.split('=', 1) for entry in info['Config'].get('Env', []) if '=' in entry)


def digest(path):
    with path.open('rb') as stream:
        checksum = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(block)
        return checksum.hexdigest()


def private_json(path, value):
    with path.open('w', encoding='utf-8') as stream:
        os.chmod(path, 0o600)
        json.dump(value, stream, indent=2)


def dump(db, user, database, destination):
    with destination.open('wb') as stream:
        os.chmod(destination, 0o600)
        docker('exec', db, 'pg_dump', '-U', user, '-d', database,
               '--no-owner', '--no-privileges', stdout=stream)
    if not destination.stat().st_size:
        raise RuntimeError('Database dump is empty')


def backup(version, instance, root, app_name=None, db_name=None):
    identifier(version); identifier(instance)
    app_name = app_name or f'{version}-{instance}'
    db_name = db_name or app_name + '-db'
    app, db = inspect(app_name), inspect(db_name)
    if not db['State'].get('Running'):
        raise RuntimeError('PostgreSQL must be running for a logical backup')
    env = environment(db)
    user = env.get('POSTGRES_USER', 'postgres')
    database = env.get('POSTGRES_DB') or user
    identifier(database)
    backup_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    path = Path(root).resolve() / version / instance / backup_id
    path.mkdir(parents=True, mode=0o700)
    os.chmod(path, 0o700)
    stopped = bool(app['State'].get('Running'))
    try:
        if stopped:
            docker('stop', app_name)
        dump(db_name, user, database, path / 'database.sql')
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            # docker cp works for stopped containers and named volumes as well as binds.
            docker('cp', f'{app_name}:/var/lib/odoo', str(temp / 'odoo-data'))
            source = temp / 'odoo-data' / 'filestore' / database
            source.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, temp / database)
            with tarfile.open(path / 'filestore.tar.gz', 'w:gz') as archive:
                archive.add(temp / database, arcname=database)
            docker('cp', f'{app_name}:/etc/odoo', str(temp / 'etc'))
            docker('cp', f'{app_name}:/mnt/extra-addons', str(temp / 'addons'))
            with tarfile.open(path / 'config.tar.gz', 'w:gz') as archive:
                archive.add(temp / 'etc', arcname='etc')
                archive.add(temp / 'addons', arcname='addons')
        private_json(path / 'containers.json', {'odoo': app, 'db': db})
        files = {p.name: digest(p) for p in path.iterdir() if p.is_file()}
        for file in path.iterdir():
            os.chmod(file, 0o600)
        private_json(path / 'manifest.json', {'format': 1, 'backup_id': backup_id,
            'version': version, 'instance': instance, 'database': database, 'db_user': user,
            'files': files, 'status': 'completed'})
        print(str(path))
        return path
    except Exception:
        # Keep incomplete evidence, never mark it completed or offer it for restore.
        (path / 'INCOMPLETE').touch()
        raise
    finally:
        if stopped:
            docker('start', app_name)


def load_verified(path):
    path = Path(path).resolve()
    manifest = json.loads((path / 'manifest.json').read_text())
    if manifest.get('format') != 1 or manifest.get('status') != 'completed' or (path / 'INCOMPLETE').exists():
        raise ValueError('Incomplete or unsupported backup format')
    required = {'database.sql', 'filestore.tar.gz', 'config.tar.gz', 'containers.json'}
    if not required.issubset(manifest.get('files', {})):
        raise ValueError('Backup manifest is missing required files')
    for name, expected in manifest['files'].items():
        if Path(name).name != name or '\\' in name:
            raise ValueError('Unsafe backup member')
        file = path / name
        if file.is_symlink() or not file.is_file() or digest(file) != expected:
            raise ValueError('Backup checksum mismatch: ' + name)
    identifier(manifest['database'])
    return manifest


def extract(archive_path, target):
    with tarfile.open(archive_path, 'r:gz') as archive:
        for member in archive.getmembers():
            candidate = (Path(target) / member.name).resolve()
            if not candidate.is_relative_to(Path(target).resolve()) or not (member.isfile() or member.isdir()):
                raise ValueError('Unsafe archive member')
        try:
            archive.extractall(target, filter='data')
        except TypeError:  # Python 3.10; members already validated above
            archive.extractall(target)


def clone(spec, name, source_app, target_app, port=None, domain=None):
    """Create isolated new volumes; never reattach the source's data mounts."""
    if subprocess.run(['docker', 'inspect', name], capture_output=True).returncode == 0:
        raise ValueError('New instance container already exists: ' + name)
    args = ['create', '--name', name, '--restart', 'unless-stopped']
    for entry in spec['Config'].get('Env', []):
        key, _, value = entry.partition('=')
        if key in ('HOST', 'PGHOST', 'DB_HOST'):
            value = target_app + '-db'
        args += ['-e', key + '=' + value]
    for mount in spec.get('Mounts', []):
        destination = mount['Destination']
        if destination == '/var/run/docker.sock':
            raise ValueError('Refusing a database/app backup with Docker socket access')
        # Configuration is restored via docker cp; data is always a fresh named volume.
        if destination in ('/etc/odoo', '/etc/odoo/odoo.conf', '/mnt/extra-addons'):
            continue
        volume = name + '-' + re.sub(r'[^a-zA-Z0-9]', '-', destination)
        docker('volume', 'create', volume)
        args += ['-v', volume + ':' + destination]
    if name == target_app:
        if port:
            if not 1024 <= int(port) <= 65535:
                raise ValueError('Restore HTTP port must be in 1024..65535')
            args += ['-p', f'{port}:8069']
        if domain:
            if not re.fullmatch(r'[A-Za-z0-9.-]+', domain):
                raise ValueError('Invalid restore domain')
            for key, value in (spec['Config'].get('Labels') or {}).items():
                if not key.startswith('traefik.'):
                    continue
                key = key.replace(source_app, target_app)
                value = value.replace(source_app, target_app)
                value = re.sub(r'Host\(`[^`]+`\)', f'Host(`{domain}`)', value)
                args += ['--label', key + '=' + value]
    args += ['--network', target_app + '-internal', spec['Config']['Image']]
    args += spec['Config'].get('Cmd') or []
    docker(*args)


def restore(path, root, new_instance=None, http_port=None, domain=None, confirm_replace=False):
    if not new_instance and not confirm_replace:
        raise ValueError("Existing database replacement requires --confirm-replace")
    path = Path(path).resolve()
    manifest = load_verified(path)  # no writes or stops before verification
    specs = json.loads((path / 'containers.json').read_text())
    source = specs['odoo']['Name'].lstrip('/')
    target = source
    user, database = manifest['db_user'], manifest['database']
    if new_instance:
        identifier(new_instance)
        target = manifest['version'] + '-' + new_instance
        if target == source:
            raise ValueError('New instance must differ from source')
        if not http_port and not domain:
            raise ValueError('New instance requires --http-port or --domain')
        docker('network', 'create', target + '-internal')
        clone(specs['db'], target + '-db', source, target)
        clone(specs['odoo'], target, source, target, http_port, domain)
        if domain:
            network = specs['odoo']['Config'].get('Labels', {}).get('traefik.docker.network', 'proxy')
            docker('network', 'connect', network, target)
    else:
        # A verified logical backup and matching filestore are mandatory before replacement.
        backup(manifest['version'], manifest['instance'], Path(root) / 'safety', target, target + '-db')
    app = inspect(target)
    was_running = bool(app['State'].get('Running'))
    if was_running:
        docker('stop', target)
    try:
        docker('start', target + '-db')
        for attempt in range(60):
            if subprocess.run(['docker', 'exec', target + '-db', 'pg_isready', '-U', user], capture_output=True).returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError('PostgreSQL readiness timed out')
        # Existing database connections are terminated before replacement.
        docker('exec', target + '-db', 'dropdb', '-U', user, '--if-exists', '--force', database)
        docker('exec', target + '-db', 'createdb', '-U', user, '-E', 'UTF8', database)
        with (path / 'database.sql').open('rb') as stream:
            docker('exec', '-i', target + '-db', 'psql', '-U', user, '-d', database,
                   '-v', 'ON_ERROR_STOP=1', stdin=stream)
        docker('start', target)
        docker('exec', '-u', '0', target, 'mkdir', '-p', '/var/lib/odoo/filestore', '/mnt/extra-addons')
        docker('stop', target)
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            extract(path / 'filestore.tar.gz', temp)
            extract(path / 'config.tar.gz', temp)
            docker('cp', str(temp / database), f'{target}:/var/lib/odoo/filestore/')
            # Preserve new-instance DB environment. Restore addons; configuration is copied
            # only for the original target, where DB host and domains remain valid.
            docker('cp', str(temp / 'addons') + '/.', f'{target}:/mnt/extra-addons/')
            if not new_instance:
                docker('cp', str(temp / 'etc') + '/.', f'{target}:/etc/odoo/')
        docker('start', target)
        docker('exec', '-u', '0', target, 'chown', '-R', 'odoo:odoo', '/var/lib/odoo', '/mnt/extra-addons')
        for attempt in range(60):
            result = subprocess.run(['docker', 'exec', target, 'python3', '-c',
                "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8069/web/login', timeout=3)"], capture_output=True)
            if result.returncode == 0:
                print('Restore verified: ' + target)
                return
            time.sleep(2)
        raise RuntimeError('Restored Odoo HTTP check failed')
    except Exception:
        # Keep the app stopped after incomplete replacement; never advertise partial success.
        subprocess.run(['docker', 'stop', target], capture_output=True)
        raise


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='action', required=True)
    b = commands.add_parser('backup')
    b.add_argument('version'); b.add_argument('instance'); b.add_argument('--root', default='/data/backups')
    r = commands.add_parser('restore')
    r.add_argument('path'); r.add_argument('--root', default='/data/backups')
    r.add_argument('--confirm-replace', action='store_true')
    r.add_argument('--new-instance'); r.add_argument('--http-port', type=int); r.add_argument('--domain')
    args = parser.parse_args()
    try:
        if args.action == 'backup':
            backup(args.version, args.instance, args.root)
        else:
            restore(args.path, args.root, args.new_instance, args.http_port, args.domain, args.confirm_replace)
    except (ValueError, OSError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f'Backup/restore failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
