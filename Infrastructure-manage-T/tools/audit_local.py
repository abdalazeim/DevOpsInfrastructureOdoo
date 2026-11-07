"""Reproducible local checks. Never install software or contact an infrastructure host."""
import argparse
import ast
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    destination = Path(args.output).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    results = []

    def command(name, argv, expected=0):
        started = time.monotonic()
        try:
            result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True,
                                    encoding='utf-8', errors='replace', timeout=180,
                                    env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
            output = result.stdout + '\n' + result.stderr
            code = result.returncode
        except (OSError, subprocess.SubprocessError) as exc:
            output, code = str(exc), None
        (destination / (name + '.log')).write_text(output, encoding='utf-8')
        results.append(dict(name=name, command=argv, exit_code=code,
                            expected_exit_code=expected, passed=code == expected,
                            seconds=round(time.monotonic() - started, 3)))
        return output

    output = command('unittest', [sys.executable, '-B', '-m', 'unittest', 'discover', 'tests', '-v'])
    match = re.search(r'Ran (\d+) tests', output)
    count = int(match.group(1)) if match else None
    base = [sys.executable, '-B', 'app/main.py']
    command('cli-help', base + ['--help'])
    command('cli-validate', base + ['--action', 'validate', '--dry-run'])
    command('cli-preflight-plan', base + ['--action', 'preflight', '--dry-run'])
    command('cli-final-plan', base + ['--action', 'final-workflow', '--odoo-version', '17', '--mode', 'local', '--dry-run'])
    command('cli-selection-required', base + ['--action', 'final-workflow', '--dry-run'], 2)
    command('cli-invalid-port', base + ['--action', 'final-workflow', '--odoo-version', '17', '--http-port', '0', '--dry-run'], 2)
    errors, scanned = [], 0
    for folder in ('app', 'tests', 'tools'):
        for path in (ROOT / folder).rglob('*.py'):
            scanned += 1
            try:
                ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
            except Exception as exc:
                errors.append(str(exc))
    results.append(dict(name='python-ast', passed=not errors, files=scanned, errors=errors))
    bash = shutil.which('bash') if os.name != 'nt' else 'C:/Program Files/Git/bin/bash.exe'
    shell_files = subprocess.check_output(['git', 'ls-files', '*.sh'], cwd=ROOT, text=True).splitlines()
    for number, path in enumerate(shell_files):
        command(f'shell-{number:02}', [bash, '-n', path])
    import yaml
    class UniqueKeys(yaml.SafeLoader):
        pass
    def mapping(loader, node, deep=False):
        value = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in value:
                raise ValueError('Duplicate YAML key: ' + str(key))
            value[key] = loader.construct_object(value_node, deep=deep)
        return value
    UniqueKeys.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    yaml_rows = []
    for name in subprocess.check_output(['git', 'ls-files', '*.yaml', '*.yml'], cwd=ROOT, text=True).splitlines():
        try:
            list(yaml.load_all((ROOT / name).read_text(encoding='utf-8-sig'), Loader=UniqueKeys))
            yaml_rows.append(dict(path=name, status='PASS'))
        except Exception as exc:
            yaml_rows.append(dict(path=name, status='FAIL', error=str(exc)))
    (destination / 'yaml-check.json').write_text(json.dumps(yaml_rows, indent=2), encoding='utf-8')
    results.append(dict(name='yaml-parse', files=len(yaml_rows), passed=all(r['status'] == 'PASS' for r in yaml_rows)))
    summary = dict(generated_at=datetime.now(timezone.utc).isoformat(),
                   platform=platform.platform(), python=sys.version, unit_tests=count,
                   checks=results, passed=sum(r['passed'] for r in results), total=len(results),
                   not_executed=['Ubuntu installation', 'Docker/Compose live deployment',
                       'PostgreSQL/Odoo authentication and initialization', 'Traefik DNS/TLS',
                       'Ansible runtime', 'Jenkins authenticated pipeline', 'Real backup/restore drill',
                       'Python 3.10/3.11/3.12 runtime matrix'])
    (destination / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(f"Local checks: {summary['passed']}/{summary['total']}; unit tests: {count}")
    return 0 if all(r['passed'] for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
