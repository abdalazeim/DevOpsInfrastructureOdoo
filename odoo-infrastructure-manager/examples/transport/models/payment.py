"""Payment model for the transport module."""

from django.db import models

from apps.core.models import BaseModel


class Payment(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="الكود")
    shipment = models.ForeignKey(
        "Shipment", on_delete=models.PROTECT, verbose_name="الشحنة"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="المبلغ")
    payment_date = models.DateTimeField(verbose_name="تاريخ الدفع")
    method = models.CharField(max_length=50, blank=True, default="", verbose_name="طريقة الدفع")

    class Meta:
        db_table = "transport_payments"
        verbose_name = "دفعة"
        verbose_name_plural = "المدفوعات"
        ordering = ["-payment_date"]

    def __str__(self):
        return f"{self.code} - {self.amount}"
