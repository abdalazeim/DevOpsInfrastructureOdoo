# Completion implementation plan

Updated: 2026-11-07. Input: both attached workflow specifications.

1. Repair shared execution gates in `app/core/installation_pipeline.py`: reject invalid dependency graphs, retain inspection evidence, distinguish a missing runtime from an unhealthy installed runtime, record completed inspections, and avoid interactive sudo in captured execution.
2. Strengthen `app/services/managed_stack.py`: preserve existing configuration/volumes, start/authenticate PostgreSQL before Odoo, initialize only a newly created database, and verify the selected database and HTTP endpoint.
3. Extend `app/core/final_workflow.py` using the current profile: measured preparation, structured component/integration records, safe Ansible verification, authenticated Jenkins evidence, accurate progress, resume, Markdown/JSON reports and documentation references.
4. Route existing CLI/TUI deployment entry points and the main Ansible playbook through the shared deployment contract. Preserve standalone legacy assets and existing data; require explicit migration for incompatible layouts.
5. Complete architecture, dependency, component verification, error recovery and report documentation. Keep historical evidence intact.
6. Add regressions for actual failure modes, run the local audit and document unexecuted Ubuntu/service tests. No production readiness claim without live evidence.

No isolated Ubuntu target is available. Local tests use temporary files and mocks. No production services, data, volumes, domains or network attachments will be changed by this development work.
