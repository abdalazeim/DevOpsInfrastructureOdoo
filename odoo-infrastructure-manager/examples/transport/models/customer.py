"""Customer model for the transport module."""

from django.db import models

from apps.core.models import BaseModel


class Customer(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="الكود")
    name = models.CharField(max_length=255, verbose_name="الاسم")
    phone = models.CharField(max_length=20, blank=True, default="", verbose_name="الهاتف")
    email = models.EmailField(blank=True, default="", verbose_name="البريد الإلكتروني")
    address = models.TextField(blank=True, default="", verbose_name="العنوان")

    class Meta:
        db_table = "transport_customers"
        verbose_name = "عميل"
        verbose_name_plural = "العملاء"
        ordering = ["name"]

    def __str__(self):
        return self.name
