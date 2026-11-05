# Infrastructure Manager

The Django web application is the authenticated control plane for infrastructure inventory and approved automation. The CLI/TUI and older Python workflows remain separate legacy interfaces; the web dashboard does not invoke their arbitrary command or workflow payloads.

## Implemented modules

- Overview: configured service inventory, container counts, CPU/memory/disk data, historical samples, recent alerts and Semaphore runs.
- Docker: opt-in local engine inventory for containers/images/networks/volumes/Compose, bounded redacted logs, and typed container lifecycle actions dispatched through Task Manager. Docker write operations remain disabled by default.
- Service catalog: Odoo, Django projects, PostgreSQL, Redis, and Traefik inventory. Unknown provider state remains unknown; hostnames found in old documentation are not treated as verified live infrastructure.
- Server inventory: one canonical `ManagedHost` record shared by related modules, with groups, tags, protected credential references, current Linux snapshot, and durable synchronization history. Local Linux discovery collects read-only system, CPU, memory, filesystem/block-device, interface/route/DNS/socket, provider, security-context, sensor, service, and process data. Per-section status and freshness distinguish missing measurements from real zero values; filesystem data remains compatible through the `disks` list. `/api/v1/servers/` exposes the same inventory with granular permissions and never returns credential material.
- Monitoring: local procfs or a configured Prometheus Node Exporter source. `collect_infra_metrics` stores samples, evaluates enabled threshold rules, sends optional email, and prunes samples older than 30 days.
- Backups: opt-in policy/artifact inventory and approved Semaphore backup/restore templates. Live restore requires a successful dry-run of the same artifact, template, and variables, plus a dedicated `backup_restore` permission, checkbox confirmation, and typing `RESTORE`. This release does not manipulate backup files directly.
- Automation: administrator-approved Semaphore templates with a single exact managed-host limit, schema-validated variables encrypted at rest, dry-run by default, and confirmed live runs through typed Infrastructure Engine tasks. Optional schedules are dry-run-only and maintain linked run/task history.
- Tasks: durable database-backed state and bounded/redacted logs, typed Infrastructure Engine dispatch, optional Celery/Redis worker, and authenticated `/api/v1/tasks/` list/detail/cancel/retry endpoints. Cancellation and retry are permission-gated; unsupported task interruption is reported as a request, not a completed cancellation.
- Security: Django session login, existing role/permission service, dashboard-managed host/service/template records, and an audit log page. Django Admin is not installed or routed.

## Initial setup

1. Install the pinned application dependencies, copy `.env.example` to `.env`, set a unique `SECRET_KEY`, and configure the database.
2. Run `python manage.py migrate`, create a superuser for the dashboard, and run `python manage.py runserver` for local development.
3. Use Dashboard → Hosts & services to register a `ManagedHost` and its `ManagedService` records. Use exact verified values. Mark a host `is_local` only if the Django process is actually on that host.
   Create server groups and tags in the inventory page, then assign them when registering or editing a host. Each live discovery attempt is retained in that host's synchronization history; missing provider data is shown as unavailable rather than zero.
