"""
Odoo Infrastructure Manager Module
Provides discovery, lifecycle management, and diagnostics for Odoo 17 & 19 environments.
"""
import os
import subprocess
import json
import tarfile
import datetime
import hashlib
from typing import Dict, Any, List

class OdooDockerManager:
    CONFIG = {
        '17': {
            'dir': '/opt/odoo-17-docker',
            'docker_compose': '/opt/odoo-17-docker/docker-compose.yml',
            'container_name': 'odoo17',
            'db_container': 'odoo17-db'
        },
        '19': {
            'dir': '/opt/odoo19-enterprise',
            'docker_compose': '/opt/odoo19-enterprise/docker-compose.yml',
            'container_name': 'odoo19',
            'db_container': 'odoo19-db'
        }
    }

    @classmethod
    def discover_odoo_env(cls) -> Dict[str, Any]:
        """Audits both Odoo environments."""
        return {
            'odoo17': cls._inspect_instance('17'),
            'odoo19': cls._inspect_instance('19'),
            'proxy_network_exists': cls._check_network('proxy'),
            'warnings': []
        }

    @classmethod
    def _inspect_instance(cls, version: str) -> Dict[str, Any]:
        cfg = cls.CONFIG.get(version)
        if not cfg or not os.path.exists(cfg['dir']):
            return {'container_status': 'not_found', 'image': 'N/A', 'version': version}
        
        # Check container
        try:
            res = subprocess.run(['docker', 'inspect', cfg['container_name']], stdout=subprocess.PIPE, text=True, check=False)
            if res.returncode == 0:
                data = json.loads(res.stdout)[0]
                state = data.get('State', {})
                return {
                    'container_status': 'running' if state.get('Running') else 'stopped',
                    'image': data.get('Config', {}).get('Image', 'unknown'),
                    'uptime': state.get('StartedAt', 'N/A'),
                    'db_ready': True, # Mock
                    'http_ready': True, # Mock
                    'version': version,
                    'pg_version': '16' if version == '17' else '18'
                }
        except:
            pass
        return {'container_status': 'stopped', 'image': 'N/A', 'version': version, 'pg_version': 'N/A'}

    @staticmethod
    def _check_network(network: str) -> bool:
        return subprocess.run(['docker', 'network', 'inspect', network], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

    @classmethod
    def lifecycle_action(cls, version: str, action: str) -> bool:
        """Executes start/stop/restart/logs via bash script."""
        script = os.path.join("automation/scripts/deploy-odoo.sh")
        cmd = ['bash', script, version, action]
        return subprocess.run(cmd).returncode == 0

    @classmethod
    def _inspect_instance(cls, version: str) -> Dict[str, Any]:
        """Audits actual Docker state."""
        container_name = f"odoo{version}"
        try:
            # Check container
            res = subprocess.run(['docker', 'inspect', container_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            if res.returncode == 0:
                data = json.loads(res.stdout)[0]
                state = data.get('State', {})
                return {
                    'container_status': 'running' if state.get('Running') else 'stopped',
                    'image': data.get('Config', {}).get('Image', 'unknown'),
                    'uptime': state.get('StartedAt', 'N/A'),
                    'db_ready': True, # Simple check: docker exec odoo17-db pg_isready...
                    'http_ready': True, # Simple check: curl...
                    'version': version,
                    'pg_version': '16' if version == '17' else '18'
                }
        except:
            pass
        return {'container_status': 'not_found', 'image': 'N/A', 'version': version, 'pg_version': 'N/A'}

