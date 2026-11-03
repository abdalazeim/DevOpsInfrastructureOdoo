from django.urls import path

from . import views

urlpatterns = [
    path("capabilities/", views.api_capabilities, name="api_capabilities"),
    # Dashboard
    path("dashboard/stats", views.dashboard_stats, name="dashboard_stats"),
    # Audit logs
    path("audit-logs", views.list_audit_logs, name="list_audit_logs"),
    # Backup
    path("backup/create", views.create_backup, name="create_backup"),
    path("backup/list", views.list_backups, name="list_backups"),
    path(
        "backup/download/<str:filename>",
        views.download_backup,
        name="download_backup",
    ),
    path("backup/restore", views.restore_backup, name="restore_backup"),
    path("backup/<str:filename>", views.delete_backup, name="delete_backup"),
    # Settings
    path("settings/lookups", views.list_lookups, name="list_lookups"),
    path(
        "settings/lookups/<int:lookup_id>",
        views.update_lookup,
        name="update_lookup",
    ),
    path(
        "settings/system", views.list_system_settings, name="list_system_settings"
    ),
    path(
        "settings/system/<int:setting_id>",
        views.update_system_setting,
        name="update_system_setting",
    ),
    path(
        "settings/seed", views.seed_default_settings, name="seed_default_settings"
    ),
    path(
        "settings/bulk-save",
        views.bulk_save_settings,
        name="bulk_save_settings",
    ),
    path(
        "settings/all", views.list_all_settings, name="list_all_settings"
    ),
]
