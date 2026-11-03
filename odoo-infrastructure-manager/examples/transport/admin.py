from django.contrib import admin

from .models import (
    Shipment,
    Good,
    Trip,
    Customer,
    Vehicle,
    Driver,
    Route,
    Payment,
    Expense,
)


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ("code", "customer", "status", "created_at", "is_active")
    list_filter = ("status", "is_active", "created_at")
    search_fields = ("code", "customer__name")
    ordering = ("-created_at",)


@admin.register(Good)
class GoodAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("code", "vehicle", "driver", "status", "created_at")
    list_filter = ("status", "is_active", "created_at")
    search_fields = ("code", "vehicle__plate", "driver__name")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "phone", "is_active")
    search_fields = ("name", "code", "phone")


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("plate", "code", "capacity_weight", "capacity_volume", "is_active")
    list_filter = ("is_active",)
    search_fields = ("plate", "code")


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "phone", "license_number", "is_active")
    search_fields = ("name", "code", "phone", "license_number")


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "origin", "destination", "is_active")
    search_fields = ("name", "code", "origin", "destination")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("code", "shipment", "amount", "payment_date", "is_active")
    list_filter = ("is_active", "payment_date")
    search_fields = ("code", "shipment__code")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("code", "trip", "amount", "expense_date", "is_active")
    list_filter = ("is_active", "expense_date")
    search_fields = ("code", "trip__code")
