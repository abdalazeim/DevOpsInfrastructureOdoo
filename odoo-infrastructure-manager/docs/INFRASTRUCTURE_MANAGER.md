# Infrastructure Manager

The Django web application is the authenticated control plane for infrastructure inventory and approved automation. The CLI/TUI and older Python workflows remain separate legacy interfaces; the web dashboard does not invoke their arbitrary command or workflow payloads.

## Implemented modules

- Overview: configured service inventory, container counts, CPU/memory/disk data, historical samples, recent alerts and Semaphore runs.
- Docker: opt-in, bounded read-only container/image/network/volume/Compose discovery and container logs. It never starts, stops, deletes, or executes inside a container.
- Service catalog: Odoo, Django projects, PostgreSQL, Redis, and Traefik inventory. Unknown provider state remains unknown; hostnames found in old documentation are not treated as verified live infrastructure.
- Monitoring: local procfs or a configured Prometheus Node Exporter source. `collect_infra_metrics` stores samples, evaluates enabled threshold rules, sends optional email, and prunes samples older than 30 days.
- Backups: policy/artifact inventory and approved Semaphore backup/restore templates. Restore requires a dedicated `backup_restore` permission, dry-run review, checkbox confirmation, and typing `RESTORE`. This release does not manipulate backup files directly.
- Automation: enabled administrator-approved Semaphore templates only, dry-run by default, explicit confirmation for live runs, constrained inventory limit, run audit, and sanitized task output.
- Security: Django session login, existing role/permission service, dashboard-managed host/service/template records, and an audit log page. Django Admin is not installed or routed.

## Initial setup

1. Install the pinned application dependencies, copy `.env.example` to `.env`, set a unique `SECRET_KEY`, and configure the database.
2. Run `python manage.py migrate`, create a superuser for the dashboard, and run `python manage.py runserver` for local development.
3. Use Dashboard → Hosts & services to register a `ManagedHost` and its `ManagedService` records. Use exact verified values. Mark a host `is_local` only if the Django process is actually on that host.
4. For local Docker discovery, set `INFRA_DOCKER_READ_ENABLED=True` only after limiting the Django process's Docker socket/group permissions to read-only operations externally. Docker socket access is effectively host-level privilege; application read-only commands do not make a writable Docker socket safe.
5. For Prometheus metrics, set `PROMETHEUS_URL` to the trusted Prometheus base URL and set the exact Node Exporter label on each host's `prometheus_instance` field. `collect_infra_metrics` can then be run from a scheduler at the desired interval.
6. For Semaphore, set `SEMAPHORE_URL`, `SEMAPHORE_API_TOKEN`, and the bounded `SEMAPHORE_TIMEOUT_SECONDS`. Run `python manage.py sync_semaphore_catalog` to import templates disabled, then review and approve them in Dashboard → Automation templates. The installed Semaphore version and credentials are environment-specific and must be configured by the operator.
7. Configure SMTP and `INFRA_ALERT_EMAILS` to enable alert mail. Without SMTP, events remain visible in the dashboard.

## Configuration

| Setting | Default | Purpose |
| --- | --- | --- |
| `INFRA_DOCKER_READ_ENABLED` | `False` | Opt in to local read-only Docker discovery |
| `PROMETHEUS_URL` | empty | Trusted Prometheus base URL |
| `SEMAPHORE_URL` | empty | Semaphore API base URL |
| `SEMAPHORE_API_TOKEN` | empty | Semaphore bearer token; store outside source control |
| `SEMAPHORE_TIMEOUT_SECONDS` | `8` | Bounded Semaphore request timeout |
| `INFRA_ALERT_EMAILS` | empty | Optional alert recipients |
| `TRAEFIK_API_URL` | empty | Trusted Traefik API base URL; HTTPS required for remote endpoints |
| `TRAEFIK_API_TOKEN` | empty | Optional bearer token for the read-only Traefik API |

## Operational boundaries

- There are no arbitrary shell, SQL, Docker mutation, or direct file deletion controls in the web interface. Restore can only be requested through an approved Semaphore template with a separate permission and double confirmation.
- Live changes can only be launched through a specific enabled Semaphore template that an authorized manager has marked writable; a second confirmation is required. Discovery templates are dry-run only.
- The legacy stdlib API binds only to loopback and rejects operation creation. Use the authenticated Django dashboard for approved automation.
- The dashboard needs real provider configuration to show operational status. Empty inventory or unconfigured providers are expected on a fresh install.
- Backup schedules are metadata. Configure an OS scheduler for metrics collection and the approved Semaphore project's own schedule for recurring automation; no background worker is bundled.
- The Traefik view reads routers, services and middlewares from the optional API provider. Traefik's standard API response does not expose certificate expiry here; expiry alerts still require a certificate metrics/provider integration.

## Verification

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.dashboard.tests.test_dashboard
```

The test suite uses an isolated in-memory database. No test contacts Docker, Prometheus, or Semaphore.
