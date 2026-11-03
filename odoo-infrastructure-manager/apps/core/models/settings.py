from django.db import models


class LookupCategory(models.Model):
    category = models.CharField(
        max_length=100,
        verbose_name="التصنيف",
        help_text="مفتاح التصنيف (عام، يمكن تعريفه حسب المشروع)",
    )
    name = models.CharField(max_length=255, verbose_name="الاسم")
    name_en = models.CharField(
        max_length=255, blank=True, default="", verbose_name="الاسم بالإنجليزية"
    )
    sort_order = models.IntegerField(default=0, verbose_name="ترتيب الفرز")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    extra_data = models.JSONField(
        default=dict, blank=True, verbose_name="بيانات إضافية"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "settings_lookups"
        verbose_name = "قيمة تصنيف"
        verbose_name_plural = "قيم التصنيفات"
        ordering = ["category", "sort_order", "name"]
        indexes = [
            models.Index(fields=["category", "name"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.category})"


class SystemSetting(models.Model):
    key = models.CharField(max_length=100, unique=True, verbose_name="المفتاح")
    value = models.TextField(blank=True, default="", verbose_name="القيمة")
    description = models.TextField(blank=True, default="", verbose_name="الوصف")
    category = models.CharField(
        max_length=30,
        default="general",
        verbose_name="التصنيف",
        help_text="مفتاح التصنيف (عام، يمكن تعريفه حسب المشروع)",
    )
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "settings_system"
        verbose_name = "إعداد النظام"
        verbose_name_plural = "إعدادات النظام"
        ordering = ["category", "key"]

    def __str__(self):
        return f"{self.key} = {self.value}"