4. For local Docker discovery, set `INFRA_DOCKER_READ_ENABLED=True` only after reviewing the host-level privilege granted by the Docker socket. Docker's socket does not provide application-level read-only access control; a process that can access it can generally control the daemon. Keep `INFRA_DOCKER_WRITE_ENABLED=False` unless the operator has explicitly accepted that risk and configured the task worker and separate action permissions.
5. For Prometheus metrics, set `PROMETHEUS_URL` to the trusted Prometheus base URL and set the exact Node Exporter label on each host's `prometheus_instance` field. `collect_infra_metrics` can then be run from a scheduler at the desired interval.
6. For Semaphore, set `SEMAPHORE_URL`, `SEMAPHORE_API_TOKEN`, and the bounded `SEMAPHORE_TIMEOUT_SECONDS`. Run `python manage.py sync_semaphore_catalog` to import templates disabled, then assign each template an enabled `ManagedHost` with one exact Semaphore inventory alias in `ansible_limit` before approving it in Dashboard → Automation templates. Declare allowed variable names and types in the template catalog. Values are encrypted at rest; secret-like variable names are rejected and playbook output remains redacted.
7. To use scheduled dry-runs, enable Task Manager dispatch and configure the Celery/Redis worker as described in `docs/operations/TASK_WORKER.md`. Run `python manage.py dispatch_due_automation_schedules` every minute from cron or a systemd timer. Schedules require an active creator, enabled approved template, and are always dry-run; missed intervals are not replayed.
8. For scheduled live backups, enable only the intended `BackupPolicy` after reviewing its approved template and retention behavior. Run `python manage.py dispatch_due_backup_policies` every minute from cron or a systemd timer. Policies are disabled by default; scheduler sends are re-authorized as the policy creator, and missed intervals are not replayed.
9. Configure the Django email backend and `DEFAULT_FROM_EMAIL`, then run `python manage.py dispatch_pending_notifications` every minute from cron or a systemd timer. Users with access to an event category receive in-app notifications by default and can enable email delivery in Dashboard → Notifications. Mail failures are retried up to five times with backoff; the alert collector does not perform SMTP requests.
10. Grant `reports.view` together with the corresponding source permission, and `reports.export` for downloads. Dashboard → Reports reads current records; exports are synchronous and limited to 5,000 CSV rows or 300 PDF rows.

## Configuration

| Setting | Default | Purpose |
| --- | --- | --- |
| `INFRA_DOCKER_READ_ENABLED` | `False` | Opt in to local read-only Docker discovery |
| `INFRA_DOCKER_WRITE_ENABLED` | `False` | Additional gate for explicitly confirmed, task-dispatched container lifecycle actions |
| `PROMETHEUS_URL` | empty | Trusted Prometheus base URL |
| `SEMAPHORE_URL` | empty | Semaphore API base URL |
| `SEMAPHORE_API_TOKEN` | empty | Semaphore bearer token; store outside source control |
| `SEMAPHORE_TIMEOUT_SECONDS` | `8` | Bounded Semaphore request timeout |
| `CREDENTIAL_ENCRYPTION_KEY` | empty | Fernet key; required to persist automation variables or credentials |
| `TRAEFIK_API_URL` | empty | Trusted Traefik API base URL; HTTPS required for remote endpoints |
| `TRAEFIK_API_TOKEN` | empty | Optional bearer token for the read-only Traefik API |

## Operational boundaries

- There are no arbitrary shell, SQL, Docker mutation, or direct file deletion controls in the web interface. Restore can only be requested through an approved Semaphore template with a separate permission and double confirmation.
- Live changes can only be launched through a specific enabled Semaphore template that an authorized manager has marked writable; a second confirmation is required. Discovery templates are dry-run only.
- Ansible playbooks and inventory definitions are still maintained in Semaphore. This application exposes only approved templates and a single exact managed-host limit; it does not accept playbook files, arbitrary Ansible arguments, or broad inventory expressions.
- The legacy stdlib API binds only to loopback and rejects operation creation. Use the authenticated Django dashboard for approved automation.
- The dashboard needs real provider configuration to show operational status. Empty inventory or unconfigured providers are expected on a fresh install.
- Backup schedules are metadata. Configure an OS scheduler for metrics collection and `dispatch_due_automation_schedules`; no background worker is bundled.
- Notification email uses the configured Django Email backend and a durable outbox. Schedule `dispatch_pending_notifications` to deliver queued messages; missing email configuration is recorded as a delivery failure and is not reported as successful.
- Reports use live source data, add no duplicate records, and audit only successful downloads. CSV formula-like cells are neutralized; PDF generation uses the ReportLab dependency.
- The Traefik view reads routers, services and middlewares from the optional API provider. Traefik's standard API response does not expose certificate expiry here; expiry alerts still require a certificate metrics/provider integration.

## Verification

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

The test suite uses an isolated in-memory database. Infrastructure and queue adapters are mocked; no test contacts Docker, Prometheus, Semaphore, or Redis. Production broker/worker and Semaphore connectivity must be verified in the deployment environment before enabling dispatch or schedules.
