# Test Results Report

> **Last updated:** 2026-11-07  
> **Governance:** [DEVELOPMENT_METHODOLOGY.md](DEVELOPMENT_METHODOLOGY.md) · Evidence-based status only.

## 1. Summary

| Check | Result | Status | Notes |
|---|---|---|---|
| `python -m compileall -q app` (2026-11-07, local) | Exit 0 | **SUCCESS** | Syntax/bytecode compile check |
| `python -m pytest -q` (2026-11-07, local) | `168 passed in 3.73s` | **SUCCESS** | Local unit/regression tests; mock-heavy where applicable |
| Prior audit evidence bundle | Recorded | **PARTIAL** | [evidence/2026-11-07/summary.json](evidence/2026-11-07/summary.json), logs, YAML/document checks as stored |
| Ubuntu/Docker/Compose/Odoo/PostgreSQL/Traefik/Ansible/Jenkins E2E | Not executed | **NOT VERIFIED** | No isolated live target |
| Backup restore drill (isolated) | Not executed | **NOT VERIFIED** | Safety constraint |
| TUI interactive full flow | Not fully executed | **NOT VERIFIED** | Menu construction/tests do not prove all interactive behavior |
| Python 3.10/3.11/3.12 matrix | Not executed in this pass | **NOT VERIFIED** | Local rerun used available Python environment |

## 2. Reproduce (Safe, Local)

```bash
python -m compileall -q app
python -m pytest -q
```

Optional (non-mutating, preserves prior evidence by using a new output dir): `python -B tools/audit_local.py --output docs/evidence/local-rerun`

## 3. Interpretation Rules

- CLI/dry-run/plan exit codes can indicate planning/validation behavior, **not** deployment or integration success.
- Mock-based tests **do not** prove external service connectivity.
- Do not report `SUCCESS` for integration/deployment without target runtime evidence.

## 4. Historical Notes (Preserved)

The 2026-11-07 evidence directory records prior local checks (including a Windows-portable import fix rerun; see `evidence/2026-11-07/unittest-before-portable-import-fix.log` if present). Active document/archive validation counts in prior evidence remain historical artifacts; use current index/governance docs for authoritative process.

