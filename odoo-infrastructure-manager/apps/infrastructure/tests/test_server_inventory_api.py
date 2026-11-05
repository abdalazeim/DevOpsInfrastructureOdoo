import json
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.core.models import AuditLog
from apps.automation.models import ApprovedTaskTemplate
from apps.backup.models import BackupArtifact
from apps.databases.models import DatabaseInstance
from apps.infrastructure.models import (
    InfrastructureSnapshot,
    InfrastructureSyncRecord,
    ManagedHost,
    ManagedService,
    ServerGroup,
    ServerTag,
)
from apps.monitoring.models import AlertEvent, AlertRule, ResourceSample
from apps.security.models import Credential
from apps.infrastructure.services.discovery import discover_host
from apps.tasks.models import Task


class ServerInventoryApiTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            "infra-admin", "infra@example.test", "long-infra-password"
        )
        self.client.force_login(self.admin)
        self.host = ManagedHost.objects.create(
            name="prod-app", hostname="prod.example.test", environment="production"
        )
        self.group = ServerGroup.objects.create(name="production")
        self.tag = ServerTag.objects.create(name="web", color="#123ABC")
        self.host.groups.add(self.group)
        self.host.tags.add(self.tag)

    def test_list_filters_and_paginates_canonical_host_records(self):
        response = self.client.get(
            "/api/v1/servers/?group=production&tag=web&page_size=1"
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["meta"]["total"], 1)
        self.assertEqual(payload["data"]["items"][0]["hostname"], "prod.example.test")
        self.assertEqual(payload["data"]["items"][0]["groups"], [self.group.pk])
        self.assertEqual(payload["data"]["items"][0]["tags"], [self.tag.pk])
        self.assertNotIn("credential_reference", payload["data"]["items"][0])

    def test_create_and_update_server_audit_changes_without_exposing_credentials(self):
        create = self.client.post(
            "/api/v1/servers/",
            data=json.dumps({
                "name": "staging-db",
                "hostname": "db.example.test",
                "environment": "staging",
                "groups": [self.group.pk],
                "tags": [self.tag.pk],
            }),
            content_type="application/json",
        )
        self.assertEqual(create.status_code, 201, create.content)
        created = create.json()["data"]
        self.assertFalse(created["has_credential"])
        self.assertNotIn("credential_id", created)
        self.assertNotIn("encrypted_secret", created)

        updated = self.client.patch(
            f"/api/v1/servers/{created['id']}/",
            data=json.dumps({"description": "Owned by the database team"}),
            content_type="application/json",
        )
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(updated.json()["data"]["description"], "Owned by the database team")
        self.assertEqual(
            AuditLog.objects.filter(module="infrastructure.host").count(), 2
        )

    def test_server_detail_never_exposes_credential_material_or_reference(self):
        credential = Credential.objects.create(
            name="private ssh",
            kind=Credential.Kind.SSH_PASSWORD,
            username="ops",
            encrypted_secret="encrypted-test-value",
        )
        self.host.credential = credential
        self.host.credential_reference = f"credential:{credential.pk}"
        self.host.save(update_fields=["credential", "credential_reference"])

        response = self.client.get(f"/api/v1/servers/{self.host.pk}/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertTrue(payload["has_credential"])
        self.assertNotIn("credential_id", payload)
        self.assertNotIn("credential_reference", payload)
        self.assertNotIn("encrypted_secret", payload)
        self.assertNotIn("encrypted-test-value", response.content.decode())

    def test_server_detail_includes_snapshot_data_and_section_availability(self):
        snapshot_record = InfrastructureSnapshot.objects.create(
            host=self.host,
            source="local-linux",
            status=InfrastructureSnapshot.Status.PARTIAL,
            data={
                "cpu": {"usage_percent": 0.0},
                "storage": {"filesystems": [{"mountpoint": "/", "total_bytes": 1000}]},
                "disks": [{"mountpoint": "/", "total_bytes": 1000}],
            },
            availability={
                "cpu": {"status": "available", "observed_at": 1.0},
                "memory": {"status": "unavailable", "reason": "AccessDenied"},
            },
            collection_duration_ms=125,
        )
        InfrastructureSnapshot.objects.filter(pk=snapshot_record.pk).update(
            captured_at=timezone.now() - timedelta(minutes=6)
        )

        response = self.client.get(f"/api/v1/servers/{self.host.pk}/")
        self.assertEqual(response.status_code, 200)
        snapshot = response.json()["data"]["latest_snapshot"]
        self.assertEqual(snapshot["status"], "partial")
        self.assertTrue(snapshot["is_stale"])
        self.assertEqual(snapshot["data"]["cpu"]["usage_percent"], 0.0)
        self.assertEqual(snapshot["data"]["storage"]["filesystems"][0]["total_bytes"], 1000)
        self.assertEqual(snapshot["availability"]["memory"]["status"], "unavailable")
        self.assertEqual(snapshot["collection_duration_ms"], 125)

    def test_create_only_permission_can_register_without_read_access(self):
        user = get_user_model().objects.create_user(
            "registrar", "registrar@example.test", "long-registrar-password"
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.permissions = ["server.create"]
        profile.save(update_fields=["permissions"])
        self.client.force_login(user)

        response = self.client.post(
            "/api/v1/servers/",
            data=json.dumps({"name": "new-host", "hostname": "new.example.test"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(
            self.client.get("/api/v1/servers/").status_code, 403
        )

    def test_discovery_requires_its_specific_permission_and_dispatch(self):
        user = get_user_model().objects.create_user(
            "viewer", "viewer@example.test", "long-viewer-password"
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.permissions = ["task.view"]
        profile.save(update_fields=["permissions"])
        self.client.force_login(user)

        with patch("apps.infrastructure.api_views.queue_infrastructure_operation") as queue:
            denied = self.client.post(
                f"/api/v1/servers/{self.host.pk}/discover/"
            )
            self.assertEqual(denied.status_code, 403)
            queue.assert_not_called()

            profile.permissions = ["server.discover", "task.view"]
            profile.save(update_fields=["permissions"])
            queue.return_value = type(
                "QueuedTask",
                (),
                {"pk": uuid.uuid4(), "status": Task.Status.QUEUED, "operation": "server.discover"},
            )()
            accepted = self.client.post(f"/api/v1/servers/{self.host.pk}/discover/")
        self.assertEqual(accepted.status_code, 202, accepted.content)
        self.assertEqual(accepted.json()["data"]["status"], Task.Status.QUEUED)
        queue.assert_called_once()

    def test_group_and_tag_creation_validation_and_catalog_endpoints(self):
        group_response = self.client.post(
            "/api/v1/servers/groups/",
            data=json.dumps({"name": "database", "description": "Database servers"}),
            content_type="application/json",
        )
        self.assertEqual(group_response.status_code, 201, group_response.content)
        tag_response = self.client.post(
            "/api/v1/servers/tags/",
            data=json.dumps({"name": "invalid-color", "color": "red;display:none"}),
            content_type="application/json",
        )
        self.assertEqual(tag_response.status_code, 400)
        self.assertTrue(self.client.get("/api/v1/servers/groups/").json()["success"])
        self.assertTrue(self.client.get("/api/v1/servers/tags/").json()["success"])

    def test_dashboard_shows_groups_tags_and_sync_history(self):
        record = InfrastructureSyncRecord.objects.create(
            host=self.host,
            source="remote-ssh-linux",
            status=InfrastructureSyncRecord.Status.PARTIAL,
            updated_sections=["system"],
            started_at=self.host.created_at,
            completed_at=self.host.created_at,
        )
        response = self.client.get(reverse("dashboard:inventory"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.group.name)
        self.assertContains(response, self.tag.name)
        self.assertContains(response, "Partially collected")
        self.assertEqual(record.host, self.host)

    @patch("apps.infrastructure.services.discovery.collect_ssh_snapshot")
    def test_discovery_persists_history_and_preserves_manual_inventory(self, collect):
        self.host.description = "Manually maintained description"
        self.host.operating_system = "Admin override"
        self.host.save(update_fields=["description", "operating_system"])
        collect.return_value = {
            "source": "remote-ssh-linux",
            "status": "partial",
            "data": {"system": {
                "distribution": "Ubuntu 24.04",
                "kernel": "6.8.0",
                "architecture": "x86_64",
            }},
            "availability": {
                "system": {"status": "available"},
                "memory": {"status": "unavailable"},
            },
            "duration_ms": 20,
            "error_details": "memory: PermissionError",
        }

        snapshot = discover_host(self.host)
        self.host.refresh_from_db()
        record = InfrastructureSyncRecord.objects.get(host=self.host)
        self.assertEqual(snapshot.status, InfrastructureSnapshot.Status.PARTIAL)
        self.assertEqual(record.updated_sections, ["system"])
        self.assertEqual(self.host.operating_system, "Ubuntu 24.04")
        self.assertEqual(self.host.description, "Manually maintained description")
        self.assertEqual(self.host.environment, ManagedHost.Environment.PRODUCTION)
        self.assertEqual(self.host.connection_status, ManagedHost.ConnectionStatus.ONLINE)
        history = self.client.get(
            f"/api/v1/servers/{self.host.pk}/sync-history/"
        )
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["data"]["items"][0]["id"], str(record.pk))

    def test_related_service_and_task_refer_to_the_canonical_host(self):
        service = ManagedService.objects.create(
            host=self.host, key="web", name="Web service", kind=ManagedService.Kind.OTHER
        )
        task = Task.objects.create(
            name="Probe", operation="server.test_connection",
            target_server=self.host, requested_by=self.admin,
        )
        self.assertEqual(service.host_id, self.host.pk)
        self.assertEqual(task.target_server_id, self.host.pk)
        self.assertEqual(self.host.services.get(), service)
        self.assertEqual(self.host.tasks.get(), task)

        database = DatabaseInstance.objects.create(
            host=self.host, name="production", engine="postgresql"
        )
        rule = AlertRule.objects.create(
            name="CPU high", metric=AlertRule.Metric.CPU, threshold=90
        )
        alert = AlertEvent.objects.create(rule=rule, host=self.host, title="CPU high")
        sample = ResourceSample.objects.create(
            host=self.host, source="test", cpu_percent=42
        )
        backup = BackupArtifact.objects.create(host=self.host, status="success")
        template = ApprovedTaskTemplate.objects.create(
            name="Inspect host", project_id=1, template_id=1,
            category=ApprovedTaskTemplate.Category.DISCOVERY, host=self.host,
        )
        self.assertEqual(database.host_id, self.host.pk)
        self.assertEqual(alert.host_id, self.host.pk)
        self.assertEqual(sample.host_id, self.host.pk)
        self.assertEqual(backup.host_id, self.host.pk)
        self.assertEqual(template.host_id, self.host.pk)

    def test_inventory_frontend_creates_group_and_tag_for_host_assignment(self):
        group_response = self.client.post(
            reverse("dashboard:create_server_group"),
            {"name": "operations", "description": "Operations"},
        )
        tag_response = self.client.post(
            reverse("dashboard:create_server_tag"),
            {"name": "critical", "color": "#12abEF"},
        )
        self.assertEqual(group_response.status_code, 302)
        self.assertEqual(tag_response.status_code, 302)
        group = ServerGroup.objects.get(name="operations")
        tag = ServerTag.objects.get(name="critical")

        create_response = self.client.post(
            reverse("dashboard:create_inventory_item", args=["host"]),
            {
                "name": "tagged-host",
                "hostname": "tagged.example.test",
                "environment": "staging",
                "server_type": "remote",
                "connection_type": "ssh",
                "ssh_port": "22",
                "groups": [str(group.pk)],
                "tags": [str(tag.pk)],
                "description": "",
                "enabled": "on",
            },
        )
        self.assertEqual(create_response.status_code, 302)
        host = ManagedHost.objects.get(name="tagged-host")
        self.assertEqual(list(host.groups.all()), [group])
        self.assertEqual(list(host.tags.all()), [tag])
