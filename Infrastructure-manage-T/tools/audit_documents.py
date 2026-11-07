"""Check active local document links and preserved historical document hashes."""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    errors, links = [], 0
    files = (list(ROOT.glob('*.md')) + list(ROOT.glob('*.txt')) +
             list((ROOT / 'docs').glob('*.md')) + list((ROOT / 'docs').glob('*.txt')) +
             list((ROOT / 'deployment').rglob('*.md')))
    for path in files:
        for match in re.finditer(r'\[[^\]]*\]\((?:<([^>]+)>|([^\s)]+))\)', path.read_text(encoding='utf-8-sig')):
            link = match.group(1) or match.group(2)
            if '://' in link or link.startswith('#'):
                continue
            links += 1
            if not (path.parent / link.split('#')[0]).exists():
                errors.append(dict(file=path.relative_to(ROOT).as_posix(), target=link))
    manifest = json.loads((ROOT / 'docs/archive/2026-11-07/manifest.json').read_text(encoding='utf-8'))
    for item in manifest:
        path = ROOT / item['archive']
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            errors.append(dict(hash_mismatch=item['archive']))
    result = dict(links_checked=links, archive_hashes_checked=len(manifest), errors=errors, passed=not errors)
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    result = main()
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2), encoding='utf-8')
    sys.exit(0 if result['passed'] else 1)
