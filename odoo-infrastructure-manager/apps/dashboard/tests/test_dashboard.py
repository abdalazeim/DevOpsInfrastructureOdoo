from unittest.mock import patch
import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.automation.models import ApprovedTaskTemplate, AutomationRun
from apps.automation.services.semaphore_client import SemaphoreClient, SemaphoreError
from apps.accounts.models import UserProfile
from apps.core.models import AuditLog
from apps.core.services.system_settings import get_setting
from apps.dashboard.services.traefik_service import TraefikReadOnlyService
from apps.dashboard.forms import ManagedHostForm
from apps.dashboard.views import _redact
from apps.infrastructure.models import ManagedHost, ServerGroup
from apps.security.models import Credential
from cryptography.fernet import Fernet
from apps.tasks.models import Task
from apps.tasks.services.task_service import append_task_log, create_task, transition_task

TEST_CREDENTIAL_KEY = Fernet.generate_key().decode("ascii")


class DashboardAccessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("operator", "operator@example.test", "test-password")
        self.client.force_login(self.user)

    def test_docker_discovery_is_not_configured_by_default(self):
        response = self.client.get(reverse("dashboard:containers"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Docker provider unavailable")

    def test_container_logs_require_container_to_be_discovered(self):
        response = self.client.get(reverse("dashboard:container_logs", args=["arbitrary-name"]))
        self.assertEqual(response.status_code, 503)

    @patch("infrastructure_engine.core.engine.SSHConnectionAdapter.inspect", return_value={
        "operating_system": "Linux", "os_version": "6.8.0", "architecture": "x86_64",
    })
    def test_server_connection_probe_updates_verified_metadata_and_audit(self, inspect):
        host = ManagedHost.objects.create(name="ssh-host", hostname="ssh.example.test")
        response = self.client.post(reverse("dashboard:test_server_connection", args=[host.pk]))
        self.assertEqual(response.status_code, 200)
        host.refresh_from_db()
        self.assertEqual(host.connection_status, ManagedHost.ConnectionStatus.ONLINE)
        self.assertEqual(host.operating_system, "Linux")
        self.assertTrue(host.last_connection_at)
        inspect.assert_called_once_with(host)
        self.assertTrue(AuditLog.objects.filter(module="infrastructure.operation", object_id=str(host.pk)).exists())

    @patch("infrastructure_engine.core.engine.SSHConnectionAdapter.inspect", side_effect=Exception("secret leaked?"))
    def test_unexpected_probe_errors_are_redacted_and_marked_unreachable(self, inspect):
        host = ManagedHost.objects.create(name="failing-host", hostname="fail.example.test")
        response = self.client.post(reverse("dashboard:test_server_connection", args=[host.pk]))
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"secret leaked?", response.content)
        host.refresh_from_db()
        self.assertEqual(host.connection_status, ManagedHost.ConnectionStatus.UNREACHABLE)

    def test_unconfigured_ssh_is_not_misreported_as_unreachable(self):
        host = ManagedHost.objects.create(name="no-credential", hostname="no-credential.example.test")
        response = self.client.post(reverse("dashboard:test_server_connection", args=[host.pk]))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["status"], "not_configured")
        host.refresh_from_db()
        self.assertEqual(host.connection_status, ManagedHost.ConnectionStatus.UNKNOWN)

    def test_granular_server_create_permission_does_not_require_legacy_admin_grant(self):
        operator = get_user_model().objects.create_user("server-registrar", password="test-password")
        profile, _ = UserProfile.objects.get_or_create(user=operator)
        profile.permissions = ["server.view", "server.create"]
        profile.save(update_fields=["permissions"])
        self.client.force_login(operator)
        response = self.client.post(reverse("dashboard:create_inventory_item", args=["host"]), {
            "name": "granular-host", "hostname": "granular.example.test", "environment": "staging",
            "server_type": "remote", "connection_type": "ssh", "ssh_port": "22",
            "ansible_limit": "granular-host", "description": "", "enabled": "on",
        })
        self.assertEqual(response.status_code, 302)
        host = ManagedHost.objects.get(name="granular-host")
        denied = self.client.post(
            reverse("dashboard:update_inventory_item", args=["host", host.pk]),
            {"name": "changed", "hostname": "changed.example.test"},
        )
        self.assertEqual(denied.status_code, 403)


class ApprovedAutomationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("admin", "admin@example.test", "test-password")
        self.client.force_login(self.user)
        self.host = ManagedHost.objects.create(name="prod", hostname="prod.example.test", ansible_limit="prod-web")
        self.template = ApprovedTaskTemplate.objects.create(
            name="Check services", project_id=1, template_id=2,
            category=ApprovedTaskTemplate.Category.DISCOVERY, enabled=True, read_only=True,
        )

    @patch("apps.dashboard.views.SemaphoreClient.start_task", return_value={"id": 42})
    def test_approved_template_starts_as_dry_run(self, start_task):
        response = self.client.post(reverse("dashboard:run_template", args=[self.template.pk]), {"mode": "dry_run"})
        self.assertEqual(response.status_code, 302)
        start_task.assert_called_once_with(1, 2, dry_run=True, limit="")
        run = AutomationRun.objects.get()
        self.assertTrue(run.dry_run)
        self.assertEqual(run.external_task_id, 42)

    @patch("apps.dashboard.views.SemaphoreClient.start_task")
    def test_read_only_template_cannot_be_launched_live(self, start_task):
        response = self.client.post(reverse("dashboard:run_template", args=[self.template.pk]),
                                    {"mode": "live", "confirm": "yes"})
        self.assertEqual(response.status_code, 400)
        start_task.assert_not_called()

    def test_live_run_requires_explicit_confirmation(self):
        self.template.read_only = False
        self.template.host = self.host
        self.template.category = ApprovedTaskTemplate.Category.SERVICE
        self.template.save()
        with patch("apps.dashboard.views.SemaphoreClient.start_task") as start_task:
            response = self.client.post(reverse("dashboard:run_template", args=[self.template.pk]), {"mode": "live"})
        self.assertEqual(response.status_code, 302)
        start_task.assert_not_called()

    def test_main_pages_render_for_infrastructure_operator(self):
        for route in ("dashboard:index", "dashboard:containers", "dashboard:inventory", "dashboard:automation_templates", "dashboard:odoo_services",
                      "dashboard:django_projects", "dashboard:database_services", "dashboard:backups",
                      "dashboard:alerts", "dashboard:audit", "dashboard:traefik"):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(reverse(route)).status_code, 200)

    def test_django_admin_route_is_removed(self):
        self.assertEqual(self.client.get("/admin/").status_code, 404)

    def test_dashboard_forces_english_ltr_even_with_old_arabic_session(self):
        session = self.client.session
        session["app_language"] = "ar"
        session.save()
        response = self.client.get(reverse("dashboard:index"))
        self.assertContains(response, 'lang="en" dir="ltr"')

    def test_dashboard_loads_enterprise_visual_system_after_page_styles(self):
        response = self.client.get(reverse("dashboard:index"))
        self.assertContains(response, "css/dashboard.css?v=2")
        self.assertContains(response, "css/enterprise-shell.css?v=1")
        self.assertLess(
            response.content.index(b"css/dashboard.css?v=2"),
            response.content.index(b"css/enterprise-shell.css?v=1"),
        )

    def test_global_settings_validate_store_and_audit_changes(self):
        invalid = self.client.post(reverse("dashboard:global_settings"), {
            "ssh_timeout_seconds": 8, "operation_timeout_seconds": 300,
            "monitoring_collection_interval_seconds": 2, "metrics_retention_days": 30,
        })
        self.assertEqual(invalid.status_code, 200)
        self.assertFalse(get_setting("monitoring_collection_interval_seconds"))

        saved = self.client.post(reverse("dashboard:global_settings"), {
            "ssh_timeout_seconds": 8, "operation_timeout_seconds": 300,
            "monitoring_collection_interval_seconds": 120, "metrics_retention_days": 30,
        })
        self.assertEqual(saved.status_code, 302)
        self.assertEqual(get_setting("monitoring_collection_interval_seconds"), "120")
        self.assertTrue(AuditLog.objects.filter(module="core.settings", object_id="monitoring_collection_interval_seconds").exists())

    @override_settings(RUNTIME_SETTING_ENV_OVERRIDES={"ssh_timeout_seconds": "17"})
    def test_environment_overrides_are_read_only_on_settings_page(self):
        response = self.client.get(reverse("dashboard:global_settings"))
        self.assertContains(response, 'name="ssh_timeout_seconds"')
        self.assertContains(response, 'value="17"')
        self.assertContains(response, "controlled by the environment")

    def test_task_center_reads_persisted_tasks_and_redacted_logs(self):
        task = create_task(name="SSH metadata probe", operation="server.test_connection", actor=self.user)
        transition_task(task.pk, Task.Status.QUEUED, actor=self.user)
        append_task_log(task.pk, content="Connected with password=must-not-render")
        listing = self.client.get(reverse("dashboard:tasks"))
        self.assertContains(listing, "SSH metadata probe")
        detail = self.client.get(reverse("dashboard:task_detail", args=[task.pk]))
        self.assertContains(detail, "[REDACTED]")
        self.assertNotContains(detail, "must-not-render")

    def test_task_cancel_endpoint_uses_shared_state_transition(self):
        task = create_task(name="Queued operation", operation="server.probe", actor=self.user)
        transition_task(task.pk, Task.Status.QUEUED, actor=self.user)
        response = self.client.post(reverse("dashboard:cancel_task", args=[task.pk]))
        self.assertEqual(response.status_code, 302)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.CANCELLED)

    def test_host_can_be_managed_from_dashboard_inventory(self):
        response = self.client.post(reverse("dashboard:create_inventory_item", args=["host"]), {
            "name": "test-host", "hostname": "test.example.test", "environment": "development",
            "server_type": "remote", "connection_type": "ssh", "ssh_port": "22",
            "ansible_limit": "test-host", "description": "", "enabled": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ManagedHost.objects.filter(name="test-host").exists())

    @override_settings(CREDENTIAL_ENCRYPTION_KEY=TEST_CREDENTIAL_KEY)
    def test_server_inventory_captures_remote_connection_metadata_without_secrets(self):
        group = ServerGroup.objects.create(name="Production")
        credential = Credential(name="Production SSH", kind=Credential.Kind.SSH_PASSWORD, username="ops")
        credential.set_secret("test-secret-value")
        credential.save()
        form = ManagedHostForm(data={
            "name": "remote-host", "hostname": "remote.example.test",
            "server_type": "remote", "connection_type": "ssh", "ssh_port": "2222",
            "credential": str(credential.pk), "groups": [str(group.pk)],
            "operating_system": "Ubuntu", "os_version": "24.04", "architecture": "x86_64",
            "environment": "production", "location": "Tripoli DC", "ansible_limit": "remote-host",
            "description": "Managed production host", "enabled": "on",
        })
        self.assertTrue(form.is_valid(), form.errors)
        host = form.save()
        self.assertEqual(host.ssh_port, 2222)
        self.assertEqual(host.connection_status, ManagedHost.ConnectionStatus.UNKNOWN)
        self.assertEqual(list(host.groups.all()), [group])
        self.assertEqual(host.credential, credential)
        self.assertEqual(host.credential_reference, f"credential:{credential.pk}")

        response = self.client.get(reverse("dashboard:inventory"))
        self.assertContains(response, "Production SSH")
        self.assertNotContains(response, "test-secret-value")
        self.assertNotContains(response, credential.encrypted_secret)

    def test_local_host_form_forces_direct_process_connection(self):
        form = ManagedHostForm(data={
            "name": "local-host", "hostname": "localhost", "server_type": "remote",
            "connection_type": "ssh", "ssh_port": "22", "environment": "development",
            "ansible_limit": "", "description": "", "enabled": "on", "is_local": "on",
        })
        self.assertTrue(form.is_valid(), form.errors)
        host = form.save()
        self.assertEqual(host.server_type, ManagedHost.ServerType.LOCAL)
        self.assertEqual(host.connection_type, ManagedHost.ConnectionType.LOCAL)

    def test_restore_requires_separate_permission_and_typed_confirmation(self):
        restore = ApprovedTaskTemplate.objects.create(
            name="Restore database", project_id=1, template_id=9,
            category=ApprovedTaskTemplate.Category.RESTORE, enabled=True, read_only=False, host=self.host,
        )
        operator = get_user_model().objects.create_user("backup-operator", password="test-password")
        profile, _ = UserProfile.objects.get_or_create(user=operator)
        profile.permissions = ["infrastructure_manage"]
        profile.save(update_fields=["permissions"])
        self.client.force_login(operator)
        with patch("apps.dashboard.views.SemaphoreClient.start_task") as start_task:
            denied = self.client.post(reverse("dashboard:run_template", args=[restore.pk]), {"mode": "dry_run"})
        self.assertEqual(denied.status_code, 403)
        start_task.assert_not_called()

        self.client.force_login(self.user)
        with patch("apps.dashboard.views.SemaphoreClient.start_task") as start_task:
            missing_confirmation = self.client.post(reverse("dashboard:run_template", args=[restore.pk]),
                                                   {"mode": "live", "confirm": "yes"})
        self.assertEqual(missing_confirmation.status_code, 400)
        start_task.assert_not_called()


class LegacyApiSafetyTests(TestCase):
    @override_settings(INFRA_DOCKER_READ_ENABLED=False)
    def test_unauthenticated_dashboard_redirects_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    def test_login_uses_english_session_form(self):
        user = get_user_model().objects.create_user("english-user", password="StrongPassword123!")
        page = self.client.get(reverse("login"))
        self.assertContains(page, "Sign in")
        self.assertContains(page, 'lang="en"')
        self.assertNotContains(page, "تسجيل الدخول")
        response = self.client.post(reverse("login"), {
            "username": user.username,
            "password": "StrongPassword123!",
            "next": "",
        })
        self.assertRedirects(response, reverse("dashboard:index"), fetch_redirect_response=False)
        self.assertTrue(response.wsgi_request.user.is_authenticated)


class SemaphoreClientTests(TestCase):
    @override_settings(SEMAPHORE_URL="https://semaphore.example.test", SEMAPHORE_API_TOKEN="secret-token",
                       SEMAPHORE_TIMEOUT_SECONDS=3)
    @patch("apps.automation.services.semaphore_client.urlopen")
    def test_task_request_uses_fixed_endpoint_and_dry_run_payload(self, urlopen):
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = b'{"id": 31}'
        result = SemaphoreClient().start_task(4, 8, dry_run=True, limit="prod-web")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://semaphore.example.test/api/project/4/tasks")
        self.assertEqual(json.loads(request.data), {"template_id": 8, "dry_run": True, "limit": "prod-web"})
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-token")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 3)
        self.assertEqual(result, {"id": 31})

    @override_settings(SEMAPHORE_URL="http://semaphore.example.test", SEMAPHORE_API_TOKEN="token")
    def test_remote_http_url_is_rejected(self):
        with self.assertRaises(SemaphoreError):
            SemaphoreClient()


class TraefikProviderTests(TestCase):
    def test_unconfigured_provider_is_explicit(self):
        result = TraefikReadOnlyService.inspect()
        self.assertFalse(result["available"])
        self.assertEqual(result["routers"], [])

    @override_settings(TRAEFIK_API_URL="http://external.example.test")
    def test_remote_plain_http_provider_is_rejected_without_request(self):
        with patch("apps.dashboard.services.traefik_service.build_opener") as build_opener:
            result = TraefikReadOnlyService.inspect()
        self.assertFalse(result["available"])
        build_opener.assert_not_called()

    def test_task_log_redaction_covers_json_credentials_and_bearer_values(self):
        safe = _redact('{"password":"hidden", "Authorization":"Bearer eyJ.abc.xyz"}')
        self.assertNotIn("hidden", safe)
        self.assertNotIn("eyJ.abc.xyz", safe)
