from datetime import timedelta
from io import BytesIO
from io import StringIO
import json
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.infrastructure.models import ManagedHost
from apps.monitoring.models import AlertEvent, AlertRule, MetricCollection, ResourceSample
from apps.monitoring.services.collection import collect_host, prune_metrics
from apps.notifications.models import Notification, NotificationDelivery, NotificationPreference
from apps.notifications.services.delivery import dispatch_pending_notifications

ensure_notification_queued_column = import_module(
    "apps.monitoring.migrations.0005_repair_alert_notification_queued_column"
).ensure_notification_queued_column


class AlertNotificationColumnRepairTests(TestCase):
    def test_repairs_the_column_when_migration_record_exists_but_column_is_missing(self):
        model = MagicMock()
        model._meta.db_table = "monitoring_alertevent"
        model._meta.get_field.return_value.column = "last_notification_queued_at"
        apps = MagicMock()
        apps.get_model.return_value = model
        schema_editor = MagicMock()
        cursor = MagicMock()
        schema_editor.connection.cursor.return_value.__enter__.return_value = cursor
        schema_editor.connection.introspection.table_names.return_value = [
            "monitoring_alertevent"
        ]
        schema_editor.connection.introspection.get_table_description.return_value = [
            SimpleNamespace(name="id")
        ]

        ensure_notification_queued_column(apps, schema_editor)

        schema_editor.add_field.assert_called_once_with(
            model, model._meta.get_field.return_value
        )

    def test_does_not_add_a_column_that_already_exists(self):
        model = MagicMock()
        model._meta.db_table = "monitoring_alertevent"
        model._meta.get_field.return_value.column = "last_notification_queued_at"
        apps = MagicMock()
        apps.get_model.return_value = model
        schema_editor = MagicMock()
        cursor = MagicMock()
        schema_editor.connection.cursor.return_value.__enter__.return_value = cursor
        schema_editor.connection.introspection.table_names.return_value = [
            "monitoring_alertevent"
        ]
        schema_editor.connection.introspection.get_table_description.return_value = [
            SimpleNamespace(name="id"),
            SimpleNamespace(name="last_notification_queued_at"),
        ]

        ensure_notification_queued_column(apps, schema_editor)

        schema_editor.add_field.assert_not_called()


def metrics(cpu=91, available=True):
    return {
        "available": available,
        "source": "test-provider",
        "reason": "provider unavailable" if not available else "",
        "cpu_percent": cpu if available else None,
        "memory": {"percent": 50, "total_bytes": 1000, "used_bytes": 500} if available else None,
        "disk": {"percent": 40} if available else None,
        "network_rx_bytes_per_second": 1 if available else None,
        "network_tx_bytes_per_second": 2 if available else None,
    }


