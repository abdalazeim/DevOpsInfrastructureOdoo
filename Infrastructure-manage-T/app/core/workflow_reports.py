"""Evidence-only report rendering. No command execution or readiness inference from files."""
import json
import os
from pathlib import Path


def private_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        os.chmod(temporary, 0o600)
        stream.write(content)
    temporary.replace(path)


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ').replace('\r', ' ')


def render(report, title):
    lines = [f'# {title}', '', f"Generated: {report['generated_at']}",
             f"Host: {cell(report['host']['hostname'])} | OS: {cell(report['host']['system'])}",
             f"Profile hash: `{report['profile_hash']}`", f"Result: **{report['workflow_status']}**",
             f"Production readiness: **{report['status']}**", '',
             f"Verified required checks: {report['verified_checks']}/{report['required_checks']} "
             f"({report['completed_percent']}%). This is evidence coverage, not phase/report-writing progress.", '',
             '## Components', '', '| Component | Installation | Operation | Integration | Verification |',
             '|---|---|---|---|---|']
    for row in report.get('components', []):
        lines.append('| ' + ' | '.join(cell(row[k]) for k in ('name', 'installation', 'operation', 'integration', 'verification')) + ' |')
    lines += ['', '## Phases', '', '| Stage | Status | Started | Finished | Duration | Successful / Failed / Skipped |',
              '|---|---|---|---|---|---|']
    for phase in report['phases']:
        lines.append('| ' + ' | '.join(cell(v) for v in (phase['name'], phase['status'], phase.get('started_at', ''),
                     phase.get('finished_at', ''), phase.get('duration_seconds', 0),
                     f"{phase.get('success_count', 0)} / {phase.get('failure_count', 0)} / {phase.get('skip_count', 0)}")) + ' |')
    lines += ['', '## Check evidence', '']
    for check in report['checks']:
        lines += [f"### {cell(check['name'])}",
                  f"{check.get('component_a', '')} → {check.get('component_b', '')}; "
                  f"{check.get('integration_type', '')}; **{check['status']}**", '',
                  '```json', json.dumps(check, ensure_ascii=False, indent=2).replace('```', '` ` `'), '```', '']
    lines += ['## Remaining acceptance', ''] + ['- ' + item for item in report['unverified_acceptance']]
    lines += ['', '## Service addresses', '',
              'Addresses below are configuration values. Only a SUCCESS HTTP check in the evidence verifies an address.']
    lines += ['- ' + cell(item['url']) for item in report.get('stacks', [])]
    lines += ['', '## Operations and recovery', '',
              'Use the exact profile/Compose project recorded in the stack settings. Inspect state and logs before retrying.',
              'Do not recreate existing containers or adopt old volumes automatically. Restoration requires explicit confirmation and an isolated drill.',
              'See docs/MASTER_SYSTEM_DOCUMENTATION.md and docs/disaster-recovery.md in the source checkout.']
    return '\n'.join(lines) + '\n'


def write_reports(folder, report):
    for name in ('INTEGRATION_AND_OPERATION_SUCCESS_REPORT', 'FINAL_INFRASTRUCTURE_DEPLOYMENT_REPORT'):
        private_write(Path(folder) / (name + '.json'), json.dumps(report, ensure_ascii=False, indent=2))
        private_write(Path(folder) / (name + '.md'), render(report, name.replace('_', ' ')))
