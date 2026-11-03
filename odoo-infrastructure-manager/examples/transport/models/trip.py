"""Trip model for the transport module."""

from django.db import models

from apps.core.models import BaseModel


class Trip(BaseModel):
    class Status(models.TextChoices):
        PLANNED = "planned", "مخطط لها"
        LOADING = "loading", "تحت التحميل"
        IN_PROGRESS = "in_progress", "جارية"
        COMPLETED = "completed", "مكتملة"
        CLOSED = "closed", "مغلقة"
        CANCELLED = "cancelled", "ملغاة"

    code = models.CharField(max_length=50, unique=True, verbose_name="الكود")
    vehicle = models.ForeignKey(
        "Vehicle", on_delete=models.PROTECT, verbose_name="المركبة"
    )
    driver = models.ForeignKey(
        "Driver", on_delete=models.PROTECT, verbose_name="السائق"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PLANNED, verbose_name="الحالة"
    )
    origin = models.CharField(max_length=255, verbose_name="موقع الانطلاق")
    destination = models.CharField(max_length=255, verbose_name="الوجهة")
    planned_date = models.DateTimeField(verbose_name="التاريخ المخطط")
    notes = models.TextField(blank=True, default="", verbose_name="ملاحظات")

    class Meta:
        db_table = "transport_trips"
        verbose_name = "رحلة"
        verbose_name_plural = "الرحلات"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["status"]),
            models.Index(fields=["vehicle"]),
            models.Index(fields=["driver"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.driver}"


class TripShipment(models.Model):
    trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="linked_shipments"
    )
    shipment = models.ForeignKey(
        "Shipment", on_delete=models.CASCADE, related_name="trips"
    )
    linked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "transport_trip_shipments"
        unique_together = ("trip", "shipment")
        verbose_name = "ربط رحلة بشحنة"
        verbose_name_plural = "ربط الرحلات بالشحنات"
