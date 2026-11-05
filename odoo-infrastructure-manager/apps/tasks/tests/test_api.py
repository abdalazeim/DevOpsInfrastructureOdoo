import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.infrastructure.models import ManagedHost
from apps.tasks.models import Task, TaskLog
from apps.tasks.services.runner import run_infrastructure_task


class TaskApiTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            "task-api-admin", "task-api@example.test", "long-task-api-password"
        )
        self.client.force_login(self.admin)
        self.host = ManagedHost.objects.create(
            name="api-host", hostname="api.example.test"
        )

    def make_task(self, **kwargs):
        defaults = {
            "name": "Inspect host",
            "operation": "server.test_connection",
            "requested_by": self.admin,
            "target_server": self.host,
            "safe_metadata": {
                "operation_request": {
                    "operation": "server.test_connection",
                    "target_id": self.host.pk,
                    "parameters": {},
                    "confirmation": None,
                },
                "credential_reference": "must-not-be-returned",
            },
        }
        defaults.update(kwargs)
        return Task.objects.create(**defaults)

    def test_api_requires_authentication_and_task_view_permission(self):
        self.client.logout()
        self.assertEqual(self.client.get("/api/v1/tasks/").status_code, 401)

        user = get_user_model().objects.create_user(
            "no-task-access", "no-task-access@example.test", "long-user-password"
        )
        self.client.force_login(user)
        response = self.client.get("/api/v1/tasks/")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()["success"])

    def test_action_permissions_are_separate_from_task_read_permission(self):
        user = get_user_model().objects.create_user(
            "task-reader", "task-reader@example.test", "long-reader-password"
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.permissions = ["task.view"]
        profile.save(update_fields=["permissions"])
        task = self.make_task(status=Task.Status.QUEUED)
        self.client.force_login(user)

        cancel = self.client.post(f"/api/v1/tasks/{task.pk}/cancel/")
        retry = self.client.post(f"/api/v1/tasks/{task.pk}/retry/")
        self.assertEqual(cancel.status_code, 403)
        self.assertEqual(retry.status_code, 403)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.QUEUED)

    def test_list_filters_and_paginates_without_exposing_safe_metadata(self):
        matching = self.make_task()
        self.make_task(operation="linux.service.restart", status=Task.Status.FAILED)
        response = self.client.get(
            f"/api/v1/tasks/?status=pending&target_server={self.host.pk}&page_size=1"
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["meta"]["total"], 1)
        self.assertEqual(payload["items"][0]["id"], str(matching.pk))
        self.assertNotIn("safe_metadata", payload["items"][0])
        self.assertNotIn("credential_reference", response.content.decode())

    def test_invalid_filters_and_unknown_detail_return_standard_errors(self):
        invalid = self.client.get("/api/v1/tasks/?status=made-up")
        self.assertEqual(invalid.status_code, 400)
        self.assertFalse(invalid.json()["success"])

        missing = self.client.get(f"/api/v1/tasks/{uuid.uuid4()}/")
        self.assertEqual(missing.status_code, 404)
        self.assertFalse(missing.json()["success"])

    def test_detail_returns_bounded_logs_in_sequence_and_safe_fields(self):
        task = self.make_task()
        TaskLog.objects.create(
            task=task, sequence=2, stream=TaskLog.Stream.STDERR, content="second"
        )
        TaskLog.objects.create(
            task=task, sequence=1, stream=TaskLog.Stream.SYSTEM, content="first"
        )
        response = self.client.get(f"/api/v1/tasks/{task.pk}/")
        self.assertEqual(response.status_code, 200)
        detail = response.json()["data"]
        self.assertEqual(
            [entry["content"] for entry in detail["logs"]], ["first", "second"]
        )
        self.assertNotIn("safe_metadata", detail)
        self.assertEqual(detail["target_server"]["id"], self.host.pk)

    def test_cancel_api_marks_queued_task_cancelled(self):
        task = self.make_task(status=Task.Status.QUEUED)
        response = self.client.post(f"/api/v1/tasks/{task.pk}/cancel/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["status"], Task.Status.CANCELLED)
        task.refresh_from_db()
        self.assertTrue(task.finished_at)

    def test_cancel_running_task_records_request_without_claiming_completion(self):
        task = self.make_task(status=Task.Status.RUNNING)
        response = self.client.post(f"/api/v1/tasks/{task.pk}/cancel/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["status"], Task.Status.RUNNING)
        self.assertTrue(response.json()["data"]["cancel_requested_at"])
        task.refresh_from_db()
        self.assertIsNone(task.finished_at)

    def test_retry_rejects_nonterminal_or_exhausted_tasks(self):
        task = self.make_task(status=Task.Status.QUEUED, max_attempts=1)
        response = self.client.post(f"/api/v1/tasks/{task.pk}/retry/")
        self.assertEqual(response.status_code, 400)
        task.status = Task.Status.FAILED
        task.attempt_count = 1
        task.save(update_fields=["status", "attempt_count"])
        response = self.client.post(f"/api/v1/tasks/{task.pk}/retry/")
        self.assertEqual(response.status_code, 400)

    @override_settings(TASK_DISPATCH_ENABLED=True, CELERY_BROKER_URL="redis://localhost/1")
    @patch("apps.tasks.services.dispatcher.publish_task")
    @patch("apps.tasks.services.dispatcher.dispatch_status", return_value={"ready": True})
    @patch("apps.tasks.services.operation_tasks.dispatch_status", return_value={"ready": True})
    def test_retry_revalidates_operation_and_dispatches_failed_task(
        self, operation_dispatch, queue_dispatch, publish
    ):
        task = self.make_task(
            status=Task.Status.FAILED,
            attempt_count=1,
            max_attempts=2,
        )
        response = self.client.post(f"/api/v1/tasks/{task.pk}/retry/")
        self.assertEqual(response.status_code, 202, response.content)
        self.assertEqual(response.json()["data"]["status"], Task.Status.QUEUED)
        publish.assert_called_once_with(task.pk)

    def test_retry_permission_is_independent_from_read_permission(self):
        operator = get_user_model().objects.create_user(
            "task-retrier", "task-retrier@example.test", "long-retrier-password"
        )
        profile, _ = UserProfile.objects.get_or_create(user=operator)
        profile.permissions = ["task.retry"]
        profile.save(update_fields=["permissions"])
        task = self.make_task(status=Task.Status.FAILED)
        self.client.force_login(operator)
        response = self.client.post(f"/api/v1/tasks/{task.pk}/retry/")
        self.assertEqual(response.status_code, 403)


class TaskCancellationRunnerTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            "runner-admin", "runner@example.test", "long-runner-password"
        )
        self.host = ManagedHost.objects.create(
            name="runner-host", hostname="runner.example.test"
        )

    @patch("apps.tasks.services.runner.InfrastructureEngine.execute")
    def test_worker_honors_cancel_request_before_starting_operation(self, execute):
        task = Task.objects.create(
            name="Cancelled before execution",
            operation="server.test_connection",
            requested_by=self.admin,
            target_server=self.host,
            status=Task.Status.QUEUED,
            cancel_requested_at=timezone.now(),
            safe_metadata={
                "operation_request": {
                    "operation": "server.test_connection",
                    "target_id": self.host.pk,
                    "parameters": {},
                }
            },
        )
        result = run_infrastructure_task(task.pk)
        task.refresh_from_db()
        self.assertEqual(result["status"], Task.Status.CANCELLED)
        self.assertEqual(task.status, Task.Status.CANCELLED)
        execute.assert_not_called()
