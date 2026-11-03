"""Shipment model for the transport module."""

from django.db import models

from apps.core.models import BaseModel


class Shipment(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "مسودة"
        PENDING = "pending", "قيد الانتظار"
        LOADED = "loaded", "محملة"
        IN_TRANSIT = "in_transit", "في الطريق"
        DELIVERED = "delivered", "مسلمة"
        EXCEPTION = "exception", "استثناء"
        CANCELLED = "cancelled", "ملغاة"

    code = models.CharField(max_length=50, unique=True, verbose_name="الكود")
    customer = models.ForeignKey(
        "Customer", on_delete=models.PROTECT, verbose_name="العميل"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT, verbose_name="الحالة"
    )
    origin = models.CharField(max_length=255, verbose_name="موقع الانطلاق")
    destination = models.CharField(max_length=255, verbose_name="الوجهة")
    weight = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="الوزن"
    )
    volume = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="الحجم"
    )
    notes = models.TextField(blank=True, default="", verbose_name="ملاحظات")
    is_draft = models.BooleanField(default=False, verbose_name="مسودة")

    class Meta:
        db_table = "transport_shipments"
        verbose_name = "شحنة"
        verbose_name_plural = "الشحنات"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["status"]),
            models.Index(fields=["customer"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.customer}"


class ShipmentException(models.Model):
    shipment = models.ForeignKey(
        Shipment, on_delete=models.CASCADE, related_name="exceptions"
    )
    reason = models.TextField(verbose_name="سبب الاستثناء")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "transport_shipment_exceptions"
        verbose_name = "استثناء شحنة"
        verbose_name_plural = "استثناءات الشحنات"


class ShipmentPOD(models.Model):
    shipment = models.OneToOneField(
        Shipment, on_delete=models.CASCADE, related_name="pod"
    )
    signature = models.TextField(blank=True, default="", verbose_name="التوقيع")
    photo = models.TextField(blank=True, default="", verbose_name="صورة التسليم")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "transport_shipment_pod"
        verbose_name = "إثبات تسليم (POD)"
        verbose_name_plural = "إثباتات التسليم"
