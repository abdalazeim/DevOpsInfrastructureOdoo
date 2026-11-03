"""Permission catalog: single source of truth for permission codes.

Core/Accounts expose generic permissions. Business modules register their own
permissions at app-ready time via :func:`register_permissions`, keeping
Accounts free of any business domain.
"""

# ─── Generic (Core/Accounts) permissions ──────────────────────────────
_CORE_PERMISSIONS = [
    # قوائم النظام (nav)
    {"code": "nav_dashboard", "label": "لوحة التحكم", "group": "nav"},
    {"code": "nav_reports", "label": "التقارير", "group": "nav"},
    {"code": "nav_settings", "label": "الإعدادات", "group": "nav"},
    {"code": "nav_backup", "label": "النسخ الاحتياطية", "group": "nav"},
    {"code": "nav_users", "label": "إدارة المستخدمين", "group": "nav"},
    # الأزرار والإجراءات (actions)
    {"code": "users_manage", "label": "إدارة المستخدمين", "group": "actions"},
    {"code": "settings_manage", "label": "إدارة الإعدادات العامة", "group": "actions"},
    {"code": "backup_manage", "label": "إدارة النسخ الاحتياطية", "group": "actions"},
    {"code": "audit_view", "label": "عرض سجل التدقيق", "group": "actions"},
    # New granular contracts; legacy app codes above remain valid aliases.
    {"code": "server.view", "label": "View servers", "group": "servers"},
    {"code": "server.create", "label": "Register servers", "group": "servers"},
    {"code": "server.update", "label": "Edit server records", "group": "servers"},
    {"code": "server.delete", "label": "Remove servers", "group": "servers"},
    {"code": "server.connect", "label": "Test server connections", "group": "servers"},
    {"code": "server.restart", "label": "Restart servers", "group": "servers"},
    {"code": "server.shutdown", "label": "Shut down servers", "group": "servers"},
    {"code": "docker.container.view", "label": "View containers", "group": "containers"},
    {"code": "docker.container.create", "label": "Create containers", "group": "containers"},
    {"code": "docker.container.start", "label": "Start containers", "group": "containers"},
    {"code": "docker.container.stop", "label": "Stop containers", "group": "containers"},
    {"code": "docker.container.restart", "label": "Restart containers", "group": "containers"},
    {"code": "docker.container.delete", "label": "Remove containers", "group": "containers"},
    {"code": "automation.playbook.view", "label": "View playbooks", "group": "automation"},
    {"code": "automation.playbook.create", "label": "Manage playbooks", "group": "automation"},
    {"code": "automation.playbook.execute", "label": "Execute playbooks", "group": "automation"},
    {"code": "monitoring.view", "label": "View monitoring data", "group": "monitoring"},
    {"code": "monitoring.alert.manage", "label": "Manage alert rules", "group": "monitoring"},
    {"code": "monitoring.alert.acknowledge", "label": "Acknowledge alerts", "group": "monitoring"},
    {"code": "backup.view", "label": "View backups", "group": "backup"},
    {"code": "backup.create", "label": "Create backups", "group": "backup"},
    {"code": "backup.restore", "label": "Restore backups", "group": "backup"},
    {"code": "database.view", "label": "View database instances", "group": "databases"},
    {"code": "database.manage", "label": "Manage database instances", "group": "databases"},
    {"code": "security.credentials.manage", "label": "Manage credential references", "group": "security"},
    {"code": "task.view", "label": "View execution tasks", "group": "tasks"},
    {"code": "task.cancel", "label": "Cancel eligible tasks", "group": "tasks"},
    {"code": "task.retry", "label": "Retry eligible tasks", "group": "tasks"},
    {"code": "reports.view", "label": "View reports", "group": "reports"},
    {"code": "reports.export", "label": "Export reports", "group": "reports"},
    {"code": "settings.view", "label": "View global settings", "group": "settings"},
    {"code": "settings.manage", "label": "Manage global settings", "group": "settings"},
]

_CORE_GROUPS = [
    {"key": "nav", "label": "قوائم النظام", "icon": "fa-list"},
    {"key": "actions", "label": "الأزرار والإجراءات", "icon": "fa-hand-pointer"},
    {"key": "servers", "label": "Servers", "icon": "fa-server"},
    {"key": "containers", "label": "Containers", "icon": "fa-box"},
    {"key": "automation", "label": "Automation", "icon": "fa-list-check"},
    {"key": "monitoring", "label": "Monitoring", "icon": "fa-chart-line"},
    {"key": "backup", "label": "Backup", "icon": "fa-box-archive"},
    {"key": "databases", "label": "Databases", "icon": "fa-database"},
    {"key": "security", "label": "Security", "icon": "fa-shield-halved"},
    {"key": "tasks", "label": "Tasks", "icon": "fa-list-check"},
    {"key": "reports", "label": "Reports", "icon": "fa-file-lines"},
    {"key": "settings", "label": "Global settings", "icon": "fa-sliders"},
]

# ─── Module-registered permissions ────────────────────────────────────
_MODULE_PERMISSIONS = []
_MODULE_GROUPS = []


def register_permissions(permissions, groups=None):
    """Register permission codes from a business module (call in apps.ready)."""
    for perm in permissions:
        code = perm.get("code")
        if code and not any(p.get("code") == code for p in get_all_permissions()):
            _MODULE_PERMISSIONS.append(perm)
    for group in groups or []:
        key = group.get("key")
        if key and not any(g.get("key") == key for g in get_all_groups()):
            _MODULE_GROUPS.append(group)


def get_all_permissions():
    return _CORE_PERMISSIONS + _MODULE_PERMISSIONS


def get_all_groups():
    return _CORE_GROUPS + _MODULE_GROUPS


# ─── Public aliases (backwards compatible) ────────────────────────────
MASTER_PERMISSIONS = _CORE_PERMISSIONS
PERMISSION_GROUPS = _CORE_GROUPS
