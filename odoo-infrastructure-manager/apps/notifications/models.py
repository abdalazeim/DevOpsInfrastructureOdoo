from django.conf import settings
from django.db import models
from django.db.models import Q


class Notification(models.Model):
    class Category(models.TextChoices):
        ALERT = "alert", "Monitoring alerts"
        BACKUP = "backup", "Backups"
        AUTOMATION = "automation", "Automation"
        TASK = "task", "Tasks"
        SECURITY = "security", "Security"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    title = models.CharField(max_length=200)
    message = models.CharField(max_length=2000, blank=True)
    source_app = models.CharField(max_length=80, blank=True)
    source_model = models.CharField(max_length=100, blank=True)
    source_pk = models.CharField(max_length=100, blank=True)
    dedupe_key = models.CharField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(fields=["user", "read_at", "-created_at"], name="notif_user_read_time_idx"),
            models.Index(fields=["source_app", "source_model", "source_pk"], name="notif_source_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "category", "dedupe_key"],
                condition=Q(dedupe_key__isnull=False),
                name="uniq_notification_dedupe",
            )
        ]

    def __str__(self):
        return f"{self.title} ({self.user_id})"


class NotificationDelivery(models.Model):
    class Channel(models.TextChoices):
        EMAIL = "email", "Email"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENDING = "sending", "Sending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SUPPRESSED = "suppressed", "Suppressed"

    notification = models.OneToOneField(
        Notification,
        on_delete=models.CASCADE,
        related_name="email_delivery",
    )
    channel = models.CharField(
        max_length=12, choices=Channel.choices, default=Channel.EMAIL
    )
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING
    )
    attempt_count = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(db_index=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["next_attempt_at", "pk"]
        indexes = [
            models.Index(fields=["status", "next_attempt_at"], name="notif_delivery_due_idx")
        ]


class NotificationPreference(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    category = models.CharField(max_length=20, choices=Notification.Category.choices)
    in_app_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "category"], name="uniq_notification_preference"
            )
        ]
