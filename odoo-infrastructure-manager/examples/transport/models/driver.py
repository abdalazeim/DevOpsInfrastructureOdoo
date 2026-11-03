"""Driver model for the transport module."""

from django.db import models

from apps.core.models import BaseModel


class Driver(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="الكود")
    name = models.CharField(max_length=255, verbose_name="الاسم")
    phone = models.CharField(max_length=20, blank=True, default="", verbose_name="الهاتف")
    license_number = models.CharField(
        max_length=50, blank=True, default="", verbose_name="رقم الرخصة"
    )
    hire_date = models.DateField(null=True, blank=True, verbose_name="تاريخ التوظيف")

    class Meta:
        db_table = "transport_drivers"
        verbose_name = "سائق"
        verbose_name_plural = "السائقون"
        ordering = ["name"]

    def __str__(self):
        return self.name
