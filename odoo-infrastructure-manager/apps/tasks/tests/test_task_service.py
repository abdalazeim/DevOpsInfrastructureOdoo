from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from apps.core.models import AuditLog
from apps.tasks.models import Task, TaskLog
from apps.tasks.services.task_service import (
    MAX_TASK_LOG_CHARS,
    append_task_log,
    create_task,
    request_task_cancellation,
    transition_task,
)


class TaskServiceTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser("task-admin", "task@example.test", "long-task-password")

    def make_task(self, **kwargs):
        return create_task(name="Inspect server", operation="server.inspect", actor=self.admin, **kwargs)

    def test_task_state_machine_records_attempts_and_audit(self):
        task = self.make_task(max_attempts=2)
        self.assertEqual(task.status, Task.Status.PENDING)
        task = transition_task(task.pk, Task.Status.QUEUED, actor=self.admin)
        task = transition_task(task.pk, Task.Status.RUNNING, actor=self.admin)
        self.assertEqual(task.attempt_count, 1)
        task = transition_task(task.pk, Task.Status.FAILED, actor=self.admin,
                               error_category="adapter", error_message="password=secret-value")
        self.assertNotIn("secret-value", task.error_message)
        task = transition_task(task.pk, Task.Status.QUEUED, actor=self.admin)
        task = transition_task(task.pk, Task.Status.RUNNING, actor=self.admin)
        task = transition_task(task.pk, Task.Status.COMPLETED, actor=self.admin, result_summary="Verified")
        self.assertTrue(task.is_terminal)
        self.assertTrue(task.finished_at)
        self.assertEqual(task.attempt_count, 2)
        self.assertGreaterEqual(AuditLog.objects.filter(module="tasks", object_id=str(task.pk)).count(), 6)

    def test_terminal_tasks_cannot_be_reopened(self):
        task = self.make_task()
        transition_task(task.pk, Task.Status.CANCELLED, actor=self.admin)
        with self.assertRaises(ValidationError):
            transition_task(task.pk, Task.Status.QUEUED, actor=self.admin)

    def test_retry_limit_is_enforced(self):
        task = self.make_task(max_attempts=1)
        transition_task(task.pk, Task.Status.QUEUED, actor=self.admin)
        transition_task(task.pk, Task.Status.RUNNING, actor=self.admin)
        transition_task(task.pk, Task.Status.FAILED, actor=self.admin)
        with self.assertRaises(ValidationError):
            transition_task(task.pk, Task.Status.QUEUED, actor=self.admin)

    def test_running_task_cancellation_is_requested_not_falsely_completed(self):
        task = self.make_task()
        transition_task(task.pk, Task.Status.QUEUED, actor=self.admin)
        transition_task(task.pk, Task.Status.RUNNING, actor=self.admin)
        task = request_task_cancellation(task.pk, actor=self.admin)
        self.assertEqual(task.status, Task.Status.RUNNING)
        self.assertTrue(task.cancel_requested_at)
        task = transition_task(task.pk, Task.Status.CANCELLED, actor=self.admin)
        self.assertTrue(task.is_terminal)

    def test_cancel_requires_permission(self):
        task = self.make_task()
        operator = get_user_model().objects.create_user("task-viewer", password="long-task-password")
        with self.assertRaises(PermissionDenied):
            request_task_cancellation(task.pk, actor=operator)

    def test_logs_redact_secrets_and_bound_total_size(self):
        task = self.make_task(safe_metadata={"token": "private-token", "host": "edge-1"})
        self.assertEqual(task.safe_metadata["token"], "[REDACTED]")
        append_task_log(task.pk, stream=TaskLog.Stream.STDOUT, content='password="secret-value"')
        log = task.logs.get()
        self.assertNotIn("secret-value", log.content)
        self.assertIn("[REDACTED]", log.content)
        for _ in range(MAX_TASK_LOG_CHARS // 8192):
            append_task_log(task.pk, content="x" * 8192)
        self.assertFalse(append_task_log(task.pk, content="overflow"))
        total = sum(len(row.content) for row in task.logs.all())
        self.assertLessEqual(total, MAX_TASK_LOG_CHARS)