class MetricCollectionTests(TestCase):
    def setUp(self):
        self.host = ManagedHost.objects.create(
            name="local-test", hostname="localhost", is_local=True
        )

    def _email_subscriber(self):
        user = get_user_model().objects.create_user(
            username="alert-subscriber", email="alerts@example.test"
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.permissions = ["monitoring.view"]
        profile.save(update_fields=["permissions"])
        NotificationPreference.objects.create(
            user=user,
            category=Notification.Category.ALERT,
            email_enabled=True,
        )
        return user

    @patch("apps.monitoring.services.collection.MetricsService.collect")
    def test_collection_creates_sample_and_success_record_then_respects_interval(self, collect):
        collect.return_value = metrics()
        result = collect_host(self.host, interval_seconds=60)
        skipped = collect_host(self.host, interval_seconds=60)

        self.assertEqual(result.status, "success")
        self.assertEqual(skipped.status, "skipped")
        self.assertEqual(ResourceSample.objects.count(), 1)
        self.assertEqual(MetricCollection.objects.count(), 1)
        collect.assert_called_once()

    @patch("apps.monitoring.services.collection.MetricsService.collect")
    def test_failed_provider_attempt_is_recorded(self, collect):
        collect.return_value = metrics(available=False)

        result = collect_host(self.host, interval_seconds=60)

        record = MetricCollection.objects.get()
        self.assertEqual(result.status, "failed")
        self.assertEqual(record.status, MetricCollection.Status.FAILED)
        self.assertEqual(record.error_message, "provider unavailable")
        self.assertFalse(ResourceSample.objects.exists())

    @patch("apps.monitoring.services.collection.MetricsService.collect", side_effect=RuntimeError)
    def test_provider_exception_is_recorded_without_losing_the_attempt(self, collect):
        result = collect_host(self.host, interval_seconds=60)

        self.assertEqual(result.status, "failed")
        self.assertIn("RuntimeError", result.reason)
        self.assertEqual(MetricCollection.objects.get().status, MetricCollection.Status.FAILED)
        collect.assert_called_once()

    @patch("apps.monitoring.services.collection.MetricsService.collect")
    def test_alert_deduplicates_tracks_occurrences_resolves_and_reopens(self, collect):
        rule = AlertRule.objects.create(
            name="CPU high", metric=AlertRule.Metric.CPU, threshold=80, enabled=True
        )
        collect.return_value = metrics(cpu=91)
        first = collect_host(self.host, interval_seconds=0)
        second = collect_host(self.host, interval_seconds=0)
        event = AlertEvent.objects.get()
        self.assertEqual(first.alerts_created, 1)
        self.assertEqual(second.alerts_created, 0)
        self.assertEqual(event.occurrences, 2)

        collect.return_value = metrics(cpu=10)
        collect_host(self.host, interval_seconds=0)
        event.refresh_from_db()
        self.assertIsNotNone(event.resolved_at)

        collect.return_value = metrics(cpu=95)
        collect_host(self.host, interval_seconds=0)
        self.assertEqual(AlertEvent.objects.filter(rule=rule).count(), 2)

    @patch("apps.monitoring.services.collection.MetricsService.collect")
    def test_missing_metric_does_not_resolve_or_increment_an_active_alert(self, collect):
        rule = AlertRule.objects.create(
            name="CPU partial", metric=AlertRule.Metric.CPU, threshold=80, enabled=True
        )
        event = AlertEvent.objects.create(
            rule=rule, host=self.host, title="CPU threshold exceeded", occurrences=2
        )
        collect.return_value = metrics(cpu=None)

        collect_host(self.host, interval_seconds=0)

        event.refresh_from_db()
        self.assertIsNone(event.resolved_at)
        self.assertEqual(event.occurrences, 2)

    @patch("apps.monitoring.services.collection.MetricsService.collect")
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="infra@example.test",
    )
    def test_alert_notification_is_queued_then_delivered_once(self, collect):
        self._email_subscriber()
        AlertRule.objects.create(
            name="CPU email", metric=AlertRule.Metric.CPU, threshold=80, enabled=True
        )
        collect.return_value = metrics()

        result = collect_host(self.host, interval_seconds=0)

        event = AlertEvent.objects.get()
        self.assertEqual(result.alerts_created, 1)
        self.assertEqual(event.notification_status, AlertEvent.NotificationStatus.PENDING)
        self.assertEqual(Notification.objects.filter(source_model="AlertEvent").count(), 1)
        self.assertEqual(NotificationDelivery.objects.count(), 1)
        delivery_result = dispatch_pending_notifications()

        event.refresh_from_db()
        self.assertEqual(delivery_result.sent, 1)
        self.assertEqual(event.notification_status, AlertEvent.NotificationStatus.SENT)
        self.assertEqual(len(mail.outbox), 1)

    @patch("apps.monitoring.services.collection.MetricsService.collect")
    @patch("apps.notifications.services.delivery.send_mail", side_effect=OSError("SMTP down"))
    @override_settings(DEFAULT_FROM_EMAIL="infra@example.test")
    def test_email_failure_is_retried_and_persisted(self, send, collect):
        self._email_subscriber()
        AlertRule.objects.create(
            name="CPU email failure", metric=AlertRule.Metric.CPU, threshold=80, enabled=True
        )
        collect.return_value = metrics()

        collect_host(self.host, interval_seconds=0)
        for _ in range(5):
            dispatch_pending_notifications(now=timezone.now() + timedelta(days=1))

        event = AlertEvent.objects.get()
        delivery = NotificationDelivery.objects.get()
        self.assertEqual(delivery.attempt_count, 5)
        self.assertEqual(delivery.status, NotificationDelivery.Status.FAILED)
        self.assertEqual(delivery.last_error, "OSError")
        self.assertEqual(event.notification_status, AlertEvent.NotificationStatus.FAILED)
        self.assertIn("failed", event.notification_error.lower())
        self.assertEqual(send.call_count, 5)

    def test_prune_removes_expired_samples_and_collection_records(self):
        sample = ResourceSample.objects.create(host=self.host, source="test")
        MetricCollection.objects.create(
            host=self.host, sample=sample, source="test",
            status=MetricCollection.Status.SUCCESS,
        )
        old = timezone.now() - timedelta(days=40)
        ResourceSample.objects.filter(pk=sample.pk).update(captured_at=old)
        MetricCollection.objects.filter(sample=sample).update(captured_at=old)

        deleted_samples, deleted_collections = prune_metrics(retention_days=30)

        self.assertEqual(deleted_samples, 1)
        self.assertEqual(deleted_collections, 1)
        self.assertFalse(ResourceSample.objects.exists())
        self.assertFalse(MetricCollection.objects.exists())

    @patch("apps.monitoring.management.commands.collect_infra_metrics.prune_metrics")
    @patch("apps.monitoring.management.commands.collect_infra_metrics.get_runtime_setting")
    def test_command_prunes_even_when_no_targets_are_configured(self, get_setting, prune):
        get_setting.side_effect = [60, 30]
        self.host.enabled = False
        self.host.save(update_fields=["enabled"])

        with self.assertRaises(CommandError):
            call_command("collect_infra_metrics", stdout=StringIO(), stderr=StringIO())

        prune.assert_called_once_with(30)

    @patch("apps.monitoring.management.commands.collect_infra_metrics.collect_host")
    @patch("apps.monitoring.management.commands.collect_infra_metrics.prune_metrics")
    @patch("apps.monitoring.management.commands.collect_infra_metrics.get_runtime_setting")
    def test_command_reports_provider_failures_after_attempting_all_hosts(
        self, get_setting, prune, collect,
    ):
        second_host = ManagedHost.objects.create(
            name="remote-test", hostname="remote.test", prometheus_instance="remote:9100"
        )
        get_setting.side_effect = [60, 30]
        prune.return_value = (0, 0)
        collect.side_effect = [
            type("Result", (), {"status": "failed", "source": "test", "reason": "down",
                                "alerts_created": 0})(),
            type("Result", (), {"status": "success", "source": "test", "reason": "",
                                "alerts_created": 0})(),
        ]

        with self.assertRaises(CommandError):
            call_command("collect_infra_metrics", stdout=StringIO(), stderr=StringIO())

        self.assertEqual(collect.call_count, 2)
        prune.assert_called_once_with(30)
        self.assertTrue(ManagedHost.objects.filter(pk=second_host.pk).exists())


