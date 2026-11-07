# Documentation Index

> **Last updated:** 2026-11-07  
> **Project:** `Infrastructure-manage-T` / DevOpsInfrastructureOdoo  
> **Overall status:** **NOT READY** (no verified live Ubuntu/Docker/Ansible/Jenkins/Odoo/PostgreSQL/Traefik E2E integration evidence in this workspace)

## Mandatory Governance (read before changes)

| Document | Purpose | Status |
|---|---|---|
| [AI_DEVELOPMENT_RULES.md](AI_DEVELOPMENT_RULES.md) | Mandatory pre-work rules for AI/developers | Current |
| [DEVELOPMENT_METHODOLOGY.md](DEVELOPMENT_METHODOLOGY.md) | 8-phase delivery + 7-stage infrastructure workflow | Current |
| [MASTER_SYSTEM_DOCUMENTATION.md](MASTER_SYSTEM_DOCUMENTATION.md) | Central system reference (architecture, workflow, operations, evidence limits) | Current (evidence-limited) |

## Mandatory Delivery Reports

| Document | Purpose | Status |
|---|---|---|
| [INTEGRATION_AND_OPERATION_SUCCESS_REPORT.md](INTEGRATION_AND_OPERATION_SUCCESS_REPORT.md) | Integration/operation evidence (only verified claims) | Current — **NOT VERIFIED** (no isolated live runtime) |
| [FINAL_INFRASTRUCTURE_DEPLOYMENT_REPORT.md](FINAL_INFRASTRUCTURE_DEPLOYMENT_REPORT.md) | Final infrastructure/deployment status | Current — **NOT READY / NOT VERIFIED** |
| [WORKFLOW_IMPLEMENTATION_REPORT.md](WORKFLOW_IMPLEMENTATION_REPORT.md) | Workflow implementation/evidence mapping | Current (code/test evidence; runtime NOT VERIFIED) |
| [TEST_RESULTS_REPORT.md](TEST_RESULTS_REPORT.md) | Actual test/validation results | Current (local evidence) |
| [DOCUMENTATION_UPDATE_REPORT.md](DOCUMENTATION_UPDATE_REPORT.md) | Documentation changes, preserved/protected files, validation | Current (this pass) |

## Operational / Technical References

| Document | Purpose | Status |
|---|---|---|
| [architecture.md](architecture.md) | Architecture overview | Current reference |
| [security.md](security.md) | Security/hardening guidance | Current reference |
| [disaster-recovery.md](disaster-recovery.md) | Backup/restore/DR guidance | Current reference (restore drills NOT VERIFIED here) |
| [FINAL_PRODUCTION_READINESS_REPORT.md](FINAL_PRODUCTION_READINESS_REPORT.md) | Production readiness blockers | Current — **NOT READY** |
| [PROJECT_LANGUAGE_MIGRATION_REPORT.md](PROJECT_LANGUAGE_MIGRATION_REPORT.md) | Arabic→English migration status (prior pass) | Historical/contextual |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Implementation planning notes | Review before use (may contain stale assumptions) |
| [SYSTEM_AUDIT_2026-11-05.md](SYSTEM_AUDIT_2026-11-05.md) | System audit | Historical — verify before relying on findings |
| [REVIEW_RECHECK_2026-11-05.md](REVIEW_RECHECK_2026-11-05.md), [REVIEW_THIRD_2026-11-05.md](REVIEW_THIRD_2026-11-05.md) | Review reports | Historical |

## Evidence / Archive

| Path | Purpose | Status |
|---|---|---|
| [evidence/2026-11-07/summary.json](evidence/2026-11-07/summary.json) | Local audit/check summary | Evidence artifact |
| [evidence/2026-11-07/document-inventory.json](evidence/2026-11-07/document-inventory.json) | Document inventory | Evidence artifact |
| [archive/2026-11-07/ARCHIVE_NOTICE.md](archive/2026-11-07/ARCHIVE_NOTICE.md) | Archive notice | Historical |
| [archive/2026-11-07/manifest.json](archive/2026-11-07/manifest.json) | Archived document hashes | Historical integrity |

## Deployment Command Docs (Protected)

The following `deployment/**/Installing*.Command.md` files are **protected by user instruction** in this task (no content changes unless separately approved): `ansible/InstallingAnsible.Command.md`, `docker/Installing Docker.Command.md`, `jenkins/Installing Jenkins.Command.md`, `odoo17/InstallingOdoo 17.0Command.md`, `odoo18/InstallingOdoo 18.0Command.md`, `portainer/Installing Portainer.Command.md`, `python/Installing Python.Command.md`, `traefik/Installing Traefik.Command.md`. `odoo19/InstallingOdoo 19.0Command.md` was modified only by explicit prior user request (restore naming/curl commands). Historical F/N/T audit IDs remain in archived audit reports and are **not** represented as fully closed here.
