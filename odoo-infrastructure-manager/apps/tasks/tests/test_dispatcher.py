from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta

from apps.infrastructure.models import ManagedHost
from apps.tasks.models import Task
from apps.tasks.services.dispatcher import TaskDispatchUnavailable, enqueue_task
from apps.tasks.services.operation_tasks import queue_infrastructure_operation
from apps.tasks.services.runner import run_infrastructure_task
from infrastructure_engine.core.engine import OperationResult


class TaskDispatcherTests(TestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_superuser("queue-admin", "queue@example.test", "long-queue-password")
        self.host = ManagedHost.objects.create(name="queued-host", hostname="host.example.test")

    @override_settings(TASK_DISPATCH_ENABLED=False, CELERY_BROKER_URL="")
    def test_disabled_dispatch_never_changes_a_pending_task(self):
        task = Task.objects.create(name="Pending", operation="server.test_connection", requested_by=self.actor)
        with self.assertRaises(TaskDispatchUnavailable):
            enqueue_task(task, actor=self.actor)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.PENDING)

    @override_settings(TASK_DISPATCH_ENABLED=True, CELERY_BROKER_URL="redis://localhost/1")
    @patch("apps.tasks.services.dispatcher.publish_task")
    def test_registered_operation_is_saved_and_queued_without_arguments_to_shell(self, publish):
        with patch("apps.tasks.services.dispatcher.dispatch_status", return_value={"ready": True}), \
                patch("apps.tasks.services.operation_tasks.dispatch_status", return_value={"ready": True}):
            task = queue_infrastructure_operation(
                operation="server.test_connection", target_id=self.host.pk,
                actor=self.actor, parameters={},
            )
        self.assertEqual(task.status, Task.Status.QUEUED)
        self.assertEqual(task.operation, "server.test_connection")
        self.assertEqual(task.safe_metadata["operation_request"]["target_id"], self.host.pk)
        publish.assert_called_once_with(task.pk)

    @override_settings(TASK_DISPATCH_ENABLED=True, CELERY_BROKER_URL="redis://localhost/1")
    @patch("apps.tasks.services.dispatcher.publish_task", side_effect=OSError("private broker detail"))
    def test_publish_failure_is_recorded_without_exposing_transport_error(self, publish):
        task = Task.objects.create(name="Pending", operation="server.test_connection", requested_by=self.actor)
        with patch("apps.tasks.services.dispatcher.dispatch_status", return_value={"ready": True}):
            result = enqueue_task(task, actor=self.actor)
        self.assertEqual(result.status, Task.Status.FAILED)
        self.assertEqual(result.error_category, "queue_publish")
        self.assertEqual(result.error_message, "OSError")
        self.assertNotIn("private broker detail", result.error_message)

    @override_settings(TASK_DISPATCH_ENABLED=True, CELERY_BROKER_URL="redis://localhost/1")
    @patch("apps.tasks.services.runner.InfrastructureEngine.execute", return_value=OperationResult(
        "server.test_connection", "success", "SSH connection verified.", {"operating_system": "Linux"},
    ))
    def test_worker_revalidates_through_engine_and_ignores_duplicate_delivery(self, execute):
        with patch("apps.tasks.services.dispatcher.dispatch_status", return_value={"ready": True}), \
                patch("apps.tasks.services.operation_tasks.dispatch_status", return_value={"ready": True}), \
                patch("apps.tasks.services.dispatcher.publish_task"):
            task = queue_infrastructure_operation(
                operation="server.test_connection", target_id=self.host.pk,
                actor=self.actor, parameters={},
            )
        self.assertEqual(run_infrastructure_task(str(task.pk))["status"], Task.Status.COMPLETED)
        self.assertEqual(run_infrastructure_task(str(task.pk))["status"], Task.Status.COMPLETED)
        execute.assert_called_once()
        self.assertTrue(execute.call_args.kwargs["via_task"])

    def test_stale_running_task_is_marked_timed_out(self):
        task = Task.objects.create(
            name="Stale task", operation="server.test_connection", requested_by=self.actor,
            status=Task.Status.RUNNING, started_at=timezone.now() - timedelta(hours=1), attempt_count=1,
        )
        call_command("reconcile_stale_tasks", "--older-than=300", stdout=None)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.TIMEOUT)
        self.assertEqual(task.error_category, "worker_timeout")
        self.assertTrue(task.finished_at)
