import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.notifications.models import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
)
from apps.notifications.services.delivery import dispatch_pending_notifications
from apps.notifications.services.publishing import (
    publish_notification,
    save_preferences,
)


class NotificationTests(TestCase):
    def setUp(self):
        self.user = self._user(
            "notification-operator",
            "operator@example.test",
            ["monitoring.view", "task.view"],
        )
        self.other_user = self._user(
            "other-operator", "other@example.test", ["monitoring.view", "task.view"]
        )

    @staticmethod
    def _user(username, email, permissions):
        user = get_user_model().objects.create_user(
            username=username, email=email
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.permissions = permissions
        profile.save(update_fields=["permissions"])
        return user

    def _publish_alert(self, **kwargs):
        return publish_notification(
            category=Notification.Category.ALERT,
            title="CPU threshold exceeded",
            message="test-host: CPU is high.",
            source_app="monitoring",
            source_model="AlertEvent",
            source_pk="77",
            dedupe_key="alert-77-occurrence-1",
            **kwargs,
        )

    def test_publisher_targets_only_active_users_with_domain_permission(self):
        inactive = self._user(
            "inactive-operator", "inactive@example.test", ["monitoring.view"]
        )
        inactive.is_active = False
        inactive.save(update_fields=["is_active"])
        self._user("unprivileged", "none@example.test", [])

        result = self._publish_alert()

        self.assertEqual(result.created, 2)
        self.assertSetEqual(
            set(Notification.objects.values_list("user__username", flat=True)),
            {"notification-operator", "other-operator"},
        )
        self.assertFalse(NotificationDelivery.objects.exists())

    def test_deduplication_is_per_recipient_and_default_is_in_app_only(self):
        first = self._publish_alert()
        second = self._publish_alert()

        self.assertEqual(first.created, 2)
        self.assertEqual(second.created, 0)
        self.assertEqual(Notification.objects.count(), 2)
        self.assertFalse(NotificationDelivery.objects.exists())

    def test_preferences_support_email_only_and_reject_missing_address(self):
        save_preferences(
            self.user,
            [{
                "category": Notification.Category.ALERT,
                "in_app_enabled": False,
                "email_enabled": True,
            }],
        )
        result = self._publish_alert()

        self.assertEqual(result.created, 2)
        self.assertEqual(result.email_queued, 1)
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)
        self.assertEqual(NotificationDelivery.objects.count(), 1)
        self.other_user.email = ""
        self.other_user.save(update_fields=["email"])
        with self.assertRaisesMessage(ValidationError, "Add an email address"):
            save_preferences(
                self.other_user,
                [{
                    "category": Notification.Category.ALERT,
                    "email_enabled": True,
                }],
            )

    def test_disabled_channels_suppress_notification(self):
        save_preferences(
            self.user,
            [{
                "category": Notification.Category.ALERT,
                "in_app_enabled": False,
                "email_enabled": False,
            }],
        )

        result = self._publish_alert()

        self.assertEqual(result.created, 1)
        self.assertFalse(Notification.objects.filter(user=self.user).exists())
        self.assertEqual(Notification.objects.count(), 1)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="infra@example.test",
    )
    def test_delivery_sends_once_and_updates_state(self):
        NotificationPreference.objects.create(
            user=self.user,
            category=Notification.Category.TASK,
            email_enabled=True,
        )
        publish_notification(
            category=Notification.Category.TASK,
            title="Task completed",
            message="Task 41 completed.",
            source_app="tasks",
            source_model="Task",
            source_pk="41",
        )

        first = dispatch_pending_notifications()
        second = dispatch_pending_notifications()
        delivery = NotificationDelivery.objects.get()

        self.assertEqual(first.sent, 1)
        self.assertEqual(second.sent, 0)
        self.assertEqual(delivery.status, NotificationDelivery.Status.SENT)
        self.assertEqual(delivery.attempt_count, 1)
        self.assertEqual(delivery.sent_at is not None, True)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_disabling_email_suppresses_queued_delivery(self):
        NotificationPreference.objects.create(
            user=self.user,
            category=Notification.Category.TASK,
            email_enabled=True,
        )
        publish_notification(
            category=Notification.Category.TASK,
            title="Task completed",
            message="Task 43 completed.",
            source_app="tasks",
            source_model="Task",
            source_pk="43",
        )
        save_preferences(
            self.user,
            [{
                "category": Notification.Category.TASK,
                "email_enabled": False,
            }],
        )

        with patch("apps.notifications.services.delivery.send_mail") as send:
            result = dispatch_pending_notifications()

        delivery = NotificationDelivery.objects.get()
        self.assertEqual(result.suppressed, 0)
        self.assertEqual(delivery.status, NotificationDelivery.Status.SUPPRESSED)
        send.assert_not_called()

    @override_settings(DEFAULT_FROM_EMAIL="infra@example.test")
    @patch(
        "apps.notifications.services.delivery.send_mail",
        side_effect=OSError("sensitive SMTP diagnostic"),
    )
    def test_delivery_retries_to_limit_and_does_not_stop_later_messages(self, send):
        for user in (self.user, self.other_user):
            NotificationPreference.objects.create(
                user=user,
                category=Notification.Category.TASK,
                email_enabled=True,
            )
        publish_notification(
            category=Notification.Category.TASK,
            title="Task failed",
            message="A task failed.",
            source_app="tasks",
            source_model="Task",
            source_pk="42",
        )

        results = [
            dispatch_pending_notifications(now=timezone.now() + timedelta(days=1))
            for _ in range(5)
        ]
        deliveries = list(NotificationDelivery.objects.order_by("pk"))

        self.assertEqual(send.call_count, 10)
        self.assertEqual(sum(result.failed for result in results), 2)
        self.assertTrue(
            all(item.status == NotificationDelivery.Status.FAILED for item in deliveries)
        )
        self.assertTrue(all(item.attempt_count == 5 for item in deliveries))
        self.assertTrue(all(item.last_error == "OSError" for item in deliveries))
        self.assertNotIn("sensitive", " ".join(item.last_error for item in deliveries))

    def test_api_is_scoped_to_session_user_and_supports_preferences(self):
        Notification.objects.create(
            user=self.user,
            category=Notification.Category.ALERT,
            title="Visible",
        )
        Notification.objects.create(
            user=self.other_user,
            category=Notification.Category.ALERT,
            title="Private",
        )
        self.client.force_login(self.user)

        response = self.client.get("/api/v1/notifications/?unread=true")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["title"], "Visible")
        self.assertEqual(payload["items"][0]["email_status"], "not_enabled")
        self.assertEqual(payload["meta"]["unread_count"], 1)

        private_id = Notification.objects.get(user=self.other_user).pk
        denied = self.client.post(
            f"/api/v1/notifications/{private_id}/read/"
        )
        self.assertEqual(denied.status_code, 404)

        preference_response = self.client.patch(
            "/api/v1/notifications/preferences/",
            data=json.dumps({
                "preferences": [{
                    "category": "alert",
                    "in_app_enabled": False,
                    "email_enabled": True,
                }]
            }),
            content_type="application/json",
        )
        self.assertEqual(preference_response.status_code, 200)
        preference = NotificationPreference.objects.get(user=self.user, category="alert")
        self.assertFalse(preference.in_app_enabled)
        self.assertTrue(preference.email_enabled)

    def test_api_read_all_updates_only_current_users_notifications(self):
        Notification.objects.create(
            user=self.user, category=Notification.Category.TASK, title="Mine"
        )
        other = Notification.objects.create(
            user=self.other_user, category=Notification.Category.TASK, title="Theirs"
        )
        self.client.force_login(self.user)

        response = self.client.post("/api/v1/notifications/read-all/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["updated"], 1)
        other.refresh_from_db()
        self.assertIsNone(other.read_at)

    def test_dashboard_renders_personal_inbox_and_channel_preferences(self):
        Notification.objects.create(
            user=self.user,
            category=Notification.Category.ALERT,
            title="Dashboard alert",
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard:notifications"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard alert")
        self.assertContains(response, "Delivery preferences")
        self.assertContains(response, "Mark all as read")

    def test_dashboard_preferences_and_mark_read_are_user_scoped(self):
        notification = Notification.objects.create(
            user=self.user,
            category=Notification.Category.TASK,
            title="Dashboard task",
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("dashboard:notification_preferences"),
            {
                f"channel_{category}": "off"
                for category, _ in Notification.Category.choices
            },
        )

        self.assertEqual(response.status_code, 302)
        preference = NotificationPreference.objects.get(user=self.user, category="task")
        self.assertFalse(preference.in_app_enabled)
        self.assertFalse(preference.email_enabled)

        response = self.client.post(
            reverse("dashboard:notification_read", args=[notification.pk])
        )
        self.assertEqual(response.status_code, 302)
        notification.refresh_from_db()
        self.assertIsNotNone(notification.read_at)

    def test_delivery_management_command_reports_counts(self):
        output = []

        class Output:
            def write(self, text):
                output.append(text)

        call_command("dispatch_pending_notifications", stdout=Output())

        self.assertIn("Notifications sent: 0", output[0])
