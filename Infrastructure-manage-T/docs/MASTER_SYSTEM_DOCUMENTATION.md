# Master system documentation

Updated: 2026-11-07 | Version 1.1.0 Beta | **NOT READY**

> **Governance:** [AI_DEVELOPMENT_RULES.md](AI_DEVELOPMENT_RULES.md) and [DEVELOPMENT_METHODOLOGY.md](DEVELOPMENT_METHODOLOGY.md) are mandatory for changes. Use [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) to locate current vs. historical references. Evidence-based status only: `SUCCESS` / `FAILED` / `PARTIAL SUCCESS` / `SKIPPED` / `NOT VERIFIED`.


## Scope and entry points

Run commands from the repository root. `app/main.py` is the CLI entry point; `app/ui/app.py` and `app/ui/textual_app.py` provide terminal interfaces. No React frontend or manager API server is needed. Managed services such as Odoo still expose their own HTTP endpoints.

The canonical reviewed orchestration path is `final-workflow`. `sequential-install` and `server-setup` share profile-driven definitions, but do not themselves provide all seven acceptance phases. Legacy `prep`, `traefik`, `odoo17`, `odoo18`, `odoo19`, `full`, standalone shell scripts and deployment playbooks remain separate implementations. They are retained for compatibility, not certified equivalent to the canonical path. Do not combine deployment layouts against the same data directories.

## Configuration and dependencies

`profiles/example.yaml` is an example, not a production inventory. Copy it to a private profile and review server, data_root, backup_root, proxy network/subnet, deployment_mode, selected Odoo image/database, domain, HTTP port and Traefik ACME email. `jenkins_enabled` defaults false. No real domains or server settings were changed by this audit.

Python manager requires Python >=3.10, PyYAML and Textual. The local audit ran Python 3.14 only; Python 3.10/3.11/3.12 execution is unverified. Container Odoo Python comes from the selected image. Host runtime selection is available through the runtime setup interface; it is separate from Docker-based Odoo deployment. Do not change Ubuntu's system python3 alternative as part of an Odoo installation.

The example profile selects image pairs Odoo17/PostgreSQL16, Odoo18/PostgreSQL17 and Odoo19/PostgreSQL18. These are configuration choices, not an end-to-end compatibility certification. PostgreSQL18 uses `/var/lib/postgresql` for its named volume; older images use `/var/lib/postgresql/data`. Package/image availability, pgvector use and host compatibility require target verification.

Install manager dependencies in a virtual environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -B app/main.py --help
```

These setup commands are instructions for a future Ubuntu environment, not an installation result from this audit.

## Seven-phase operation

1. **System Preparation**: verify Ubuntu identity and inspect disk/architecture. The current preflight does not enforce a complete capacity budget. Review available memory/disk, privileges, existing installations, ports and backups before apply.
2. **Sequential Installation**: resolve dependencies; system packages, Python/Git, Docker Engine, Compose, proxy network, selected Odoo/PostgreSQL, Traefik and Ansible; Jenkins is optional. Actual order is dependency-based. Existing components are checked before installation. Failed dependencies block dependents.
3. **Operation Verification**: execute component checks; Odoo/database must be running, unpaused, healthy and match the profile image. Infrastructure checks alone do not prove application readiness.
4. **Integration & Connectivity**: authenticate Odoo to PostgreSQL with SELECT 1, check Odoo HTTP, local Traefik dashboard, and configured Ansible inventory/connectivity/syntax. Jenkins login HTTP is insufficient; its authenticated pipeline acceptance remains unimplemented.
5. **Integration Success Report**: save evidence and failures. Successful report writing does not mean integrations succeeded.
6. **Final Deployment Report**: record checks, phase states and unresolved acceptance. Mandatory restore/Ubuntu evidence remains outstanding, so the workflow currently reports NOT READY even when its checks pass.
7. **Documentation Synchronization**: verify central documents exist. This is a reference check, not automatic verification of every sentence against deployment state.

## Plan, verify, apply and resume

```bash
python -B app/main.py --profile profiles/example.yaml --action final-workflow --odoo-version 17 --mode local --dry-run
```

Dry run does not execute installation commands or write workflow reports. Its exit 0 means the plan was generated; phases remain NOT_VERIFIED and readiness remains NOT READY.

On an isolated Ubuntu target, with a reviewed private profile:

```bash
python -B app/main.py --profile profiles/reviewed.yaml --action final-workflow --odoo-version 17 --mode local --report-dir reports/staging
```

Without `--apply`, verification is read-only for infrastructure, but writes local report files. To install the reviewed plan add `--apply`. To resume that same profile/report directory add `--resume`. The state file contains a profile hash: changed profiles are rejected. Resume does not replace health/integration checks with a previous success. NOT READY returns exit 1 for a real run; missing required version returns exit 2.

`profiles/reviewed.yaml` is an operator-created example path; it is not supplied. The command does not connect to an SSH server automatically: execution is local to the machine running the manager. `server.ip_or_host` must not be mistaken for automatic remote execution.

## Managed Docker layout

`app/services/managed_stack.py` creates `<data_root>/odooXX/compose.json`, `credentials.json`, `odoo.conf` and `addons/`; Compose manages database and filestore named volumes. Secrets and Compose are mode 0600 in a 0700 parent. The mounted Odoo configuration is readable inside its container. Protect Docker administrative access: it can read container environment secrets.

Local Odoo binds loopback ports 10017/10018/10019 by default; `--http-port` overrides the selected version. PostgreSQL has no published host port. Local Traefik uses loopback 10080 and dashboard 10090. Optional managed Jenkins uses loopback 8081. Domain mode uses the reviewed Odoo domain, proxy network, Traefik 80/443 and ACME. A syntactically valid domain is not proof of DNS or TLS.

Existing complete Odoo stacks are verified without recreation; partial stacks and mismatched image names fail. Exact tag matching cannot detect a mutable tag's digest change. Existing volumes with missing containers require a reviewed recovery plan. Fresh Odoo database initialization and actual file permissions still need live acceptance.

## Optional tools and legacy paths

Docker/Compose runtime setup, Host/Docker runtime choice and Portainer are available in terminal menus. Portainer's standalone installer now generates HTTPS port 9443 and the named volume `portainer_data` (Edge 8000 is optional). The installer preserves existing containers and does not migrate an old `/srv/portainer` deployment. HTTPS/UI readiness still needs a live test. Do not migrate an existing Portainer volume implicitly. pgAdmin assets are optional and not part of the seven-phase acceptance checks. Never copy sample credentials into a deployment.

Ansible definitions exist in several deployment/automation directories. The final workflow checks `deployment/ansible/inventory/hosts.ini` and `deployment/ansible/site.yml`; an inventory must be configured explicitly. Jenkins deployment does not configure credentials, a build agent or a proven Docker/Ansible job automatically.

## Notebook and daily maintenance

The Command Notebook generates and stores commands; it does not execute them. Review generated commands before copying. Its tests cover regeneration and preservation of manual edits. Keep runtime notebook data and backups private.

Read-only checks on the target include `docker ps -a`, `docker compose version`, `docker inspect odoo17`, and component logs. Use the Compose file for the exact managed instance; never substitute legacy folder layouts. Investigate failed command exit codes and stderr before retrying. Do not use automatic volume pruning, global container removal or world-writable permissions.

Before upgrade or restore, preserve private profiles, credentials, Compose/configuration, database dumps, filestore and addons. A successful archive is not proof of restoration. See [recovery](disaster-recovery.md), [security](security.md), [tests](TEST_RESULTS_REPORT.md) and [remaining blockers](FINAL_PRODUCTION_READINESS_REPORT.md).
