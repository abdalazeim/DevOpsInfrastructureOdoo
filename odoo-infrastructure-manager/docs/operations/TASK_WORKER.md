# Task Queue Deployment

The Task Manager stores authoritative state and bounded logs in Django's database. Celery transports only a task UUID through the configured broker; operation parameters remain in the task record. Workers load that record, check the requesting account again, and execute a registered Infrastructure Engine operation. The worker never accepts a shell command.

## Configure

Install the project requirements, run Redis on a private network, and set the same environment for the web process and worker:

```dotenv
TASK_DISPATCH_ENABLED=True
CELERY_BROKER_URL=redis://127.0.0.1:6379/1
CELERY_RESULT_BACKEND=
```

The Redis URL must include authentication and TLS when the broker is not confined to a trusted local network. Keep broker credentials in the deployment secret store. The Django database remains the source of task status and output; Celery results are ignored.

Start a worker from the project root with the same settings and database configuration:

```sh
venv/bin/celery -A config worker --loglevel=INFO --concurrency=2 --queues=infrastructure
```

Run the worker as a dedicated service account with only the operating-system and network access required by enabled adapters. Restrict Redis to the web and worker hosts. Do not expose the broker publicly.

## Runtime behavior

- Dispatch is off by default. The task center reports disabled configuration, missing dependencies, or missing broker configuration. A configured broker does not prove that a worker is alive.
- Publishing failure marks the database task failed with a sanitized transport category.
- Duplicate deliveries are ignored after a task leaves `queued`; workers recheck account state, permission, operation registration, target, and parameters through the Infrastructure Engine.
- Schedule `venv/bin/python manage.py reconcile_stale_tasks` at least once per minute. It marks tasks left running beyond the operation timeout plus a recovery margin as timed out; it does not blindly retry an operation whose completion is uncertain.
- Celery's result backend is not used. The application task UUID, status transitions, audit rows, and bounded/redacted logs are authoritative.
- Only explicitly registered operations can run. The current registry includes read-only server probes/discovery and a local systemd service restart that requires a typed confirmation and `linux.service.restart`; the restart has no web-request execution path.

## Verification limits

The repository tests cover disabled dispatch, publish failure, task persistence, worker-side policy revalidation, duplicate delivery, and stale-task reconciliation. They mock the broker publication. A deployment must separately verify Redis connectivity, worker startup, and task completion against its own broker and host credentials before enabling dispatch.
