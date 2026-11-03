"""Unified permission resolution for users, roles, groups and API decorators."""

from ..models import UserProfile


def get_effective_permissions(user):
    """Return the resolved permission codes for a user (``["*"]`` for admins)."""
    if user.is_superuser:
        return ["*"]

    try:
        profile = user.profile
        if profile.permissions:
            return profile.permissions
        if profile.system_role:
            return list(profile.system_role.permissions)
    except UserProfile.DoesNotExist:
        pass

    return []


def has_permission(user, *perm_codes):
    """True if the user holds any of the given permission codes (or is admin)."""
    if user.is_superuser:
        return True
    perms = get_effective_permissions(user)
    if "*" in perms:
        return True
    return any(p in perms for p in perm_codes)