class MonitoringAPITests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="monitor", password="long-test-password"
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.host = ManagedHost.objects.create(
            name="api-local", hostname="localhost", is_local=True
        )

    def grant(self, *permissions):
        self.profile.permissions = list(permissions)
        self.profile.save(update_fields=["permissions"])
        self.client.force_login(self.user)

    def test_api_requires_login_and_monitoring_permission(self):
        self.assertEqual(self.client.get("/api/v1/monitoring/targets/").status_code, 401)
        self.grant("task.view")
        self.assertEqual(self.client.get("/api/v1/monitoring/targets/").status_code, 403)

    def test_target_and_sample_apis_are_paginated_and_permission_checked(self):
        self.grant("monitoring.view")
        target_response = self.client.get("/api/v1/monitoring/targets/")
        self.assertEqual(target_response.status_code, 200)
        self.assertEqual(target_response.json()["data"]["items"][0]["id"], self.host.pk)
        sample = ResourceSample.objects.create(
            host=self.host, source="test", cpu_percent=42
        )
        sample_response = self.client.get(
            f"/api/v1/monitoring/samples/?host={self.host.pk}"
        )
        self.assertEqual(sample_response.status_code, 200)
        self.assertEqual(
            sample_response.json()["data"]["items"][0]["id"], sample.pk
        )

    def test_rule_api_enforces_manage_permission_and_validates_threshold(self):
        self.grant("monitoring.view")
        denied = self.client.post(
            "/api/v1/monitoring/rules/",
            data='{"name":"Too high","metric":"cpu_percent","threshold":101}',
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 403)

        self.grant("monitoring.alert.manage")
        invalid = self.client.post(
            "/api/v1/monitoring/rules/",
            data='{"name":"Too high","metric":"cpu_percent","threshold":101}',
            content_type="application/json",
        )
        self.assertEqual(invalid.status_code, 400)
        valid = self.client.post(
            "/api/v1/monitoring/rules/",
            data='{"name":"CPU API","metric":"cpu_percent","threshold":80,"enabled":true}',
            content_type="application/json",
        )
        self.assertEqual(valid.status_code, 201)
        self.assertEqual(AlertRule.objects.get().threshold, 80)

    def test_collection_history_and_alert_state_filters(self):
        self.grant("monitoring.view")
        MetricCollection.objects.create(
            host=self.host, source="test", status=MetricCollection.Status.FAILED,
            error_message="offline",
        )
        failed = self.client.get("/api/v1/monitoring/collections/?status=failed")
        self.assertEqual(failed.status_code, 200)
        self.assertEqual(failed.json()["data"]["items"][0]["error_message"], "offline")
        event = AlertEvent.objects.create(title="Open", host=self.host)
        open_events = self.client.get("/api/v1/monitoring/alerts/?state=open")
        self.assertEqual(open_events.status_code, 200)
        self.assertEqual(open_events.json()["data"]["items"][0]["id"], event.pk)

    def test_acknowledgement_has_dedicated_permission(self):
        event = AlertEvent.objects.create(title="Manual alert", host=self.host)
        self.grant("monitoring.view")
        denied = self.client.post(
            f"/api/v1/monitoring/alerts/{event.pk}/acknowledge/"
        )
        self.assertEqual(denied.status_code, 403)

        self.grant("monitoring.alert.acknowledge")
        response = self.client.post(
            f"/api/v1/monitoring/alerts/{event.pk}/acknowledge/"
        )
        self.assertEqual(response.status_code, 200)
        event.refresh_from_db()
        self.assertIsNotNone(event.acknowledged_at)

    def test_alert_page_accepts_monitoring_view_permission(self):
        self.grant("monitoring.view")
        MetricCollection.objects.create(
            host=self.host, source="test", status=MetricCollection.Status.FAILED,
            error_message="provider unavailable",
        )
        response = self.client.get("/dashboard/alerts/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Collection history")
        self.assertContains(response, "provider unavailable")


