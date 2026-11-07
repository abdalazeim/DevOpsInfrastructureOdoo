# DevOpsInfrastructureOdoo

Version **1.1.0 Beta** · Documentation updated **2026-11-07** · **NOT READY for production**.

Terminal-only Python CLI/TUI for inspecting and managing Ubuntu infrastructure, Docker Compose, Odoo 17/18/19, PostgreSQL, Traefik and optional Jenkins. React and an application API server are not required. Odoo, Portainer and Jenkins retain their own web interfaces.

## Start from the repository root

```bash
python -m pip install -e .
python -B app/main.py --help
python -B app/main.py --action validate
python -B app/main.py --action final-workflow --odoo-version 17 --mode local --dry-run
python -B app/main.py
```

Dependency installation is a setup instruction, not a command executed during this audit. CLI help, profile validation and the final-workflow dry run were executed locally. Interactive menus were construction-tested; all interactive actions were not exercised live.

The final workflow selects exactly one Odoo version. Dry run plans commands and does not certify installation or connectivity. Actual installation requires an Ubuntu target, a reviewed profile and `--apply`.

- [System, installation and maintenance guide](docs/MASTER_SYSTEM_DOCUMENTATION.md)
- [Documentation index](docs/DOCUMENTATION_INDEX.md)
- [Final readiness report](docs/FINAL_PRODUCTION_READINESS_REPORT.md)
- [Executed checks and limitations](docs/TEST_RESULTS_REPORT.md)
- [Backup and recovery](docs/disaster-recovery.md)

No isolated Ubuntu environment was available. Docker, database, TLS, Ansible, Jenkins and restoration acceptance remain unexecuted. Do not use a successful local test run as production acceptance.
