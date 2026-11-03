"""Good (cargo type) model for the transport module."""

from django.db import models

from apps.core.models import BaseModel


class Good(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="الكود")
    name = models.CharField(max_length=255, verbose_name="الاسم")
    description = models.TextField(blank=True, default="", verbose_name="الوصف")
    unit = models.CharField(max_length=50, default="pcs", verbose_name="الوحدة")

    class Meta:
        db_table = "transport_goods"
        verbose_name = "نوع بضاعة"
        verbose_name_plural = "أنواع البضائع"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"
