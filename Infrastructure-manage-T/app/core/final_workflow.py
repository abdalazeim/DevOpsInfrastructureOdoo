"""Seven-phase workflow driven by live checks and private persisted evidence."""
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from app.core.installation_pipeline import InstallationPipeline
from app.core.server_setup import ServerSetupWorkflow
from app.core.workflow_reports import private_write, write_reports
from app.models.deployment import selected_versions, stack_contract, validate_deployment

PHASES = ['System Preparation', 'Sequential Installation', 'Operation Verification',
          'Integration & Connectivity', 'Integration Success Report',
          'Final Deployment Report', 'Documentation Synchronization']


class FinalWorkflow:
    def __init__(self, profile, report_dir, dry_run=False, apply=False, resume=False, output=print,
                 run_jenkins_smoke=False):
        self.profile, self.folder = profile, Path(report_dir)
        self.dry_run, self.apply, self.resume, self.output = dry_run, apply, resume, output
        self.run_jenkins_smoke = run_jenkins_smoke
        self.fingerprint = hashlib.sha256(json.dumps(asdict(profile), sort_keys=True).encode()).hexdigest()
        self.phases, self.checks = [], []
        self.phase_name = PHASES[0]
        self.installation = {}
        self.host = {'hostname': platform.node(), 'system': platform.platform(), 'python': sys.version.split()[0]}
        self._phase_offset = 0
        self._secrets = [os.environ[key] for key in (
            profile.integration.jenkins_user_env, profile.integration.jenkins_token_env,
            *[getattr(profile, 'odoo' + v).database.password_env_var for v in ('17', '18', '19')],
            *[getattr(profile, 'odoo' + v).database.admin_password_env_var for v in ('17', '18', '19')])
            if os.environ.get(key)]

    def clean(self, value):
        if isinstance(value, dict):
            return {key: self.clean(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.clean(item) for item in value]
        if isinstance(value, str):
            for secret in self._secrets:
                value = value.replace(secret, '[REDACTED]')
        return value

    def record(self, label, status, started=None, component_a='', component_b='', integration_type='verification',
               required=True, **evidence):
        finished = datetime.now(timezone.utc)
        duration = max(0, time.monotonic() - started) if started is not None else 0
        check = dict(name=label, status=status, phase=self.phase_name, required=required,
                     component_a=component_a or label, component_b=component_b or 'target host',
                     integration_type=integration_type, settings=evidence.pop('settings', {}),
                     connection_result=status, functional_result=status,
                     started_at=datetime.fromtimestamp(finished.timestamp() - duration, timezone.utc).isoformat(),
                     finished_at=finished.isoformat(), duration_seconds=duration, **evidence)
        self.checks.append(self.clean(check))
        self.output(f'  [{status}] {label}')
        return status == 'SUCCESS'

    def command(self, label, args, **metadata):
        started = time.monotonic()
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=120)
            return self.record(label, 'SUCCESS' if result.returncode == 0 else 'FAILED', started,
                               command=args, exit_code=result.returncode,
                               stdout=result.stdout[-4000:], stderr=result.stderr[-4000:], **metadata)
        except (OSError, subprocess.SubprocessError) as exc:
            return self.record(label, 'NOT_VERIFIED', started, command=args, exit_code=None,
                               stderr=str(exc), **metadata)

    def phase(self, name, status, start, detail=''):
        checks = self.checks[self._phase_offset:]
        duration = time.monotonic() - start
        finished = datetime.now(timezone.utc)
        self.phases.append(dict(name=name, status=status, detail=detail,
            started_at=datetime.fromtimestamp(finished.timestamp() - duration, timezone.utc).isoformat(),
            finished_at=finished.isoformat(), duration_seconds=duration,
            success_count=sum(c['status'] == 'SUCCESS' for c in checks),
            failure_count=sum(c['status'] == 'FAILED' for c in checks),
            skip_count=sum(c['status'] in ('SKIPPED', 'NOT_VERIFIED', 'NEEDS_CONFIGURATION') for c in checks)))
        self._phase_offset = len(self.checks)
        self.output(f'[{len(self.phases)}/7] {name}: {status} {detail}')
        if not self.dry_run:
            self.save()

    def save(self):
        self.folder.mkdir(parents=True, exist_ok=True)
        os.chmod(self.folder, 0o700)
        private_write(self.folder / 'workflow-state.json', json.dumps(self.clean(self.report()), indent=2))

    def report(self):
        required = [c for c in self.checks if c.get('required', True)]
        verified = sum(c['status'] == 'SUCCESS' for c in required)
        gaps = [c['name'] + ': ' + c['status'] for c in required if c['status'] != 'SUCCESS']
        # A restore drill is mandatory acceptance and cannot be inferred from a backup manifest.
        if not any(c['name'] == 'Isolated restore drill' for c in required):
            gaps.append('Isolated restore drill: NOT_VERIFIED')
        total = len(required) + int(not any(c['name'] == 'Isolated restore drill' for c in required))
        percent = round(100 * verified / total) if total else 0
        if gaps:
            percent = min(percent, 99)
        statuses = [p['status'] for p in self.phases[:4]]
        overall = ('FAILED' if 'FAILED' in statuses else
                   'FULL SUCCESS' if len(statuses) == 4 and all(s == 'SUCCESS' for s in statuses) and not gaps else
                   'PARTIAL SUCCESS' if verified else 'NOT VERIFIED')
        rows = []
        names = ['docker-engine', 'docker-compose', *['odoo' + v for v in selected_versions(self.profile)], 'traefik', 'ansible']
        if self.profile.jenkins_enabled:
            names.append('jenkins')
        if self.profile.portainer_enabled:
            names.append('portainer')
        for name in names:
            matching = [c for c in self.checks if c.get('component_a') == name or c.get('component_b') == name]
            def status_for(phase):
                found = [c for c in matching if c['phase'] == phase and c.get('required', True)]
                if not found:
                    return 'NOT_VERIFIED'
                return 'SUCCESS' if all(c['status'] == 'SUCCESS' for c in found) else ('FAILED' if any(c['status'] == 'FAILED' for c in found) else 'NOT_VERIFIED')
            rows.append(dict(name=name, installation=self.installation.get(name, 'NOT_VERIFIED'),
                             operation=status_for(PHASES[2]), integration=status_for(PHASES[3]),
                             verification='SUCCESS' if matching and all(c['status'] == 'SUCCESS' for c in matching if c.get('required', True)) else 'NOT_VERIFIED'))
        return dict(profile_hash=self.fingerprint, phases=self.phases, checks=self.checks, host=self.host,
                    stacks=[stack_contract(self.profile, v) for v in selected_versions(self.profile)], components=rows,
                    unverified_acceptance=gaps, status='PRODUCTION READY' if overall == 'FULL SUCCESS' else 'NOT READY',
                    workflow_status=overall, dry_run=self.dry_run, generated_at=datetime.now(timezone.utc).isoformat(),
                    completed_percent=percent, verified_checks=verified, required_checks=total)

    def prepare(self):
        if platform.system() != 'Linux':
            return self.record('Ubuntu target', 'NOT_VERIFIED', detail='No Ubuntu target available; no infrastructure changes')
        info = platform.freedesktop_os_release()
        self.host.update(ubuntu_version=info.get('VERSION_ID'), architecture=platform.machine(), cpu_count=os.cpu_count())
        if info.get('ID') != 'ubuntu':
            return self.record('Ubuntu target', 'FAILED', detail='Ubuntu is required')
        target = Path(self.profile.paths.data_root)
        while not target.exists():
            target = target.parent
        free = shutil.disk_usage(target).free
        memory = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemTotal:'))) * 1024
        self.host.update(memory_bytes=memory, free_disk_bytes=free, disk_checked_at=str(target))
        enough = free >= self.profile.integration.min_free_disk_gib * 1024**3 and memory >= self.profile.integration.min_memory_mib * 1024**2
        good = self.record('Ubuntu resources', 'SUCCESS' if enough else 'FAILED', settings=self.host)
        good = self.command('Package database health', ['bash', '-c', 'report=$(dpkg --audit) && test -z "$report" || { printf "%s\\n" "$report"; exit 1; }']) and good
        if self.apply:
            good = self.command('Repository DNS', ['getent', 'hosts', 'download.docker.com', 'apt.postgresql.org']) and good
        self.command('Installed executables', ['bash', '-c', 'for c in python3 git docker ansible jenkins; do command -v "$c" || :; done'], required=False)
        if shutil.which('docker'):
            for label, args in [('Existing containers', ['ps', '-a', '--format', '{{json .}}']),
                                ('Existing networks', ['network', 'ls']), ('Existing volumes', ['volume', 'ls'])]:
                self.command(label, ['docker', *args], required=False)
        return good

    def verify_components(self):
        good = True
        for comp in ServerSetupWorkflow(self.profile).COMPONENT_DEFINITIONS:
            passed = self.command(comp.name, comp.check_cmd, component_a=comp.name)
            good = passed and good
            if self.phase_name == PHASES[1]:
                self.installation[comp.name] = 'ALREADY_INSTALLED' if passed else 'NOT_VERIFIED'
        return good

    def integrate(self):
        good = True
        for version in selected_versions(self.profile):
            cfg = getattr(self.profile, 'odoo' + version)
            spec = stack_contract(self.profile, version)
            good = self.command('Compose configuration ' + version,
                ['docker', 'compose', '-p', spec['project'], '-f', spec['compose'], 'config', '--quiet'],
                component_a=spec['app'], component_b='docker-compose', settings=spec) and good
            good = self.http('Odoo route ' + version, spec['url'] + '/web/login', component_a=spec['app']) and good
            # The managed verifier authenticates against the selected DB and checks Odoo's base schema.
            script = str(Path(__file__).resolve().parents[1] / 'services/managed_stack.py')
            good = self.command('Odoo/PostgreSQL functional connection ' + version,
                [sys.executable, script, '--profile-json', json.dumps(asdict(self.profile)), '--version', version, '--verify'],
                component_a=spec['app'], component_b=spec['database_container'], settings=spec) and good
        if self.profile.traefik.enabled:
            if self.profile.deployment_mode == 'local' and self.profile.traefik.dashboard_enabled:
                good = self.http('Traefik dashboard', 'http://127.0.0.1:10090/dashboard/', component_a='traefik') and good
                good = self.http('Traefik Docker provider', 'http://127.0.0.1:10090/api/overview', component_a='traefik') and good
            elif self.profile.deployment_mode == 'domain':
                self.record('Traefik authenticated dashboard', 'NEEDS_CONFIGURATION', component_a='traefik',
                            detail='Odoo HTTPS routes checked; separate authenticated dashboard acceptance required')
                good = False
        repo = Path(__file__).resolve().parents[2]
        inventory = Path(self.profile.integration.ansible_inventory) if self.profile.integration.ansible_inventory else None
        if inventory and inventory.is_file():
            prefix = []
            if self.profile.integration.ansible_config:
                config = Path(self.profile.integration.ansible_config)
                if not config.is_file():
                    self.record('Ansible configuration', 'NEEDS_CONFIGURATION', component_a='ansible', detail='Configured ansible.cfg missing')
                    good = False
                prefix = ['env', 'ANSIBLE_CONFIG=' + str(config)]
            for label, args in [
                ('Ansible configuration', ['ansible-config', 'dump', '--only-changed']),
                ('Ansible inventory', ['ansible-inventory', '-i', str(inventory), '--list']),
                ('Ansible connectivity', ['ansible', 'all', '-i', str(inventory), '-m', 'ansible.builtin.ping']),
                ('Ansible syntax', ['ansible-playbook', '-i', str(inventory), str(repo / 'deployment/ansible/verify.yml'), '--syntax-check']),
                ('Ansible safe playbook', ['ansible-playbook', '-i', str(inventory), str(repo / 'deployment/ansible/verify.yml')])]:
                good = self.command(label, prefix + args, component_a='ansible', component_b='target host') and good
        else:
            self.record('Ansible inventory', 'NEEDS_CONFIGURATION', component_a='ansible', detail='Configure integration.ansible_inventory explicitly')
            good = False
        if self.profile.jenkins_enabled:
            from app.services.jenkins_verification import verify_smoke
            good = self.http('Jenkins HTTP', self.profile.integration.jenkins_url.rstrip('/') + '/login', component_a='jenkins') and good
            started = time.monotonic()
            result = verify_smoke(self.profile.integration, execute=self.run_jenkins_smoke)
            good = self.record('Jenkins Docker/Ansible smoke job', result.pop('status'), started,
                               component_a='jenkins', component_b='ansible/docker/git', **result) and good
        if self.profile.portainer_enabled:
            # Default Portainer uses a self-signed certificate: do not disable TLS validation silently.
            good = self.http('Portainer HTTPS', 'https://127.0.0.1:9443/api/status', component_a='portainer') and good
        self.record('Isolated restore drill', 'NOT_VERIFIED', component_a='backup',
                    detail='Requires isolated restore and database/attachment content verification; never run against production')
        return False  # mandatory restore acceptance is deliberately not fabricated

    def run(self):
        versions = selected_versions(self.profile)
        if len(versions) != 1:
            raise ValueError('Select exactly one Odoo version for this workflow')
        validate_deployment(self.profile, versions[0])
        if self.dry_run:
            InstallationPipeline(profile=self.profile, dry_run=True, on_output=self.output).run()
            for name in PHASES:
                self.phase(name, 'NOT_VERIFIED', time.monotonic(), 'Dry-run: planned only; no execution or report files')
            return self.report()
        prior = {}
        state = self.folder / 'workflow-state.json'
        if self.resume and state.exists():
            prior = json.loads(state.read_text(encoding='utf-8'))
            if prior.get('profile_hash') != self.fingerprint:
                raise ValueError('Profile changed; resume requires a new reviewed plan/report directory')
        self.phase_name = PHASES[0]
        started = time.monotonic()
        prepared = self.prepare()
        self.phase(PHASES[0], 'SUCCESS' if prepared else ('FAILED' if any(c['status'] == 'FAILED' for c in self.checks) else 'NOT_VERIFIED'), started)
        self.phase_name = PHASES[1]
        started = time.monotonic()
        installed = False
        prior_install = any(p['name'] == PHASES[1] and p['status'] == 'SUCCESS' for p in prior.get('phases', []))
        if prepared and self.apply and not prior_install:
            result = InstallationPipeline(profile=self.profile, use_sudo=True, on_output=self.output, report_dir=self.folder / 'installation').run()
            installed = result['overall_success']
            for name, component in result['components'].items():
                self.installation[name] = component.status.value
                self.record('Installation ' + name, 'SUCCESS' if component.status.value in ('INSTALLED', 'ALREADY INSTALLED') else 'FAILED',
                            component_a=name, detail=component.error or component.skip_reason,
                            settings={'evidence_file': 'installation/latest-installation.json'})
        elif prepared:
            installed = self.verify_components()
        self.phase(PHASES[1], 'SUCCESS' if installed else 'FAILED' if prepared else 'NOT_VERIFIED', started)
        self.phase_name = PHASES[2]
        started = time.monotonic()
        operational = self.verify_components() if installed else False
        self.phase(PHASES[2], 'SUCCESS' if operational else 'FAILED' if installed else 'NOT_VERIFIED', started)
        self.phase_name = PHASES[3]
        started = time.monotonic()
        integrated = self.integrate() if operational else False
        relevant = self.checks[self._phase_offset:]
        self.phase(PHASES[3], 'SUCCESS' if integrated else 'FAILED' if any(c['status'] == 'FAILED' for c in relevant) else 'NOT_VERIFIED', started)
        for name in PHASES[4:6]:
            self.phase_name = name
            started = time.monotonic()
            write_reports(self.folder, self.clean(self.report()))
            self.phase(name, 'SUCCESS', started, 'Evidence written; inspect checks for actual integration outcome')
        self.phase_name = PHASES[6]
        started = time.monotonic()
        docs = Path(__file__).resolve().parents[2] / 'docs'
        required_docs = ('MASTER_SYSTEM_DOCUMENTATION.md', 'DOCUMENTATION_INDEX.md', 'INSTALLATION_ARCHITECTURE.md',
                         'DEPENDENCY_GRAPH.md', 'COMPONENT_VERIFICATION.md', 'ERROR_AND_RECOVERY_GUIDE.md')
        synchronized = all((docs / name).is_file() for name in required_docs)
        self.phase(PHASES[6], 'SUCCESS' if synchronized else 'FAILED', started, 'Documentation references checked; no deployment success inferred')
        self.save()
        write_reports(self.folder, self.clean(self.report()))  # final snapshots contain all seven completed phase records
        return self.report()

    def http(self, label, url, **metadata):
        started = time.monotonic()
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                good = response.status == 200
            return self.record(label, 'SUCCESS' if good else 'FAILED', started, url=url, **metadata)
        except (OSError, ValueError) as exc:
            return self.record(label, 'FAILED', started, url=url, stderr=str(exc), **metadata)
