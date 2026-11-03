"""Vehicle model for the transport module."""

from django.db import models

from apps.core.models import BaseModel


class Vehicle(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="الكود")
    plate = models.CharField(max_length=30, unique=True, verbose_name="لوحة المركبة")
    capacity_weight = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="سعة الوزن"
    )
    capacity_volume = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="سعة الحجم"
    )
    type = models.CharField(max_length=100, blank=True, default="", verbose_name="النوع")

    class Meta:
        db_table = "transport_vehicles"
        verbose_name = "مركبة"
        verbose_name_plural = "المركبات"
        ordering = ["plate"]

    def __str__(self):
        return f"{self.plate} ({self.code})"
