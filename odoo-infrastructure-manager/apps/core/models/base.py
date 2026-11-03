"""Generic abstract base models shared by every module in the template.

These models are domain-agnostic (no business logic). Any module can inherit
from them to get timestamping, soft-delete, or UUID primary keys for free.
"""

import uuid

from django.conf import settings
from django.db import models


class TimeStampModel(models.Model):
    """Adds created_at / updated_at to a model."""

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="تاريخ الإنشاء",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاريخ التحديث",
    )

    class Meta:
        abstract = True


class AuditStampModel(models.Model):
    """Adds created_by / updated_by (nullable FK to the User model)."""

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
        verbose_name="أُنشئ بواسطة",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_updated",
        verbose_name="حُدّث بواسطة",
    )

    class Meta:
        abstract = True


class AllObjects(models.Manager):
    def get_queryset(self):
        return super().get_queryset()


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def all_with_deleted(self):
        return super().get_queryset()

    def deleted_only(self):
        return super().get_queryset().filter(is_deleted=True)


class SoftDeleteModel(TimeStampModel):
    """Adds a soft-delete flag. Querysets exclude deleted rows by default."""

    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="محذوف",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاريخ الحذف",
    )

    objects = SoftDeleteManager()
    all_objects = AllObjects()

    class Meta:
        abstract = True

    def soft_delete(self):
        from django.utils import timezone

        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])


class BaseModel(TimeStampModel, AuditStampModel):
    """Combines timestamps + user stamps. Recommended base for most tables."""

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="نشط",
    )

    objects = models.Manager()
    all_objects = AllObjects()

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """Adds a UUID primary key (useful for distributed / sync-friendly ids)."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="المعرف",
    )

    class Meta:
        abstract = True
