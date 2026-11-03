"""Example module — generic CRUD model demonstrating the Master Template.

Copy this module (``apps/modules/example``) to bootstrap a new business module:
1. Rename the app and its config class.
2. Define your own models here (or extend with domain fields).
3. Register permissions in ``permissions/`` and wire them in ``apps.py``.
4. Add the app to ``INSTALLED_APPS``.
"""

from django.db import models

from apps.core.models import BaseModel


class ExampleItem(BaseModel):
    """A minimal, reusable sample entity.

    Uses the generic ``BaseModel`` (timestamps + created_by/updated_by +
    is_active) and provides a soft-delete flag through ``SoftDeleteModel``
    if desired — see ``apps/core/models/base.py``.
    """

    name = models.CharField(max_length=255, verbose_name="الاسم")
    code = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="الكود",
        help_text="كود فريد يستخدم كمعرّف مرجعي",
    )
    description = models.TextField(blank=True, default="", verbose_name="الوصف")
    quantity = models.PositiveIntegerField(default=0, verbose_name="الكمية")
    sort_order = models.IntegerField(default=0, verbose_name="ترتيب الفرز")

    class Meta:
        db_table = "example_items"
        verbose_name = "عنصر المثال"
        verbose_name_plural = "عناصر المثال"
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["code"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"
