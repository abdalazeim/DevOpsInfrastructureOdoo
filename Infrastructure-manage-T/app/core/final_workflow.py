"""Seven-phase workflow with persisted evidence, resumable installation and honest gates."""
import hashlib
import json
import os
import platform
import subprocess
import time
import urllib.request
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from app.core.installation_pipeline import InstallationPipeline
from app.core.server_setup import ServerSetupWorkflow

PHASES = ['System Preparation', 'Sequential Installation', 'Operation Verification',
          'Integration & Connectivity', 'Integration Success Report',
          'Final Deployment Report', 'Documentation Synchronization']


class FinalWorkflow:
    def __init__(self, profile, report_dir, dry_run=False, apply=False, resume=False, output=print):
        self.profile, self.folder = profile, Path(report_dir)
        self.dry_run, self.apply, self.resume, self.output = dry_run, apply, resume, output
        self.fingerprint = hashlib.sha256(json.dumps(asdict(profile), sort_keys=True).encode()).hexdigest()
        self.phases, self.checks = [], []

    def command(self, label, args):
        started = time.monotonic()
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=120)
            check = dict(name=label, status='SUCCESS' if result.returncode == 0 else 'FAILED',
                         exit_code=result.returncode, stdout=result.stdout[-4000:], stderr=result.stderr[-4000:])
        except (OSError, subprocess.SubprocessError) as exc:
            check = dict(name=label, status='NOT_VERIFIED', exit_code=None, stdout='', stderr=str(exc))
        check.update(command=args, duration_seconds=time.monotonic() - started)
        self.checks.append(check)
        return check['status'] == 'SUCCESS'

    def phase(self, name, status, start, detail=''):
        self.phases.append(dict(name=name, status=status, detail=detail,
            finished_at=datetime.now(timezone.utc).isoformat(), duration_seconds=time.monotonic() - start))
        self.output(f'{name}: {status} {detail}')
        if not self.dry_run:
            self.save()

    def save(self):
        self.folder.mkdir(parents=True, exist_ok=True)
        os.chmod(self.folder, 0o700)
        data = self.report()
        temp = self.folder / 'workflow-state.tmp'
        temp.write_text(json.dumps(data, indent=2), encoding='utf-8')
        os.chmod(temp, 0o600)
        temp.replace(self.folder / 'workflow-state.json')

    def report(self):
        required = self.phases[:4]
        ready = len(required) == 4 and all(p['status'] == 'SUCCESS' for p in required)
        return dict(profile_hash=self.fingerprint, phases=self.phases, checks=self.checks,
                    unverified_acceptance=['Isolated backup/restore drill and full Ubuntu end-to-end deployment'],
                    status='READY WITH WARNINGS' if ready and len(self.phases) == 7 and all(p['status'] == 'SUCCESS' for p in self.phases) else 'NOT READY',
                    dry_run=self.dry_run, generated_at=datetime.now(timezone.utc).isoformat(),
                    completed_percent=round(100 * sum(p['status'] == 'SUCCESS' for p in self.phases) / 7))

    def run(self):
        if self.dry_run:
            InstallationPipeline(profile=self.profile, dry_run=True, on_output=self.output).run()
            for name in PHASES:
                self.phase(name, 'NOT_VERIFIED', time.monotonic(), 'Dry-run: planned only; no changes or live verification')
            return self.report()
        prior = {}
        state = self.folder / 'workflow-state.json'
        if self.resume and state.exists():
            prior = json.loads(state.read_text())
            if prior.get('profile_hash') != self.fingerprint:
                raise ValueError('Profile changed; resume requires a new reviewed plan/report directory')
        started = time.monotonic()
        prepared = platform.system() == 'Linux'
        if prepared:
            prepared = self.command('Ubuntu identity and disk', ['bash', '-c', '. /etc/os-release; test "$ID" = ubuntu && df -Pk / && uname -m'])
        self.phase(PHASES[0], 'SUCCESS' if prepared else 'NOT_VERIFIED', started,
                   '' if prepared else 'Ubuntu target is required; no system changes made')
        started = time.monotonic()
        installed = False
        prior_install = any(p['name'] == PHASES[1] and p['status'] == 'SUCCESS' for p in prior.get('phases', []))
        if prepared and self.apply and not prior_install:
            result = InstallationPipeline(profile=self.profile, use_sudo=True, on_output=self.output, report_dir=self.folder / "installation").run()
            installed = result['overall_success']
        elif prepared:
            installed = True  # only permission to proceed to read-only verification, not an install claim
        self.phase(PHASES[1], 'SUCCESS' if installed else 'NOT_VERIFIED', started,
                   'Existing infrastructure; verification required' if installed and (not self.apply or prior_install) else '')
        started = time.monotonic()
        operational = installed
        if installed:
            setup = ServerSetupWorkflow(self.profile)
            for comp in setup.COMPONENT_DEFINITIONS:
                operational = self.command(comp.name, comp.check_cmd) and operational
        self.phase(PHASES[2], 'SUCCESS' if operational else 'NOT_VERIFIED', started)
        started = time.monotonic()
        integrated = operational
        if operational:
            for version in ('17', '18', '19'):
                cfg = getattr(self.profile, 'odoo' + version)
                if not cfg.enabled:
                    continue
                code = ("import os,psycopg2; c=psycopg2.connect(host=os.environ['HOST'], "
                        "user=os.environ['USER'],password=os.environ['PASSWORD'],dbname='postgres',connect_timeout=5); "
                        "cur=c.cursor();cur.execute('SELECT 1');assert cur.fetchone()==(1,);c.close()")
                integrated = self.command('Odoo/PostgreSQL authentication ' + version,
                    ['docker', 'exec', 'odoo' + version, 'python3', '-c', code]) and integrated
                url = ('https://' + cfg.domain + '/web/login' if self.profile.deployment_mode == 'domain'
                       else f'http://127.0.0.1:{cfg.http_port or 10000 + int(version)}/web/login')
                integrated = self.http('Odoo route ' + version, url) and integrated
            if self.profile.traefik.enabled and self.profile.deployment_mode == 'local':
                integrated = self.http('Traefik dashboard', 'http://127.0.0.1:10090/dashboard/') and integrated
            repo = Path(__file__).resolve().parents[2]
            inventory = repo / 'deployment/ansible/inventory/hosts.ini'
            if inventory.exists():
                integrated = self.command('Ansible inventory', ['ansible-inventory', '-i', str(inventory), '--list']) and integrated
                integrated = self.command('Ansible connectivity', ['ansible', 'all', '-i', str(inventory), '-m', 'ping']) and integrated
                integrated = self.command('Ansible syntax', ['ansible-playbook', '-i', str(inventory), str(repo / 'deployment/ansible/site.yml'), '--syntax-check']) and integrated
            else:
                self.checks.append(dict(name='Ansible connectivity', status='NOT_VERIFIED', stderr='Inventory not configured'))
                integrated = False
            if self.profile.jenkins_enabled:
                integrated = self.http('Jenkins HTTP', 'http://127.0.0.1:8081/login') and integrated
                # A login page is not proof of Jenkins/Docker/Ansible integration.
                self.checks.append(dict(name='Jenkins smoke pipeline', status='NOT_VERIFIED',
                    stderr='Requires an authenticated job run on the configured agent; no credentials provided to this workflow'))
                integrated = False
        self.phase(PHASES[3], 'SUCCESS' if integrated else 'NOT_VERIFIED', started)
        # These phases report evidence; they cannot turn a failed integration into success.
        for name, filename in [(PHASES[4], 'INTEGRATION_AND_OPERATION_SUCCESS_REPORT.json'),
                               (PHASES[5], 'FINAL_INFRASTRUCTURE_DEPLOYMENT_REPORT.json')]:
            started = time.monotonic()
            (self.folder / filename).write_text(json.dumps(self.report(), indent=2), encoding='utf-8')
            self.phase(name, 'SUCCESS', started, 'Evidence saved; see integration status, not just report-generation status')
        started = time.monotonic()
        docs = Path(__file__).resolve().parents[2] / 'docs'
        synchronized = all((docs / name).exists() for name in ('MASTER_SYSTEM_DOCUMENTATION.md', 'DOCUMENTATION_INDEX.md'))
        self.phase(PHASES[6], 'SUCCESS' if synchronized else 'FAILED', started, 'Central documentation references checked')
        self.save()
        return self.report()

    def http(self, label, url):
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                good = response.status == 200
            self.checks.append(dict(name=label, url=url, status='SUCCESS' if good else 'FAILED'))
            return good
        except (OSError, ValueError) as exc:
            self.checks.append(dict(name=label, url=url, status='FAILED', stderr=str(exc)))
            return False
