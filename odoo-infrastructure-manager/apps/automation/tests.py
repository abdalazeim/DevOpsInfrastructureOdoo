from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.exceptions import PermissionDenied
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from apps.automation.models import ApprovedTaskTemplate, AutomationRun, AutomationSchedule
from apps.automation.services.execution import (
    AutomationValidationError,
    execute_automation_run,
    queue_automation_run,
    validate_variable_values,
)
from apps.infrastructure.models import ManagedHost
from apps.accounts.models import UserProfile
from apps.security.services.credentials import encrypt_secret
from apps.tasks.models import Task
from apps.tasks.services.dispatcher import TaskDispatchUnavailable
from infrastructure_engine.core.engine import InfrastructureEngine, OperationRejected


TEST_KEY = Fernet.generate_key().decode("ascii")


class AutomationVariableValidationTests(SimpleTestCase):
    def setUp(self):
        self.template = ApprovedTaskTemplate(
            name="Baseline", project_id=1, template_id=1,
            category=ApprovedTaskTemplate.Category.MAINTENANCE,
            variables_schema={
                "release": {"type": "string", "required": True, "choices": ["stable", "testing"]},
                "retries": {"type": "integer"},
                "check_only": {"type": "boolean"},
            },
        )

    def test_only_declared_typed_values_are_accepted(self):
        self.assertEqual(
            validate_variable_values(
                self.template, {"release": "stable", "retries": 3, "check_only": False}
            ),
            {"release": "stable", "retries": 3, "check_only": False},
        )

    def test_unknown_wrong_type_and_sensitive_variables_are_rejected(self):
        with self.assertRaises(AutomationValidationError):
            validate_variable_values(self.template, {"release": "unknown"})
        with self.assertRaises(AutomationValidationError):
            validate_variable_values(self.template, {"release": "stable", "retries": True})
        self.template.variables_schema = {"api_token": {"type": "string"}}
        with self.assertRaises(AutomationValidationError):
            validate_variable_values(self.template, {"api_token": "must-not-be-stored"})


class AutomationExecutionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            "automation-admin", "automation@example.test", "test-password"
        )
        self.host = ManagedHost.objects.create(
            name="prod", hostname="prod.example.test", ansible_limit="prod-web"
        )
        self.template = ApprovedTaskTemplate.objects.create(
            name="Baseline", project_id=1, template_id=2,
            category=ApprovedTaskTemplate.Category.MAINTENANCE,
            enabled=True, read_only=False, requires_confirmation=True,
            host=self.host,
            variables_schema={"release": {"type": "string", "required": True}},
        )

    @override_settings(CREDENTIAL_ENCRYPTION_KEY=TEST_KEY, TASK_DISPATCH_ENABLED=True)
    @patch("apps.tasks.services.dispatcher.publish_task")
    @patch(
        "apps.tasks.services.dispatcher.dispatch_status",
        return_value={"ready": True, "status": "configured", "message": "ready"},
    )
    @patch(
        "apps.tasks.services.operation_tasks.dispatch_status",
        return_value={"ready": True, "status": "configured", "message": "ready"},
    )
    def test_manual_run_is_encrypted_and_dispatched_as_a_typed_task(
        self, operation_dispatch_status, dispatcher_status, publish_task
    ):
        run = queue_automation_run(
            template=self.template, actor=self.user, variables={"release": "stable"}
        )
        task = run.task
        self.assertEqual(run.task, task)
        self.assertEqual(run.host_limit, "prod-web")
        self.assertEqual(run.variable_names, ["release"])
        self.assertNotIn("stable", run.encrypted_variables)
        self.assertEqual(task.status, Task.Status.QUEUED)
        self.assertNotIn("stable", str(task.safe_metadata))
        self.assertEqual(
            task.safe_metadata["operation_request"]["parameters"], {"run_id": run.pk}
        )
        publish_task.assert_called_once_with(task.pk)

    @override_settings(CREDENTIAL_ENCRYPTION_KEY=TEST_KEY, TASK_DISPATCH_ENABLED=True)
    @patch("apps.automation.services.semaphore_client.SemaphoreClient.start_task", return_value={"id": 73})
    def test_worker_revalidates_scope_and_starts_approved_external_task(self, start_task):
        run = AutomationRun.objects.create(
            template=self.template, requested_by=self.user, dry_run=True,
            host_limit="prod-web",
            encrypted_variables=encrypt_secret('{"release":"stable"}'),
            variable_names=["release"], summary="Queued",
        )
        result = InfrastructureEngine.execute(
            "automation.template.execute",
            target_id=self.host.pk,
            actor=self.user,
            parameters={"run_id": run.pk},
            confirmation=True,
            via_task=True,
        )

        self.assertEqual(result.status, "success")
        start_task.assert_called_once_with(
            1, 2, dry_run=True, limit="prod-web", extra_vars={"release": "stable"}
        )
        run.refresh_from_db()
        self.assertEqual(run.external_task_id, 73)
        self.assertEqual(run.status, AutomationRun.Status.QUEUED)

    @override_settings(CREDENTIAL_ENCRYPTION_KEY=TEST_KEY)
    @patch("apps.tasks.services.operation_tasks.queue_infrastructure_operation")
    def test_dispatch_unavailable_is_saved_as_failure(self, queue_operation):
        queue_operation.side_effect = TaskDispatchUnavailable("Task dispatch is disabled.")
        run = queue_automation_run(
            template=self.template, actor=self.user, variables={"release": "stable"}
        )
        self.assertEqual(run.status, AutomationRun.Status.FAILED)
        self.assertIn("disabled", run.summary)

    @override_settings(CREDENTIAL_ENCRYPTION_KEY=TEST_KEY, TASK_DISPATCH_ENABLED=True)
    def test_worker_rejects_changed_host_scope(self):
        run = AutomationRun.objects.create(
            template=self.template, requested_by=self.user, dry_run=True,
            host_limit="stale-limit",
        )
        with self.assertRaises(OperationRejected):
            execute_automation_run(self.host, run.pk, self.user)
        run.refresh_from_db()
        self.assertEqual(run.status, AutomationRun.Status.FAILED)

    @override_settings(CREDENTIAL_ENCRYPTION_KEY=TEST_KEY, TASK_DISPATCH_ENABLED=True)
    def test_worker_revalidates_live_policy_after_approval_changes(self):
        run = AutomationRun.objects.create(
            template=self.template, requested_by=self.user, dry_run=False,
            host_limit="prod-web", encrypted_variables=encrypt_secret('{"release":"stable"}'),
            variable_names=["release"],
        )
        self.template.read_only = True
        self.template.save(update_fields=["read_only"])

        with self.assertRaises(OperationRejected):
            InfrastructureEngine.execute(
                "automation.template.execute",
                target_id=self.host.pk,
                actor=self.user,
                parameters={"run_id": run.pk},
                confirmation=True,
                via_task=True,
            )
        run.refresh_from_db()
        self.assertEqual(run.status, AutomationRun.Status.FAILED)

    @override_settings(CREDENTIAL_ENCRYPTION_KEY=TEST_KEY, TASK_DISPATCH_ENABLED=True)
    def test_worker_rechecks_restore_permission(self):
        restore_operator = get_user_model().objects.create_user(
            "restore-operator", "restore@example.test", "test-password"
        )
        profile, _ = UserProfile.objects.get_or_create(user=restore_operator)
        profile.permissions = ["automation.playbook.execute"]
        profile.save(update_fields=["permissions"])
        self.template.category = ApprovedTaskTemplate.Category.RESTORE
        self.template.save(update_fields=["category"])
        run = AutomationRun.objects.create(
            template=self.template, requested_by=restore_operator, dry_run=True,
            host_limit="prod-web",
        )

        with self.assertRaises(OperationRejected):
            InfrastructureEngine.execute(
                "automation.template.execute",
                target_id=self.host.pk,
                actor=restore_operator,
                parameters={"run_id": run.pk},
                confirmation=True,
                via_task=True,
            )
        run.refresh_from_db()
        self.assertEqual(run.status, AutomationRun.Status.FAILED)

    @override_settings(CREDENTIAL_ENCRYPTION_KEY=TEST_KEY)
    @patch("apps.tasks.services.operation_tasks.queue_infrastructure_operation")
    def test_live_run_requires_confirmation(self, queue_operation):
        with self.assertRaises(AutomationValidationError):
            queue_automation_run(
                template=self.template, actor=self.user, dry_run=False, confirmed=False
            )
        queue_operation.assert_not_called()

    @override_settings(CREDENTIAL_ENCRYPTION_KEY=TEST_KEY, TASK_DISPATCH_ENABLED=True)
    @patch("apps.tasks.services.dispatcher.publish_task")
    @patch(
        "apps.tasks.services.dispatcher.dispatch_status",
        return_value={"ready": True, "status": "configured", "message": "ready"},
    )
    @patch(
        "apps.tasks.services.operation_tasks.dispatch_status",
        return_value={"ready": True, "status": "configured", "message": "ready"},
    )
    def test_confirmed_live_run_is_task_dispatched(
        self, operation_dispatch_status, dispatcher_status, publish_task
    ):
        run = queue_automation_run(
            template=self.template,
            actor=self.user,
            dry_run=False,
            confirmed=True,
            variables={"release": "stable"},
        )
        self.assertFalse(run.dry_run)
        self.assertEqual(run.task.status, Task.Status.QUEUED)
        self.assertEqual(
            run.task.safe_metadata["operation_request"]["confirmation"], True
        )
        publish_task.assert_called_once_with(run.task.pk)

    @override_settings(CREDENTIAL_ENCRYPTION_KEY=TEST_KEY)
    def test_inactive_actor_cannot_queue(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        with self.assertRaises(PermissionDenied):
            queue_automation_run(template=self.template, actor=self.user)

    @override_settings(CREDENTIAL_ENCRYPTION_KEY=TEST_KEY, TASK_DISPATCH_ENABLED=True)
    @patch("apps.tasks.services.dispatcher.publish_task")
    @patch(
        "apps.tasks.services.dispatcher.dispatch_status",
        return_value={"ready": True, "status": "configured", "message": "ready"},
    )
    @patch(
        "apps.tasks.services.operation_tasks.dispatch_status",
        return_value={"ready": True, "status": "configured", "message": "ready"},
    )
    def test_due_schedule_dispatches_dry_run_and_advances_next_run(
        self, operation_dispatch_status, dispatcher_status, publish_task
    ):
        schedule = AutomationSchedule.objects.create(
            template=self.template, created_by=self.user, interval_minutes=15,
            enabled=True, next_run_at=timezone.now() - timedelta(minutes=1),
            encrypted_variables=encrypt_secret('{"release":"stable"}'),
            variable_names=["release"],
        )

        output = StringIO()
        call_command("dispatch_due_automation_schedules", stdout=output)

        run = AutomationRun.objects.get()
        schedule.refresh_from_db()
        self.assertTrue(run.dry_run)
        self.assertEqual(run.task.status, Task.Status.QUEUED)
        self.assertGreater(schedule.next_run_at, timezone.now())
        self.assertIn("1 queued", output.getvalue())
