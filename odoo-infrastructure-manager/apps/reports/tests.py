from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import UserProfile
from apps.backup.models import BackupArtifact
from apps.core.models import AuditLog
from apps.infrastructure.models import ManagedHost, ManagedService
from apps.monitoring.models import AlertEvent
from apps.tasks.models import Task


class ReportsAPITests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="reports-operator",
            password="long-test-password",
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.profile.permissions = [
            "reports.view",
            "reports.export",
            "server.view",
            "monitoring.view",
            "task.view",
            "backup.view",
        ]
        self.profile.save(update_fields=["permissions"])
        self.host = ManagedHost.objects.create(
            name='=HYPERLINK("https://example.test")',
            hostname="reports.example.test",
            credential_reference="vault://must-not-be-exported",
        )
        self.client.force_login(self.user)

    def test_catalog_only_includes_sources_the_user_can_read(self):
        response = self.client.get("/api/v1/reports/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {item["slug"] for item in response.json()["data"]},
            {"servers", "alerts", "tasks", "backups"},
        )

    def test_preview_uses_source_data_and_never_exposes_credential_reference(self):
        response = self.client.get("/api/v1/reports/servers/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["meta"]["total"], 1)
        self.assertEqual(payload["items"][0]["hostname"], "reports.example.test")
        self.assertNotIn("credential_reference", payload["items"][0])
        self.assertNotIn("vault://must-not-be-exported", response.content.decode())

    def test_preview_validates_filters_dates_and_pagination(self):
        for query in (
            "?from=not-a-date",
            "?from=2024-01-01&to=2025-01-02",
            "?host=0",
            "?page=0",
            "?page_size=101",
            "?unexpected=value",
        ):
            with self.subTest(query=query):
                response = self.client.get(f"/api/v1/reports/servers/{query}")
                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.json()["success"])

    def test_preview_requires_report_and_source_permissions(self):
        self.profile.permissions = ["reports.view"]
        self.profile.save(update_fields=["permissions"])

        catalog = self.client.get("/api/v1/reports/")
        preview = self.client.get("/api/v1/reports/servers/")

        self.assertEqual(catalog.status_code, 200)
        self.assertEqual(catalog.json()["data"], [])
        self.assertEqual(preview.status_code, 403)

    def test_csv_export_quotes_formula_cells_and_audits_without_row_data(self):
        response = self.client.get(
            "/api/v1/reports/servers/export/?format=csv"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        text = response.content.decode("utf-8-sig")
        self.assertIn("'=HYPERLINK", text)
        self.assertNotIn("vault://must-not-be-exported", text)
        self.assertIn('filename="reports-servers-', response["Content-Disposition"])
        self.assertEqual(
            AuditLog.objects.filter(module="reports.export").count(),
            1,
        )
        audit = AuditLog.objects.get(module="reports.export")
        self.assertEqual(audit.new_value, {"filters": {}, "row_count": 1})
        self.assertNotIn("HYPERLINK", str(audit.new_value))

    def test_export_requires_both_report_and_source_permissions(self):
        self.profile.permissions = ["reports.view", "reports.export"]
        self.profile.save(update_fields=["permissions"])

        response = self.client.get(
            "/api/v1/reports/servers/export/?format=csv"
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(AuditLog.objects.filter(module="reports.export").exists())

    def test_export_rejects_oversized_results_without_creating_partial_file(self):
        with patch("apps.reports.services.reports.MAX_CSV_ROWS", 0):
            response = self.client.get(
                "/api/v1/reports/servers/export/?format=csv"
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("exceeds the 0-row CSV limit", response.json()["message"])
        self.assertFalse(AuditLog.objects.filter(module="reports.export").exists())

    def test_pdf_export_is_a_valid_pdf_and_is_audited(self):
        response = self.client.get(
            "/api/v1/reports/servers/export/?format=pdf"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF-"))
        self.assertIn(b"/Count 1", response.content)
        self.assertTrue(response.content.rstrip().endswith(b"%%EOF"))
        self.assertEqual(
            AuditLog.objects.filter(module="reports.export").count(),
            1,
        )

    def test_backup_preview_excludes_storage_reference_and_checksum(self):
        service = ManagedService.objects.create(
            host=self.host,
            key="main-db",
            name="Main database",
            kind=ManagedService.Kind.POSTGRESQL,
        )
        BackupArtifact.objects.create(
            host=self.host,
            service=service,
            file_name="/private/storage/backup.dump",
            artifact_ref="private://storage/token",
            checksum="secret-checksum",
            status=BackupArtifact.Status.SUCCESS,
        )

        response = self.client.get("/api/v1/reports/backups/")

        self.assertEqual(response.status_code, 200)
        item = response.json()["data"]["items"][0]
        self.assertEqual(item["file_name"], "backup.dump")
        self.assertNotIn("artifact_ref", item)
        self.assertNotIn("checksum", item)
        self.assertNotIn("private://storage/token", response.content.decode())
        self.assertNotIn("secret-checksum", response.content.decode())

    def test_alert_and_task_reports_use_related_source_records_without_raw_details(self):
        AlertEvent.objects.create(
            host=self.host,
            title="Disk usage high",
            message="secret alert payload",
        )
        Task.objects.create(
            name="Restart service",
            operation="linux.service.restart",
            target_server=self.host,
            requested_by=self.user,
            error_message="secret execution detail",
        )

        alerts = self.client.get(
            f"/api/v1/reports/alerts/?host={self.host.pk}"
        )
        tasks = self.client.get(
            f"/api/v1/reports/tasks/?host={self.host.pk}"
        )

        self.assertEqual(alerts.status_code, 200)
        alert_item = alerts.json()["data"]["items"][0]
        self.assertEqual(alert_item["host"], self.host.name)
        self.assertEqual(alert_item["title"], "Disk usage high")
        self.assertNotIn("message", alert_item)
        self.assertNotIn("secret alert payload", alerts.content.decode())
        self.assertEqual(tasks.status_code, 200)
        task_item = tasks.json()["data"]["items"][0]
        self.assertEqual(task_item["target"], self.host.name)
        self.assertEqual(task_item["requested_by"], self.user.username)
        self.assertNotIn("error_message", task_item)
        self.assertNotIn("secret execution detail", tasks.content.decode())


class ReportsDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="reports-page-user",
            password="long-test-password",
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.profile.permissions = [
            "reports.view",
            "server.view",
            "reports.export",
        ]
        self.profile.save(update_fields=["permissions"])
        self.client.force_login(self.user)

    def test_reports_dashboard_shows_permitted_reports_and_live_preview_controls(self):
        ManagedHost.objects.create(
            name="dashboard-host",
            hostname="dashboard.example.test",
        )

        response = self.client.get(reverse("dashboard:reports"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Server inventory")
        self.assertContains(response, "Preview report")
        self.assertContains(response, "/api/v1/reports/")
        self.assertNotContains(response, "Alert history")

    def test_reports_dashboard_rejects_users_without_reports_view_permission(self):
        self.profile.permissions = ["server.view"]
        self.profile.save(update_fields=["permissions"])

        response = self.client.get(reverse("dashboard:reports"))

        self.assertEqual(response.status_code, 403)
