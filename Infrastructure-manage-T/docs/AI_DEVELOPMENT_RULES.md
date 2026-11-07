# AI Development Rules (Mandatory Reference)

> **Status:** Mandatory for any AI/developer agent before starting work.  
> **Last updated:** 2026-11-07  
> **Read first:** This file, then [DEVELOPMENT_METHODOLOGY.md](DEVELOPMENT_METHODOLOGY.md), [MASTER_SYSTEM_DOCUMENTATION.md](MASTER_SYSTEM_DOCUMENTATION.md), [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md), and task-specific docs.

## 1. Non-Negotiable Principles

1. **No execution before understanding.** Inspect the project, affected files, current behavior, and prior audit/repair reports first.
2. **No modification before planning.** Produce a clear plan, scope, dependencies, and verification approach.
3. **No integration claim before operation verification.** Installation success ≠ operation success ≠ integration success.
4. **No success claim without actual evidence.** Use `SUCCESS`/`FAILED`/`PARTIAL SUCCESS`/`SKIPPED`/`NOT VERIFIED` truthfully.

## 2. Required Pre-Work Checklist

- [ ] Identify the task type (docs, code, config, infra, test, report).
- [ ] Read relevant docs and recent evidence/reports.
- [ ] Locate authoritative implementation paths (CLI/workflows/services/templates/deployment assets).
- [ ] Identify duplicates/conflicts/historical docs; preserve correct information.
- [ ] Confirm data-safety constraints and protected files (e.g., user-specified deployment command docs must not be changed unless explicitly approved).
- [ ] Define what will **not** be changed.

## 3. Execution Rules

- Follow the 8-phase cycle: Discovery → Planning → Design → Implementation → Verification → Testing → Documentation → Delivery.
- Follow the 7-stage infrastructure cycle when applicable: System Preparation → Sequential Installation → Operation Verification → Integration & Connectivity → Integration Success Report → Final Deployment Report → Documentation Synchronization.
- Make minimal, reversible-minded changes. Preserve existing functionality, settings, and data.
- Prefer evidence from actual command output, tests, logs, and runtime checks. If unavailable, mark `NOT VERIFIED`.
- Do not run destructive or production-impacting commands without explicit approval.

## 4. Documentation Rules

- Do not modify executable code/config during a documentation-only task unless separately approved.
- Update docs to match actual behavior; remove contradictions; do not document unimplemented features as complete.
- Archive historical docs instead of deleting important context; label them non-authoritative.
- Keep links valid and add cross-references.

## 5. Protected/Sensitive Areas

- **Never modify without explicit approval:** databases/volumes/backups data contents, secrets, production credentials, user-designated protected docs (including deployment `Installing*.Command.md` files called out by the user).
- **Security:** no `chmod 777`, no secret leakage, least privilege, review exposed admin interfaces.
- **Backups/restores:** validate integrity; test restores only in isolated environments.

## 6. Delivery Report Requirements

Every substantial delivery must state:
- What was scanned/understood
- What changed (files/sections)
- What was intentionally not changed
- Verification performed and actual results
- Remaining risks, blockers, and `NOT VERIFIED` items
- Next safe actions

## 7. Prohibited Behaviors

- Guessing success, versions, connectivity, or runtime state.
- Rebuilding the project from scratch without approval.
- Deleting databases, Docker volumes, or backups.
- Hiding errors, partial failures, or skipped checks.
- Making broad refactors unrelated to the approved scope.