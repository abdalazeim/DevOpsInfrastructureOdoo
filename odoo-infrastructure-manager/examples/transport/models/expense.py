"""Expense model for the transport module."""

from django.db import models

from apps.core.models import BaseModel


class Expense(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name="الكود")
    trip = models.ForeignKey(
        "Trip", on_delete=models.PROTECT, verbose_name="الرحلة"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="المبلغ")
    expense_date = models.DateTimeField(verbose_name="تاريخ المصروف")
    category = models.CharField(max_length=100, blank=True, default="", verbose_name="الفئة")
    description = models.TextField(blank=True, default="", verbose_name="الوصف")

    class Meta:
        db_table = "transport_expenses"
        verbose_name = "مصروف"
        verbose_name_plural = "المصروفات"
        ordering = ["-expense_date"]

    def __str__(self):
        return f"{self.code} - {self.amount}"
