"""Unified permission resolution for users, roles, groups and API decorators."""

from ..models import UserProfile


def get_effective_permissions(user):
    """Return all active grants; a disabled identity never receives permissions."""
    if not is_identity_active(user):
        return []
    if user.is_superuser:
        return ["*"]

    permissions = set()
    try:
        profile = user.profile
        permissions.update(_valid_codes(profile.permissions))
        if profile.system_role:
            permissions.update(_valid_codes(profile.system_role.permissions))
        if profile.group_id:
            permissions.update(_valid_codes(profile.group.permissions))
    except UserProfile.DoesNotExist:
        pass

    # Django auth groups remain supported for deployments that manage access
    # through the standard auth tables. Their permission codenames are grants.
    if getattr(user, "pk", None):
        for code in user.groups.values_list("permissions__codename", flat=True):
            if code:
                permissions.add(code)
    return sorted(permissions)


def has_permission(user, *perm_codes):
    """True if any requested code is granted, with legacy-code compatibility."""
    perms = get_effective_permissions(user)
    if "*" in perms:
        return True
    expanded = set(perms)
    expanded.update(_legacy_alias(code) for code in perms)
    requested = set(perm_codes)
    requested.update(_legacy_alias(code) for code in perm_codes)
    return bool(expanded & requested)


def is_identity_active(user):
    """Check Django account state and the platform-specific user profile state."""
    if not getattr(user, "is_authenticated", False):
        return False
    if not getattr(user, "is_active", True) or not getattr(user, "is_active_user", True):
        return False
    try:
        return bool(user.profile.is_active)
    except UserProfile.DoesNotExist:
        return True


def _valid_codes(value):
    if not isinstance(value, (list, tuple, set)):
        return set()
    return {code.strip() for code in value if isinstance(code, str) and code.strip()}


def _legacy_alias(code):
    """Bridge legacy ``resource_action`` grants and new ``resource.action`` codes."""
    if not isinstance(code, str):
        return code
    if "." in code:
        resource, action = code.rsplit(".", 1)
        return f"{resource}_{action}"
    if "_" in code:
        resource, action = code.rsplit("_", 1)
        return f"{resource}.{action}"
    return code