class PrometheusAdapterTests(TestCase):
    @override_settings(PROMETHEUS_URL="https://user:secret@prom.example")
    @patch("apps.dashboard.services.metrics_service.urlopen")
    def test_prometheus_rejects_embedded_credentials_before_network_access(self, urlopen):
        from apps.dashboard.services.metrics_service import MetricsService

        result = MetricsService._prometheus_metrics("node:9100")

        self.assertFalse(result["available"])
        urlopen.assert_not_called()

    @override_settings(PROMETHEUS_URL="https://prom.example")
    @patch("apps.dashboard.services.metrics_service.urlopen")
    def test_prometheus_accepts_partial_metric_results_without_fabricating_cpu(self, urlopen):
        from apps.dashboard.services.metrics_service import MetricsService

        values = {
            "node_memory_MemTotal_bytes": "1000",
            "node_memory_MemAvailable_bytes": "400",
        }

        def fake_response(url, timeout):
            query = parse_qs(urlsplit(url).query)["query"][0]
            value = next(
                (result for metric, result in values.items() if metric in query), None
            )
            result = [{"value": [0, value]}] if value else []
            return BytesIO(json.dumps({
                "status": "success", "data": {"result": result}
            }).encode())

        urlopen.side_effect = fake_response
        result = MetricsService._prometheus_metrics("node:9100")

        self.assertTrue(result["available"])
        self.assertIsNone(result["cpu_percent"])
        self.assertEqual(result["memory"]["percent"], 60.0)
        self.assertIsNone(result["disk"])
