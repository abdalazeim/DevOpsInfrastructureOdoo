from django.contrib import admin
from django.utils import timezone

from .models import LookupCategory, SyncConflict, SyncOperation, SyncTombstone, SystemSetting


@admin.register(LookupCategory)
class LookupCategoryAdmin(admin.ModelAdmin):
    list_display = ("category", "name", "sort_order", "is_active")
    list_filter = ("category", "is_active")


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "category", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("key",)


@admin.register(SyncOperation)
class SyncOperationAdmin(admin.ModelAdmin):
    list_display = ("operation_id", "user", "kind", "status", "created_at")
    list_filter = ("status", "kind")
    search_fields = ("operation_id", "kind", "user__username")
    readonly_fields = ("operation_id", "user", "kind", "status", "result", "error", "created_at", "applied_at")


@admin.register(SyncTombstone)
class SyncTombstoneAdmin(admin.ModelAdmin):
    list_display = ("model_label", "object_pk", "scope_key", "deleted_at", "deleted_by")
    list_filter = ("model_label",)
    search_fields = ("model_label", "object_pk", "scope_key")
    readonly_fields = ("model_label", "object_pk", "scope_key", "deleted_at", "deleted_by")


@admin.register(SyncConflict)
class SyncConflictAdmin(admin.ModelAdmin):
    list_display = ("operation_id", "model_label", "object_pk", "status", "detected_at")
    list_filter = ("status", "model_label", "kind")
    search_fields = ("operation_id", "model_label", "object_pk", "message")
    readonly_fields = (
        "operation_id", "user", "kind", "model_label", "object_pk",
        "base_updated_at", "server_updated_at", "payload", "message", "detected_at",
        "resolved_by", "resolved_at",
    )

    def save_model(self, request, obj, form, change):
        if obj.status == SyncConflict.RESOLVED:
            obj.resolved_by = request.user
            obj.resolved_at = obj.resolved_at or timezone.now()
        else:
            obj.resolved_by = None
            obj.resolved_at = None
        super().save_model(request, obj, form, change)
