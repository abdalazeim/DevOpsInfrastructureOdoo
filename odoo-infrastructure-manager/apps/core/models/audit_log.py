from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "create", "إنشاء"
        UPDATE = "update", "تحديث"
        DELETE = "delete", "حذف"
        LOGIN = "login", "دخول"
        LOGOUT = "logout", "خروج"
        APPROVE = "approve", "اعتماد"
        REJECT = "reject", "رفض"
        OTHER = "other", "أخرى"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name="المستخدم",
    )
    action = models.CharField(
        max_length=20, choices=Action.choices, verbose_name="الإجراء"
    )
    module = models.CharField(max_length=100, blank=True, default="", verbose_name="الوحدة")
    object_id = models.CharField(
        max_length=100, blank=True, default="", verbose_name="معرف الكائن"
    )
    object_repr = models.CharField(
        max_length=255, blank=True, default="", verbose_name="وصف الكائن"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="عنوان IP")
    old_value = models.JSONField(null=True, blank=True, verbose_name="القيمة القديمة")
    new_value = models.JSONField(null=True, blank=True, verbose_name="القيمة الجديدة")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="وقت الإجراء")

    class Meta:
        db_table = "audit_logs"
        verbose_name = "سجل تدقيق"
        verbose_name_plural = "سجلات التدقيق"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["module", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.get_action_display()} - {self.module} - {self.object_repr}"
