"""One profile-driven Docker deployment used by both installation interfaces."""
import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import time
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.models.profile import InfrastructureProfile
from app.models.deployment import stack_contract, validate_deployment


def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, capture_output=True, timeout=kwargs.pop('timeout', 300), **kwargs).stdout.strip()


def stack_spec(profile, version, password):
    """Return Compose data; no IO, shell expansion, or hard-coded credentials."""
    cfg = getattr(profile, 'odoo' + version)
    contract = stack_contract(profile, version)
    name = contract['app']
    # Compose interpolates dollar signs even in JSON values.
    password = password.replace('$', '$$')
    network = profile.network.proxy_network_name
    pg_major = cfg.database.engine.split(':')[-1].split('-')[0].split('.')[0]
    pg_target = '/var/lib/postgresql' if int(pg_major) >= 18 else '/var/lib/postgresql/data'
    db = {'image': cfg.database.engine, 'container_name': name + '-db', 'restart': 'unless-stopped',
          'environment': {'POSTGRES_USER': cfg.database.user, 'POSTGRES_PASSWORD': password,
                          'POSTGRES_DB': cfg.database.name},
          'volumes': ['database:' + pg_target], 'networks': ['internal'],
          'healthcheck': {'test': ['CMD-SHELL', 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
                          'interval': '5s', 'timeout': '5s', 'retries': 30}}
    app = {'image': cfg.image, 'container_name': name, 'restart': 'unless-stopped',
           'environment': {'HOST': name + '-db', 'PORT': '5432', 'USER': cfg.database.user, 'PASSWORD': password},
           'depends_on': {'db': {'condition': 'service_healthy'}},
           'volumes': ['filestore:/var/lib/odoo', './odoo.conf:/etc/odoo/odoo.conf:ro', './addons:/mnt/extra-addons'],
           'networks': ['internal'],
           'healthcheck': {'test': ['CMD', 'python3', '-c',
                "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8069/web/login', timeout=5)"],
                'interval': '10s', 'timeout': '8s', 'retries': 30}}
    networks = {'internal': {'name': contract['internal_network']}}
    if profile.traefik.enabled and profile.deployment_mode == 'domain':
        if not re.fullmatch(r'[A-Za-z0-9.-]+', cfg.domain or ''):
            raise ValueError('A valid Odoo domain is required for Traefik')
        networks['proxy'] = {'external': True, 'name': network}
        app['networks'].append('proxy')
        labels = {'traefik.enable': 'true', 'traefik.docker.network': network,
                  f'traefik.http.routers.{name}.rule': f'Host(`{cfg.domain}`)',
                  f'traefik.http.routers.{name}.entrypoints': 'websecure',
                  f'traefik.http.routers.{name}.tls.certresolver': 'letsencrypt',
                  f'traefik.http.routers.{name}.service': name,
                  f'traefik.http.services.{name}.loadbalancer.server.port': '8069',
                  f'traefik.http.routers.{name}-ws.rule': f'Host(`{cfg.domain}`) && PathPrefix(`/websocket`)',
                  f'traefik.http.routers.{name}-ws.entrypoints': 'websecure',
                  f'traefik.http.routers.{name}-ws.tls.certresolver': 'letsencrypt',
                  f'traefik.http.routers.{name}-ws.service': name + '-ws',
                  f'traefik.http.services.{name}-ws.loadbalancer.server.port': '8072'}
        app['labels'] = labels
    else:
        app['ports'] = [f'127.0.0.1:{cfg.http_port or 10000 + int(version)}:8069']
    return {'services': {'db': db, 'odoo': app}, 'networks': networks,
            'volumes': {'database': {'name': contract['database_volume']},
                        'filestore': {'name': contract['filestore_volume']}}}


def verify(version, profile=None):
    for name in ('odoo' + version + '-db', 'odoo' + version):
        container = json.loads(run(['docker', 'inspect', name]))[0]
        if profile is not None:
            cfg = getattr(profile, 'odoo' + version)
            expected = cfg.database.engine if name.endswith('-db') else cfg.image
            if container.get('Config', {}).get('Image') != expected:
                raise RuntimeError(f'{name} image differs from the selected profile; explicit migration required')
        data = container['State']
        if not data.get('Running') or data.get('Paused') or data.get('Health', {}).get('Status') != 'healthy':
            raise RuntimeError(f'{name} is not healthy')
    if profile is not None:
        cfg = getattr(profile, 'odoo' + version)
        contract = stack_contract(profile, version)
        code = ("import os,sys,psycopg2,urllib.request; "
                "c=psycopg2.connect(host=os.environ['HOST'],port=os.environ['PORT'],user=os.environ['USER'],"
                "password=os.environ['PASSWORD'],dbname=sys.argv[1],connect_timeout=5);"
                "cur=c.cursor();cur.execute('SELECT 1');assert cur.fetchone()==(1,);"
                "cur.execute(\"SELECT state FROM ir_module_module WHERE name='base'\");"
                "assert cur.fetchone()==('installed',);c.close();"
                "assert urllib.request.urlopen('http://127.0.0.1:8069/web/login',timeout=10).status==200")
        run(['docker', 'exec', contract['app'], 'python3', '-c', code, cfg.database.name])


def deploy(profile, version):
    validate_deployment(profile, version)
    run(['docker', 'info'])
    cfg = getattr(profile, 'odoo' + version)
    existing = [subprocess.run(['docker', 'inspect', name], capture_output=True).returncode == 0
                for name in ('odoo' + version, 'odoo' + version + '-db')]
    if any(existing):
        if not all(existing):
            raise RuntimeError('Partial existing stack; repair requires an explicit reviewed plan')
        verify(version, profile)
        return
    if not cfg.enabled:
        raise ValueError('Requested Odoo version is disabled in the profile')
    contract = stack_contract(profile, version)
    folder = Path(contract['folder'])
    if folder.exists() and any(folder.iterdir()):
        raise RuntimeError('Existing deployment files without a complete healthy stack; reviewed recovery required')
    for volume in (contract['database_volume'], contract['filestore_volume']):
        if subprocess.run(['docker', 'volume', 'inspect', volume], capture_output=True).returncode == 0:
            raise RuntimeError('Existing data volume without a complete healthy stack; refusing automatic adoption')
    folder.mkdir(parents=True, exist_ok=True)
    os.chmod(folder, 0o700)
    credential = folder / 'credentials.json'
    if credential.exists():
        credentials = json.loads(credential.read_text())
    else:
        # Never silently change an existing DB password or adopt another installation.
        for name in ('odoo' + version, 'odoo' + version + '-db'):
            if subprocess.run(['docker', 'inspect', name], capture_output=True).returncode == 0:
                raise RuntimeError(f'{name} already exists without managed credentials; migrate it explicitly')
        credentials = {'database': os.environ.get(cfg.database.password_env_var) or secrets.token_urlsafe(32),
                       'admin': os.environ.get(cfg.database.admin_password_env_var) or secrets.token_urlsafe(32)}
        with credential.open('x') as f:
            os.chmod(credential, 0o600)
            json.dump(credentials, f)
    spec = stack_spec(profile, version, credentials['database'])
    (folder / 'addons').mkdir(exist_ok=True)
    conf = folder / 'odoo.conf'
    if any(char in credentials['admin'] for char in '\r\n'):
        raise ValueError('Admin secret must be a single line')
    conf.write_text('[options]\nadmin_passwd = ' + credentials['admin'] +
                    f'\nproxy_mode = {str(profile.traefik.enabled)}\nworkers = {cfg.workers}\n'
                    'data_dir = /var/lib/odoo\naddons_path = /mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons\n')
    os.chmod(conf, 0o644)  # parent directory is private; container needs read access.
    compose = folder / 'compose.json'
    compose.write_text(json.dumps(spec, indent=2))
    os.chmod(compose, 0o600)
    if profile.traefik.enabled and profile.deployment_mode == 'domain':
        net = profile.network.proxy_network_name
        if subprocess.run(['docker', 'network', 'inspect', net], capture_output=True).returncode:
            run(['docker', 'network', 'create', net])
    command = ['docker', 'compose', '-p', 'odoo' + version, '-f', str(compose)]
    run(command + ['config', '--quiet'])
    run(command + ['up', '-d', '--wait', '--wait-timeout', '240', 'db'])
    run(['docker', 'exec', contract['database_container'], 'sh', '-c',
         'PGPASSWORD="$POSTGRES_PASSWORD" psql -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "SELECT 1"'])
    # This branch is restricted to a fresh directory and fresh named volumes.
    run(command + ['run', '--rm', '--no-deps', 'odoo', 'odoo', '--database', cfg.database.name,
                   '--init', 'base', '--without-demo', 'all', '--stop-after-init', '--no-http'], timeout=900)
    run(command + ['up', '-d', '--no-recreate', '--wait', '--wait-timeout', '240'])
    verify(version, profile)


def infrastructure(profile, component, check=False):
    if check:
        state = json.loads(run(['docker', 'inspect', component]))[0]['State']
        if not state.get('Running') or state.get('Paused') or state.get('Restarting'):
            raise RuntimeError(f'{component} is not running')
        return
    run(['docker', 'info'])
    if subprocess.run(['docker', 'inspect', component], capture_output=True).returncode == 0:
        infrastructure(profile, component, check=True)
        return
    folder = Path(profile.paths.data_root) / component
    if folder.exists() and any(folder.iterdir()):
        raise RuntimeError('Existing infrastructure configuration requires reviewed recovery; no files overwritten')
    if component == 'jenkins' and subprocess.run(['docker', 'volume', 'inspect', 'jenkins_jenkins_data'], capture_output=True).returncode == 0:
        raise RuntimeError('Existing Jenkins home requires an explicit recovery plan')
    folder.mkdir(parents=True, exist_ok=True)
    os.chmod(folder, 0o700)
    net = profile.network.proxy_network_name
    if subprocess.run(['docker', 'network', 'inspect', net], capture_output=True).returncode:
        run(['docker', 'network', 'create', net])
    if component == 'traefik':
        import yaml
        acme = folder / 'acme.json'
        acme.touch(exist_ok=True)
        os.chmod(acme, 0o600)
        static = {'api': {'dashboard': profile.traefik.dashboard_enabled},
                  'entryPoints': {'web': {'address': ':80', 'http': {'redirections': {
                      'entryPoint': {'to': 'websecure', 'scheme': 'https'}}}}, 'websecure': {'address': ':443'}},
                  'providers': {'docker': {'exposedByDefault': False, 'network': net}},
                  'certificatesResolvers': {'letsencrypt': {'acme': {'email': profile.traefik.acme_email,
                      'storage': '/acme.json', 'httpChallenge': {'entryPoint': 'web'}}}}}
        if profile.deployment_mode == 'local':
            static.pop('certificatesResolvers')
            static['entryPoints'] = {'web': {'address': ':80'}, 'traefik': {'address': ':8080'}}
            static['api'] = {'dashboard': profile.traefik.dashboard_enabled, 'insecure': profile.traefik.dashboard_enabled}
        (folder / 'traefik.yml').write_text(yaml.safe_dump(static))
        service = {'image': profile.traefik.image, 'container_name': component, 'restart': 'unless-stopped',
                   'ports': [f'{profile.traefik.http_port}:80', f'{profile.traefik.https_port}:443'],
                   'networks': ['proxy'], 'volumes': ['/var/run/docker.sock:/var/run/docker.sock:ro',
                       './traefik.yml:/etc/traefik/traefik.yml:ro', './acme.json:/acme.json']}
        if profile.deployment_mode == 'local':
            service['ports'] = ['127.0.0.1:10080:80']
            if profile.traefik.dashboard_enabled:
                service['ports'].append('127.0.0.1:10090:8080')
        if profile.traefik.dashboard_enabled and profile.deployment_mode == 'domain':
            password_file = folder / 'dashboard-password'
            if not password_file.exists():
                password_file.write_text(secrets.token_urlsafe(24))
                os.chmod(password_file, 0o600)
            hashed = run(['openssl', 'passwd', '-apr1', '-stdin'], input=password_file.read_text())
            (folder / 'users').write_text('admin:' + hashed + '\n')
            os.chmod(folder / 'users', 0o600)
            service['volumes'].append('./users:/users:ro')
            service['labels'] = {'traefik.enable': 'true',
                'traefik.http.routers.dashboard.rule': f'Host(`{profile.traefik.dashboard_domain}`)',
                'traefik.http.routers.dashboard.entrypoints': 'websecure',
                'traefik.http.routers.dashboard.tls.certresolver': 'letsencrypt',
                'traefik.http.routers.dashboard.service': 'api@internal',
                'traefik.http.routers.dashboard.middlewares': 'dashboard-auth',
                'traefik.http.middlewares.dashboard-auth.basicauth.usersfile': '/users'}
        spec = {'services': {component: service}, 'networks': {'proxy': {'external': True, 'name': net}}}
    elif component == 'jenkins':
        spec = {'services': {'jenkins': {'image': 'jenkins/jenkins:lts-jdk21', 'container_name': 'jenkins',
                    'restart': 'unless-stopped', 'ports': ['127.0.0.1:8081:8080'],
                    'volumes': ['jenkins_data:/var/jenkins_home']}}, 'volumes': {'jenkins_data': {}}}
    else:
        raise ValueError('Unknown infrastructure component')
    compose = folder / 'compose.json'
    compose.write_text(json.dumps(spec, indent=2))
    os.chmod(compose, 0o600)
    run(['docker', 'compose', '-p', component, '-f', str(compose), 'up', '-d', '--wait'])
    infrastructure(profile, component, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile-json', required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--version', choices=['17', '18', '19'])
    group.add_argument('--component', choices=['traefik', 'jenkins'])
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    try:
        profile = InfrastructureProfile.from_dict(json.loads(args.profile_json))
        if args.component:
            infrastructure(profile, args.component, args.verify)
        else:
            verify(args.version, profile) if args.verify else deploy(profile, args.version)
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f'Stack operation failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
