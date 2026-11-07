# Development Methodology (Mandatory)

> **Status:** Current reference (governance).  
> **Last updated:** 2026-11-07  
> **Applies to:** All developers and AI systems working on `DevOpsInfrastructureOdoo` / `Infrastructure-manage-T`.  
> **Related:** [AI_DEVELOPMENT_RULES.md](AI_DEVELOPMENT_RULES.md), [MASTER_SYSTEM_DOCUMENTATION.md](MASTER_SYSTEM_DOCUMENTATION.md), [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)

## 1. Purpose

This document defines the required development and delivery lifecycle for code, configuration, documentation, and infrastructure changes. It prevents unplanned refactors, unverified success claims, and data-destructive operations.

## 2. Mandatory Work Cycle

Every task must follow these phases in order. A phase may be lightweight for small, low-risk changes, but it must not be skipped silently.

| Phase | Name | Required Output | Exit Criteria |
|---:|---|---|---|
| 1 | **Discovery** | Current-state summary, affected files/components, existing behavior to preserve | Facts are grounded in repository/code/config evidence |
| 2 | **Planning** | Scope, dependencies, risks, rollback/safety notes, verification plan | Plan reviewed against constraints (no unnecessary rebuilds, data protection) |
| 3 | **Design** | Target behavior, interfaces/contracts, impacted modules, compatibility notes | Design fits existing architecture unless approved change |
| 4 | **Implementation** | Minimal, incremental changes; no unrelated churn | Changes preserve prior functionality and data |
| 5 | **Verification** | Commands/logs/evidence for what was checked | Each change has explicit PASS/FAIL/NOT VERIFIED status |
| 6 | **Testing** | Unit/integration/regression/E2E as applicable | Tests executed are reported with actual results; missing tests are NOT VERIFIED |
| 7 | **Documentation** | Updated docs, changelog/report entries, links | Docs match actual implementation/evidence |
| 8 | **Delivery** | Final report: changes, files, results, risks, next actions | No success claim without evidence |

**Rule:** Do not declare success without actual verification/testing evidence.

## 3. Infrastructure Execution Cycle (Official)

Infrastructure work must be documented and executed (when authorized and safe) using this ordered cycle:

| Stage | Name | Key Checks |
|---:|---|---|
| 1 | **System Preparation** | OS identity, resources, privileges, existing installs, ports, backups, profile review |
| 2 | **Sequential Installation** | Dependency order, reuse existing components, no blind reinstall, dry-run support |
| 3 | **Operation Verification** | Services/containers/daemons/HTTP/DB readiness; independent from install completion |
| 4 | **Integration & Connectivity** | Real connectivity/functional checks between components; no “config exists = integrated” |
| 5 | **Integration Success Report** | Evidence-based report; SUCCESS only with documented tests |
| 6 | **Final Deployment Report** | End-to-end status, versions, risks, blockers, RTO/RPO/ops notes as available |
| 7 | **Documentation Synchronization** | Docs, index, archive labels, and reports aligned with actual state |

### Components in Scope
Ubuntu, Python, Git, Docker, Docker Compose, PostgreSQL, Odoo 17/18/19, Traefik, Ansible, Jenkins, Portainer, and supporting services.

### Dependency/Reuse Rules
- Detect and reuse working components; do not reinstall without necessity and approval.
- Respect dependencies (e.g., Docker before Compose workflows that require it; PostgreSQL/Odoo integration only after operational checks).
- Continue independent safe tasks when possible; never bypass a failed required dependency.

## 4. Verification & Integration Standards

| Area | Minimum Evidence (examples) | Not Sufficient Alone |
|---|---|---|
| Docker/Compose | `docker info`, `docker compose version`, `docker ps`, network/volume inspection (when safe) | Compose file exists |
| PostgreSQL↔Odoo | DB readiness, authenticated/app-level connectivity tests, container/log checks | Container started |
| Odoo HTTP | HTTP probe/login/page response on target | Process running |
| Traefik | Router/service discovery, routing tests, TLS checks when enabled | Static config exists |
| Ansible | Inventory validity, syntax check, connectivity/playbook dry/safe tests | Playbook file exists |
| Jenkins | Service/UI availability, credentials/agent/integration checks as authorized | Container started |
| Backup/Restore | Integrity checks; restore drill in isolated environment | Backup file created |
| Security | Permissions, secrets handling, exposure review, no `chmod 777` | Assumed secure defaults |

## 5. Status Vocabulary (Reports)

Use only: `SUCCESS`, `FAILED`, `PARTIAL SUCCESS`, `SKIPPED`, `NOT VERIFIED` (and `PARTIALLY_CONNECTED` where integration granularity is needed). Every non-trivial claim must cite evidence or be marked `NOT VERIFIED`.

## 6. Safety Controls

- No rebuild-from-scratch unless explicitly approved.
- Preserve code, data, DBs, volumes, backups, and existing configs.
- No destructive operations (`docker compose down -v`, volume/DB deletion, mass restarts) without explicit approval and backups.
- No `chmod 777`. No secrets in logs/docs/Git.
- Do not change domains/hostnames/IPs arbitrarily.
- Documentation-only tasks must not modify executable code/config unless separately approved.

## 7. Documentation Quality

- Technical docs in English; concise theory, detailed practical steps.
- Use tables, Mermaid diagrams/flowcharts/dependency graphs, checklists, command blocks.
- Keep terms/headings consistent; add correct internal links.
- Mark historical docs as archived/non-authoritative; do not delete valuable history.
- Add/update “Last updated” dates where maintained.

## 8. Definition of Done

A task is complete only when:
1. Requested scope is implemented or explicitly bounded.
2. Verification/testing evidence is recorded.
3. Documentation/reports are synchronized.
4. Risks, blockers, and NOT VERIFIED items are disclosed.