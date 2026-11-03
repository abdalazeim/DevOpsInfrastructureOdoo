"""Shared domain-agnostic constants for the template.

Modules should import from here instead of hard-coding strings scattered
across the codebase. Keep this file free of any business domain names.
"""

from django.db import models


class PermissionCode:
    """Central permission codes used by api_permission_required."""

    DASHBOARD_VIEW = "dashboard_view"
    SETTINGS_MANAGE = "settings_manage"
    USERS_MANAGE = "users_manage"
    ROLES_MANAGE = "roles_manage"
    GROUPS_MANAGE = "groups_manage"
    AUDIT_VIEW = "audit_view"
    BACKUP_MANAGE = "backup_manage"


class DefaultPageSize:
    LIST = 20
    MAX = 100


class AuditAction(models.TextChoices):
    CREATE = "create", "إنشاء"
    UPDATE = "update", "تحديث"
    DELETE = "delete", "حذف"
    LOGIN = "login", "دخول"
    LOGOUT = "logout", "خروج"
    APPROVE = "approve", "اعتماد"
    REJECT = "reject", "رفض"
    OTHER = "other", "أخرى"


class SortDirection:
    ASC = "asc"
    DESC = "desc"


class BoolValue:
    TRUE = "true"
    FALSE = "false"
