from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase, override_settings

from apps.infrastructure.models import InfrastructureSnapshot, ManagedHost
from apps.tasks.models import Task
from apps.tasks.services.operation_tasks import queue_infrastructure_operation
from apps.tasks.services.runner import run_infrastructure_task
from infrastructure_engine.core.engine import OperationRejected


class LinuxServiceOperationTests(TestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_superuser("linux-admin", "linux@example.test", "long-linux-password")
        self.host = ManagedHost.objects.create(
            name="local-linux", hostname="localhost", is_local=True,
            server_type=ManagedHost.ServerType.LOCAL,
            connection_type=ManagedHost.ConnectionType.LOCAL,
        )
        InfrastructureSnapshot.objects.create(
            host=self.host, source="local-linux", status=InfrastructureSnapshot.Status.SUCCESS,
            data={"services": {"supported": True, "items": [{
                "unit": "ssh.service", "active": "active", "substate": "running",
            }]}},
            availability={"services": {"status": "available"}},
        )

    def queue_status_ready(self):
        return patch("apps.tasks.services.operation_tasks.dispatch_status", return_value={"ready": True}), patch(
            "apps.tasks.services.dispatcher.dispatch_status", return_value={"ready": True},
        )

    @override_settings(TASK_DISPATCH_ENABLED=True, CELERY_BROKER_URL="redis://localhost/1")
    def test_restart_requires_typed_confirmation_and_a_discovered_unit(self):
        with self.queue_status_ready()[0], self.queue_status_ready()[1], self.assertRaises(OperationRejected):
            queue_infrastructure_operation(
                operation="linux.service.restart", target_id=self.host.pk,
                actor=self.actor, parameters={"unit": "ssh.service"}, confirmation=False,
            )
        self.assertFalse(Task.objects.exists())
        with self.queue_status_ready()[0], self.queue_status_ready()[1], self.assertRaises(OperationRejected):
            queue_infrastructure_operation(
                operation="linux.service.restart", target_id=self.host.pk,
                actor=self.actor, parameters={"unit": "other.service"}, confirmation=True,
            )
        self.assertFalse(Task.objects.exists())

    @override_settings(TASK_DISPATCH_ENABLED=True, CELERY_BROKER_URL="redis://localhost/1")
    @patch("infrastructure_engine.adapters.systemd.service_manager.subprocess.run")
    @patch("infrastructure_engine.adapters.systemd.service_manager.shutil.which", return_value="/usr/bin/systemctl")
    def test_restart_runs_only_fixed_systemctl_argv_and_verifies_active_state(self, which, run):
        run.return_value = None
        with self.queue_status_ready()[0], self.queue_status_ready()[1], patch("apps.tasks.services.dispatcher.publish_task"):
            task = queue_infrastructure_operation(
                operation="linux.service.restart", target_id=self.host.pk,
                actor=self.actor, parameters={"unit": "ssh.service"}, confirmation=True,
            )
        result = run_infrastructure_task(task.pk)
        self.assertEqual(result["status"], Task.Status.COMPLETED)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0], ["/usr/bin/systemctl", "--no-ask-password", "restart", "ssh.service"])
        self.assertEqual(run.call_args_list[1].args[0], ["/usr/bin/systemctl", "--no-ask-password", "is-active", "--quiet", "ssh.service"])
        self.assertTrue(all(call.kwargs["check"] for call in run.call_args_list))

    @override_settings(TASK_DISPATCH_ENABLED=True, CELERY_BROKER_URL="redis://localhost/1")
    def test_only_local_host_and_task_view_permission_can_queue_restart(self):
        remote = ManagedHost.objects.create(name="remote-linux", hostname="remote.example.test")
        with self.queue_status_ready()[0], self.queue_status_ready()[1], self.assertRaises(OperationRejected):
            queue_infrastructure_operation(
                operation="linux.service.restart", target_id=remote.pk,
                actor=self.actor, parameters={"unit": "ssh.service"}, confirmation=True,
            )
        viewer = get_user_model().objects.create_user("linux-viewer", password="long-password")
        with self.queue_status_ready()[0], self.queue_status_ready()[1], self.assertRaises(PermissionDenied):
            queue_infrastructure_operation(
                operation="linux.service.restart", target_id=self.host.pk,
                actor=viewer, parameters={"unit": "ssh.service"}, confirmation=True,
            )
        self.assertFalse(Task.objects.exists())
