# Test results report

Updated: 2026-11-07 | Python 3.14.4 / Windows 11

Actual unittest result: **168/168 passed (100% of executed tests)**. Local audit checks: **51/51 passed**; this includes the unittest command and must not be added to its test count. YAML: **110/110 parsed**, duplicate-key detection enabled.

Reproduce from the repository root:

```bash
python -B tools/audit_local.py --output docs/evidence/local-rerun
```

Use a new output directory to preserve prior evidence. The tool runs tests and non-mutating CLI plans plus AST/Bash syntax checks. It does not install software or run infrastructure. The runner also parses tracked YAML with duplicate-key detection. [Raw summary](evidence/2026-11-07/summary.json), [test log](evidence/2026-11-07/unittest.log), [YAML results](evidence/2026-11-07/yaml-check.json).

CLI plan exit 0 means planning succeeded, not a healthy deployment. Missing version and invalid port correctly return 2. Menu construction does not prove interactive behavior. Mock-based tests do not prove external services.

Not executed: Ubuntu package installation; Docker/Compose deployments and networking; Odoo17/18/19 initialization/authentication; PostgreSQL15/16/17/18 live matrix; pgvector; DNS/SSL; Ansible runtime; Jenkins CI/CD jobs; live pgAdmin/Portainer; actual backup/restore and attachment integrity; complete interactive TUI; Python3.10/3.11/3.12 runtime matrix; security vulnerability scan. User confirmed no isolated test environment.

Status remains **NOT READY**; see [remaining defects](FINAL_PRODUCTION_READINESS_REPORT.md).

The new offline restoration test initially failed on Windows because pwd was imported before its Linux-only ownership branch. The import was moved into that branch and the complete suite was rerun successfully. The earlier failure is preserved in `evidence/2026-11-07/unittest-before-portable-import-fix.log`.

Active document links: 141 checked; archive integrity: 36 original document hashes checked. See [document validation](evidence/2026-11-07/document-validation.json).
