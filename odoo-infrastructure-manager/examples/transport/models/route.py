"""Route model for the transport module."""

from django.db import models

from apps.core.models import BaseModel


class Route(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="الكود")
    name = models.CharField(max_length=255, verbose_name="اسم المسار")
    origin = models.CharField(max_length=255, verbose_name="موقع الانطلاق")
    destination = models.CharField(max_length=255, verbose_name="الوجهة")
    distance_km = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="المسافة (كم)"
    )

    class Meta:
        db_table = "transport_routes"
        verbose_name = "مسار"
        verbose_name_plural = "المسارات"
        ordering = ["name"]

    def __str__(self):
        return self.name
