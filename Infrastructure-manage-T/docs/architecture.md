# Current architecture

Updated: 2026-11-07 | 1.1.0 Beta

`app/main.py` parses CLI options, loads a profile through TerminalUI and dispatches an action. `app/models/profile.py` represents infrastructure configuration. Terminal menus and optional Textual screens call services; there is no manager web/API layer.

The final workflow in `app/core/final_workflow.py` coordinates seven phases and saves evidence under the selected report directory. `app/core/installation_pipeline.py` resolves installation dependencies using definitions adapted from `app/core/server_setup.py`. `app/services/managed_stack.py` renders Compose from that profile and invokes Docker through argument lists. Selected Odoo authenticates to its own PostgreSQL service; domain mode adds a proxy network and Traefik labels. Local mode publishes loopback HTTP.

`app/services/instance_backup.py` defines the new checksummed logical database/filestore/configuration backup contract shared with MultiVersion shell/Ansible wrappers. `app/services/system_backup.py` exports configuration and SQL; restoring its archive does not automatically import live databases. Legacy shell backups use another format.

Legacy workflows under `app/workflows`, `automation/scripts` and deployment-specific Compose/Ansible assets remain parallel execution paths. They must not be assumed equivalent. The Notebook generator is intentionally separate from execution and preserves manual edits.

[Operational contract](MASTER_SYSTEM_DOCUMENTATION.md) · [Known gaps](FINAL_PRODUCTION_READINESS_REPORT.md)
