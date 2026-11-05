from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.core.models import AuditLog
from apps.containers.models import (
    ComposeProject,
    DockerContainer,
    DockerEngine,
    DockerImage,
    DockerNetwork,
    DockerVolume,
)
from apps.infrastructure.models import ManagedHost
from apps.tasks.services.dispatcher import TaskDispatchUnavailable
from infrastructure_engine.adapters.docker.client import (
    DockerAdapterError,
    MAX_RESOURCES,
    _collect_containers,
    read_container_logs,
)
from infrastructure_engine.core.engine import InfrastructureEngine, OperationRejected


class DockerInventoryTests(TestCase):
    def setUp(self):
        self.host = ManagedHost.objects.create(
            name="docker-local",
            hostname="localhost",
            is_local=True,
            server_type="local",
            connection_type="local",
        )
        self.engine = DockerEngine.objects.create(
            host=self.host,
            status=DockerEngine.Status.AVAILABLE,
            last_checked_at=timezone.now(),
        )

    @override_settings(INFRA_DOCKER_READ_ENABLED=True)
    @patch("apps.containers.services.inventory.collect_inventory")
    def test_discovery_persists_resource_relationships(self, collect):
        from apps.containers.services.inventory import DockerInventoryService

        collect.return_value = {
            "engine": {"ServerVersion": "27.0", "ApiVersion": "1.47"},
            "containers": {"items": [{
                "docker_id": "a" * 64,
                "name": "web",
                "image": "example/web:latest",
                "image_id": "sha256:" + "b" * 64,
                "state": "running",
                "status": "Up",
                "health": "healthy",
                "ports": [],
                "network_names": ["front"],
                "mounts": [{
                    "type": "volume",
                    "source": "web-data",
                    "destination": "/data",
                    "read_write": True,
                }],
                "created_at": None,
                "started_at": None,
                "compose_project": "site",
                "compose_service": "web",
            }], "truncated": False},
            "images": {"items": [{
                "docker_id": "sha256:" + "b" * 64,
                "repositories": ["example/web:latest"],
                "size_bytes": 100,
                "created_at": None,
            }], "truncated": False},
            "volumes": {"items": [{
                "name": "web-data", "driver": "local", "mountpoint": "/var/lib/docker/volumes/web-data",
            }], "truncated": False},
            "networks": {"items": [{
                "docker_id": "c" * 64, "name": "front", "driver": "bridge",
                "scope": "local", "subnets": [],
            }], "truncated": False},
            "compose_projects": {"items": [{
                "name": "site", "services": ["web"], "status": "running",
            }], "truncated": False},
        }

        result = DockerInventoryService.discover(self.engine)

        self.assertTrue(result["available"])
        container = DockerContainer.objects.get(engine=self.engine, docker_id="a" * 64)
        self.assertEqual(container.image_record.docker_id, "sha256:" + "b" * 64)
        self.assertEqual(list(container.networks.values_list("name", flat=True)), ["front"])
        self.assertEqual(list(container.volumes.values_list("name", flat=True)), ["web-data"])
        self.assertTrue(ComposeProject.objects.filter(engine=self.engine, name="site").exists())
        self.engine.refresh_from_db()
        self.assertEqual(self.engine.engine_version, "27.0")

    @override_settings(INFRA_DOCKER_READ_ENABLED=True)
    @patch("apps.containers.services.inventory.collect_inventory")
    def test_truncated_discovery_does_not_delete_unreturned_containers(self, collect):
        from apps.containers.services.inventory import DockerInventoryService

        retained = DockerContainer.objects.create(
            engine=self.engine,
            docker_id="d" * 64,
            name="possibly-beyond-limit",
            observed_at=timezone.now(),
        )
        collect.return_value = {
            "engine": {},
            "containers": {"items": [], "truncated": True},
            "images": {"items": [], "truncated": False},
            "volumes": {"items": [], "truncated": False},
            "networks": {"items": [], "truncated": False},
            "compose_projects": {"items": [], "truncated": False},
        }

        result = DockerInventoryService.discover(self.engine)

        self.assertTrue(result["available"])
        self.assertTrue(result["truncated"])
        self.assertTrue(DockerContainer.objects.filter(pk=retained.pk).exists())

    @override_settings(INFRA_DOCKER_READ_ENABLED=True)
    @patch("apps.containers.services.inventory.collect_inventory", side_effect=DockerAdapterError("DockerException"))
    def test_failed_discovery_marks_engine_unavailable_and_preserves_inventory(self, collect):
        from apps.containers.services.inventory import DockerInventoryService

        container = DockerContainer.objects.create(
            engine=self.engine, docker_id="e" * 64, name="existing", observed_at=timezone.now()
        )
        result = DockerInventoryService.discover(self.engine)
        self.engine.refresh_from_db()

        self.assertFalse(result["available"])
        self.assertEqual(self.engine.status, DockerEngine.Status.UNAVAILABLE)
        self.assertTrue(DockerContainer.objects.filter(pk=container.pk).exists())

    def test_docker_resource_ids_are_unique_within_each_engine(self):
        DockerContainer.objects.create(
            engine=self.engine, docker_id="2" * 64, name="first", observed_at=timezone.now()
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            DockerContainer.objects.create(
                engine=self.engine, docker_id="2" * 64, name="duplicate", observed_at=timezone.now()
            )

        other_host = ManagedHost.objects.create(
            name="docker-other",
            hostname="localhost",
            is_local=False,
        )
        other_engine = DockerEngine.objects.create(host=other_host)
        DockerContainer.objects.create(
            engine=other_engine, docker_id="2" * 64, name="same-id-other-engine",
            observed_at=timezone.now(),
        )


class DockerLogsAdapterTests(TestCase):
    @patch("infrastructure_engine.adapters.docker.client.create_client")
    def test_reads_bounded_container_logs_from_registered_docker_sdk(self, create_client):
        client = create_client.return_value
        container = client.containers.get.return_value
        container.logs.return_value = b"safe output\n"

        output = read_container_logs(
            SimpleNamespace(endpoint="unix:///var/run/docker.sock"),
            "a" * 64,
            100,
        )

        self.assertEqual(output, "safe output\n")
        container.logs.assert_called_once_with(
            stdout=True, stderr=True, tail=100, timestamps=False
        )
        client.close.assert_called_once()

    @patch("infrastructure_engine.adapters.docker.client.create_client")
    def test_log_output_is_capped_at_40k_characters(self, create_client):
        create_client.return_value.containers.get.return_value.logs.return_value = (
            b"x" * 40001
        )

        output = read_container_logs(
            SimpleNamespace(endpoint="unix:///var/run/docker.sock"),
            "a" * 64,
            200,
        )

        self.assertEqual(len(output), 40000)

    @patch("infrastructure_engine.adapters.docker.client.create_client")
    def test_rejects_out_of_range_log_tail_before_connecting(self, create_client):
        with self.assertRaises(DockerAdapterError):
            read_container_logs(
                SimpleNamespace(endpoint="unix:///var/run/docker.sock"),
                "a" * 64,
                201,
            )
        create_client.assert_not_called()

    @patch("docker.DockerClient")
    def test_rejects_non_local_endpoint_before_creating_sdk_client(self, docker_client):
        from infrastructure_engine.adapters.docker.client import create_client

        with self.assertRaises(DockerAdapterError):
            create_client(SimpleNamespace(endpoint="tcp://127.0.0.1:2375"))
        docker_client.assert_not_called()

    def test_missing_docker_sdk_is_reported_explicitly(self):
        from infrastructure_engine.adapters.docker.client import create_client

        with patch("builtins.__import__", side_effect=ImportError):
            with self.assertRaisesMessage(DockerAdapterError, "Docker SDK is not installed."):
                create_client(SimpleNamespace(endpoint="unix:///var/run/docker.sock"))

    @patch("infrastructure_engine.adapters.docker.client.create_client")
    def test_inventory_sdk_failure_is_redacted_and_client_is_closed(self, create_client):
        from infrastructure_engine.adapters.docker.client import collect_inventory

        client = create_client.return_value
        client.info.side_effect = RuntimeError("sensitive daemon detail")

        with self.assertRaises(DockerAdapterError) as raised:
            collect_inventory(SimpleNamespace(endpoint="unix:///var/run/docker.sock"))

        self.assertEqual(str(raised.exception), "RuntimeError")
        self.assertNotIn("sensitive daemon detail", str(raised.exception))
        client.close.assert_called_once()

    @patch("infrastructure_engine.adapters.docker.client.create_client")
    def test_inventory_timeout_is_reported_as_adapter_failure(self, create_client):
        from infrastructure_engine.adapters.docker.client import collect_inventory

        client = create_client.return_value
        client.info.side_effect = TimeoutError()

        with self.assertRaisesMessage(DockerAdapterError, "TimeoutError"):
            collect_inventory(SimpleNamespace(endpoint="unix:///var/run/docker.sock"))
        client.close.assert_called_once()

    def test_inventory_collection_uses_engine_side_container_limit(self):
        client = SimpleNamespace(containers=Mock())
        client.containers.list.return_value = [
            SimpleNamespace(
                id=f"{index:064x}",
                name=f"container-{index}",
                status="running",
                attrs={
                    "Config": {"Image": "test", "Labels": {}},
                    "State": {"Status": "running"},
                    "NetworkSettings": {"Ports": {}, "Networks": {}},
                    "Mounts": [],
                },
            )
            for index in range(MAX_RESOURCES + 1)
        ]

        result = _collect_containers(client)

        self.assertEqual(len(result["items"]), MAX_RESOURCES)
        self.assertTrue(result["truncated"])
        client.containers.list.assert_called_once_with(
            all=True, limit=MAX_RESOURCES + 1
        )


class DockerSurfaceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "docker-reader", "docker-reader@example.test", "long-docker-password"
        )
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.permissions = ["docker.container.view"]
        profile.save(update_fields=["permissions"])
        self.host = ManagedHost.objects.create(
            name="docker-api-local",
            hostname="localhost",
            is_local=True,
            server_type="local",
            connection_type="local",
        )
        self.engine = DockerEngine.objects.create(
            host=self.host,
            status=DockerEngine.Status.AVAILABLE,
            last_checked_at=timezone.now(),
        )
        self.client.force_login(self.user)

    def test_docker_only_permission_can_access_dashboard_and_api(self):
        response = self.client.get("/dashboard/containers/")
        api_response = self.client.get("/api/v1/docker/engines/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Saved inventory")
        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(api_response.json()["data"]["items"][0]["id"], self.engine.pk)

    def test_user_without_docker_or_infrastructure_permission_is_denied(self):
        profile = self.user.profile
        profile.permissions = []
        profile.save(update_fields=["permissions"])

        response = self.client.get("/dashboard/containers/")
        api_response = self.client.get("/api/v1/docker/engines/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(api_response.status_code, 403)

    def test_engine_registration_requires_manage_permission_and_uses_local_server(self):
        profile = self.user.profile
        profile.permissions = ["docker.engine.manage"]
        profile.save(update_fields=["permissions"])

        response = self.client.post(
            "/api/v1/docker/engines/",
            data={"server_id": self.host.pk},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"]["id"], self.engine.pk)

    def test_action_requires_explicit_confirmation_before_dispatch(self):
        response = self.client.post(
            f"/api/v1/docker/engines/{self.engine.pk}/containers/{'a' * 64}/start/",
            data={"confirmation": False},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("confirmation", response.json()["error"].lower())

    @override_settings(INFRA_DOCKER_READ_ENABLED=True)
    @patch("apps.containers.api_views.queue_infrastructure_operation")
    def test_discovery_endpoint_dispatches_typed_task(self, queue):
        profile = self.user.profile
        profile.permissions = ["docker.container.view", "task.view"]
        profile.save(update_fields=["permissions"])
        queue.return_value = SimpleNamespace(
            pk="discovery-task", status="queued", operation="docker.engine.discover"
        )

        response = self.client.post(
            f"/api/v1/docker/engines/{self.engine.pk}/discover/",
            data=b"",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["data"]["task_id"], "discovery-task")
        self.assertEqual(queue.call_args.kwargs["operation"], "docker.engine.discover")

    @patch("apps.containers.api_views.queue_infrastructure_operation")
    def test_discovery_endpoint_is_disabled_by_default(self, queue):
        response = self.client.post(
            f"/api/v1/docker/engines/{self.engine.pk}/discover/",
            data=b"",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 503)
        queue.assert_not_called()

    def test_view_permission_alone_cannot_dispatch_container_action(self):
        response = self.client.post(
            f"/api/v1/docker/engines/{self.engine.pk}/containers/{'a' * 64}/start/",
            data={"confirmation": True},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

    @override_settings(INFRA_DOCKER_WRITE_ENABLED=True)
    @patch(
        "apps.containers.api_views.queue_infrastructure_operation",
        side_effect=TaskDispatchUnavailable("Task dispatch is unavailable."),
    )
    def test_action_dispatch_failure_returns_unavailable_without_fallback(self, queue):
        profile = self.user.profile
        profile.permissions = [
            "docker.container.view",
            "docker.container.start",
            "task.view",
        ]
        profile.save(update_fields=["permissions"])

        response = self.client.post(
            f"/api/v1/docker/engines/{self.engine.pk}/containers/{'a' * 64}/start/",
            data={"confirmation": True},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 503)
        queue.assert_called_once()

    @patch("apps.containers.api_views.queue_infrastructure_operation")
    def test_action_is_dispatched_only_with_separate_action_and_task_permissions(self, queue):
        profile = self.user.profile
        profile.permissions = [
            "docker.container.view",
            "docker.container.start",
            "task.view",
        ]
        profile.save(update_fields=["permissions"])
        queue.return_value = SimpleNamespace(
            pk="task-id", status="queued", operation="docker.container.start"
        )

        response = self.client.post(
            f"/api/v1/docker/engines/{self.engine.pk}/containers/{'a' * 64}/start/",
            data={"confirmation": True},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["data"]["task_id"], "task-id")
        self.assertEqual(queue.call_args.kwargs["operation"], "docker.container.start")

    @override_settings(INFRA_DOCKER_READ_ENABLED=True)
    def test_stale_saved_inventory_is_not_presented_as_current(self):
        self.engine.last_checked_at = timezone.now() - timedelta(minutes=10)
        self.engine.save(update_fields=["last_checked_at"])
        DockerContainer.objects.create(
            engine=self.engine, docker_id="1" * 64, name="old", observed_at=timezone.now()
        )

        response = self.client.get("/dashboard/containers/")

        self.assertContains(response, "Docker inventory is stale")
        self.assertNotContains(response, "Queue inventory refresh")

    @override_settings(INFRA_DOCKER_READ_ENABLED=True)
    def test_resource_page_keeps_selected_engine_scope(self):
        DockerImage.objects.create(
            engine=self.engine, docker_id="sha256:selected", observed_at=timezone.now()
        )

        response = self.client.get(
            f"/dashboard/docker/images/?engine={self.engine.pk}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.host.name)
        self.assertContains(response, "sha256:selected")

    @override_settings(
        INFRA_DOCKER_READ_ENABLED=True,
        INFRA_DOCKER_WRITE_ENABLED=True,
        TASK_DISPATCH_ENABLED=True,
    )
    @patch("apps.dashboard.views.dispatch_status", return_value={"ready": True})
    @patch("apps.dashboard.views.queue_infrastructure_operation")
    def test_dashboard_shows_state_valid_actions_and_queues_confirmed_action(
        self, queue, _dispatch_status
    ):
        profile = self.user.profile
        profile.permissions = [
            "docker.container.view",
            "docker.container.start",
            "docker.container.delete",
            "task.view",
        ]
        profile.save(update_fields=["permissions"])
        container = DockerContainer.objects.create(
            engine=self.engine,
            docker_id="8" * 64,
            name="stopped-service",
            state="exited",
            observed_at=timezone.now(),
        )
        queue.return_value = SimpleNamespace(pk="queued-task")

        page = self.client.get("/dashboard/containers/")
        self.assertContains(page, ">Start<")
        self.assertContains(page, ">Remove<")
        self.assertNotContains(page, ">Stop<")
        self.assertNotContains(page, ">Pause<")
        self.assertNotContains(page, ">Resume<")

        response = self.client.post(
            "/dashboard/containers/",
            data={
                "engine_id": self.engine.pk,
                "container_id": container.docker_id,
                "container_action": "start",
                "confirmation": "yes",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            queue.call_args.kwargs["operation"], "docker.container.start"
        )

    @override_settings(INFRA_DOCKER_READ_ENABLED=True)
    @patch("apps.dashboard.views.read_container_logs", return_value="password=secret")
    def test_logs_use_sdk_adapter_and_redact_sensitive_values(self, read_logs):
        container = DockerContainer.objects.create(
            engine=self.engine,
            docker_id="f" * 64,
            name="private-name",
            observed_at=timezone.now(),
        )

        response = self.client.get(
            f"/dashboard/containers/{container.docker_id}/logs/?engine={self.engine.pk}&format=json"
        )
        legacy_response = self.client.get(
            f"/dashboard/containers/{container.name}/logs/?engine={self.engine.pk}&format=json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(legacy_response.status_code, 200)
        self.assertEqual(response.json()["container"], "private-name")
        self.assertNotIn("secret", response.json()["logs"])
        self.assertEqual(read_logs.call_count, 2)


class DockerOperationPolicyTests(TestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_superuser(
            "docker-policy-admin",
            "docker-policy@example.test",
            "long-docker-policy-password",
        )
        self.host = ManagedHost.objects.create(
            name="docker-policy-host",
            hostname="localhost",
            is_local=True,
            server_type="local",
            connection_type="local",
        )
        self.engine = DockerEngine.objects.create(
            host=self.host,
            status=DockerEngine.Status.AVAILABLE,
            last_checked_at=timezone.now(),
        )
        self.container = DockerContainer.objects.create(
            engine=self.engine,
            docker_id="9" * 64,
            name="policy-container",
            state="exited",
            observed_at=timezone.now(),
        )

    @override_settings(INFRA_DOCKER_WRITE_ENABLED=False, TASK_DISPATCH_ENABLED=True)
    def test_write_operations_are_blocked_when_feature_gate_is_disabled(self):
        with self.assertRaises(OperationRejected) as raised:
            InfrastructureEngine.validate_request(
                "docker.container.start",
                target_id=self.host.pk,
                actor=self.actor,
                parameters={"container_id": self.container.docker_id},
                confirmation=True,
                via_task=True,
            )
        self.assertEqual(raised.exception.status_code, 503)

    @override_settings(INFRA_DOCKER_WRITE_ENABLED=True, TASK_DISPATCH_ENABLED=True)
    def test_stale_container_inventory_is_rejected(self):
        self.container.observed_at = timezone.now() - timedelta(minutes=10)
        self.container.save(update_fields=["observed_at"])

        with self.assertRaises(OperationRejected) as raised:
            InfrastructureEngine.validate_request(
                "docker.container.start",
                target_id=self.host.pk,
                actor=self.actor,
                parameters={"container_id": self.container.docker_id},
                confirmation=True,
                via_task=True,
            )
        self.assertEqual(raised.exception.status_code, 409)

    @override_settings(INFRA_DOCKER_WRITE_ENABLED=True, TASK_DISPATCH_ENABLED=True)
    def test_action_incompatible_with_current_container_state_is_rejected(self):
        with self.assertRaises(OperationRejected) as raised:
            InfrastructureEngine.validate_request(
                "docker.container.stop",
                target_id=self.host.pk,
                actor=self.actor,
                parameters={"container_id": self.container.docker_id},
                confirmation=True,
                via_task=True,
            )
        self.assertEqual(raised.exception.status_code, 409)

    @override_settings(INFRA_DOCKER_WRITE_ENABLED=True, TASK_DISPATCH_ENABLED=True)
    @patch(
        "infrastructure_engine.core.engine.perform_container_action",
        return_value={"action": "start"},
    )
    def test_valid_typed_action_reaches_adapter_and_is_audited(self, perform):
        result = InfrastructureEngine.execute(
            "docker.container.start",
            target_id=self.host.pk,
            actor=self.actor,
            parameters={"container_id": self.container.docker_id},
            confirmation=True,
            via_task=True,
        )

        self.assertEqual(result.status, "success")
        perform.assert_called_once_with(self.engine, self.container.docker_id, "start")
        self.assertTrue(AuditLog.objects.filter(
            module="infrastructure.operation",
            object_id=str(self.host.pk),
            object_repr__contains="docker.container.start",
        ).exists())
