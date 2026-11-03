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
]

_CORE_GROUPS = [
    {"key": "nav", "label": "قوائم النظام", "icon": "fa-list"},
    {"key": "actions", "label": "الأزرار والإجراءات", "icon": "fa-hand-pointer"},
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
