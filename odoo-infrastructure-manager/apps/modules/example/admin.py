from django.contrib import admin

from .models import ExampleItem


@admin.register(ExampleItem)
class ExampleItemAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "quantity", "sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    ordering = ("sort_order", "name")
