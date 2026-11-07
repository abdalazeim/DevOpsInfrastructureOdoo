"""Resolved, non-secret deployment names, paths and endpoints shared by consumers."""
from pathlib import Path
from pathlib import PurePosixPath
import re


def selected_versions(profile):
    return [v for v in ('17', '18', '19') if getattr(profile, 'odoo' + v).enabled]


def validate_deployment(profile, version):
    if profile.deployment_mode not in ('local', 'domain'):
        raise ValueError('Deployment mode must be local or domain')
    cfg = getattr(profile, 'odoo' + version)
    for raw in (profile.paths.data_root, profile.paths.backup_root):
        path = PurePosixPath(raw)
        if not path.is_absolute() or '..' in path.parts or len(path.parts) < 3:
            raise ValueError('Use a dedicated absolute deployment/backup directory')
    if not 1024 <= (cfg.http_port or 10000 + int(version)) <= 65535:
        raise ValueError('Odoo HTTP port must be in 1024..65535')
    if cfg.database.internal_port != 5432 or cfg.database.expose_public_port:
        raise ValueError('Managed PostgreSQL uses private port 5432 only')
    for value in (cfg.database.name, cfg.database.user, profile.network.proxy_network_name):
        if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,62}', value):
            raise ValueError('Invalid database or network identifier')
    if cfg.workers < 0:
        raise ValueError('Odoo workers cannot be negative')
    for value in (cfg.database.password_env_var, cfg.database.admin_password_env_var):
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', value):
            raise ValueError('Invalid credential environment reference')
    if profile.deployment_mode == 'domain':
        if not profile.traefik.enabled:
            raise ValueError('Domain mode requires Traefik')
        domains = [cfg.domain]
        if profile.traefik.dashboard_enabled:
            domains.append(profile.traefik.dashboard_domain)
        for domain in domains:
            if not re.fullmatch(r'(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}', domain) or domain.endswith('.localhost'):
                raise ValueError('Domain mode needs explicitly configured DNS domains')
        if '@' not in profile.traefik.acme_email or profile.traefik.acme_email.endswith('@localhost'):
            raise ValueError('Domain mode needs an explicit ACME email')


def stack_contract(profile, version):
    if version not in ('17', '18', '19'):
        raise ValueError('Unsupported Odoo version')
    cfg = getattr(profile, 'odoo' + version)
    name = 'odoo' + version
    port = cfg.http_port or 10000 + int(version)
    folder = Path(profile.paths.data_root) / name
    return dict(version=version, app=name, database_container=name + '-db',
                database=cfg.database.name, database_user=cfg.database.user, database_port=cfg.database.internal_port,
                folder=str(folder), compose=str(folder / 'compose.json'), project=name,
                database_volume=name + '_database', filestore_volume=name + '_filestore',
                internal_network=name + '_internal', proxy_network=profile.network.proxy_network_name,
                http_port=port, url=('https://' + cfg.domain if profile.deployment_mode == 'domain'
                                    else f'http://127.0.0.1:{port}'))
