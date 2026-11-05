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
- REST task endpoints are available under `/api/v1/tasks/`; reads require `task.view`, cancellation requires `task.cancel`, and retry requires `task.retry` plus a fresh authorization check for the original operation.
- Cancellation of pending/queued work prevents execution. Cancellation requested after a worker starts is recorded honestly; operations without cooperative cancellation are not falsely reported as stopped.
- Manual retry is limited to failed/timed-out tasks with attempts remaining. It revalidates the operation before publishing and never runs inline if the queue is unavailable.
- Schedule `venv/bin/python manage.py reconcile_stale_tasks` at least once per minute. It marks tasks left running beyond the operation timeout plus a recovery margin as timed out; it does not blindly retry an operation whose completion is uncertain.
- Celery's result backend is not used. The application task UUID, status transitions, audit rows, and bounded/redacted logs are authoritative.
- Only explicitly registered operations can run. The registry includes read-only server probes/discovery, confirmed local systemd and Docker actions, and `automation.template.execute`. Automation workers revalidate the active actor, execute permission, approved-template state, exact managed-host limit, encrypted variables, and confirmation before requesting Semaphore to start the external task. The local task records dispatch acceptance; `AutomationRun` remains the source for the remote Semaphore execution state.
- Approved Semaphore templates can have dry-run schedules. Configure `python manage.py dispatch_due_automation_schedules` to run once per minute; it only creates typed queued tasks, never runs playbooks inline, and never schedules live operations. The schedule command records failures and advances its interval rather than repeatedly replaying missed intervals.

## Verification limits

The repository tests cover disabled dispatch, publish failure, task persistence, worker-side policy revalidation, duplicate delivery, retry/cancellation, task REST permissions and payloads, and stale-task reconciliation. They mock the broker publication. A deployment must separately verify Redis connectivity, worker startup, and task completion against its own broker and host credentials before enabling dispatch.
