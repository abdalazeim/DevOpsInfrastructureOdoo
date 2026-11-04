"""Validation for permission grants accepted from account management APIs."""

from .catalog import get_all_permissions
from ..services.permission_service import get_effective_permissions


def permission_codes_from_payload(value):
    """Return normalized submitted codes or a field error string."""
    if not isinstance(value, list):
        return None, "permissions must be a list of permission codes."
    if any(not isinstance(code, str) or not code.strip() for code in value):
        return None, "Each permission must be a non-empty string."

    known = {item["code"] for item in get_all_permissions() if item.get("code")}
    # During the code migration, allow the historic underscore representation
    # of catalog entries that are being moved to resource.action naming.
    known.update(_legacy_alias(code) for code in tuple(known))
    normalized = list(dict.fromkeys(code.strip() for code in value))
    unknown = sorted(set(normalized) - known)
    if unknown:
        return None, f"Unknown permission code(s): {', '.join(unknown)}"
    return normalized, None


def actor_can_grant(actor, codes):
    """Prevent managers from delegating permissions they do not themselves hold."""
    if not getattr(actor, "is_authenticated", False):
        return False
    if getattr(actor, "is_superuser", False):
        return True
    grants = set(get_effective_permissions(actor))
    if "*" in grants:
        return True
    grant_aliases = grants | {_legacy_alias(code) for code in grants}
    return all(code in grant_aliases or _legacy_alias(code) in grant_aliases for code in codes)


def _legacy_alias(code):
    if "." in code:
        resource, action = code.rsplit(".", 1)
        return f"{resource}_{action}"
    if "_" in code:
        resource, action = code.rsplit("_", 1)
        return f"{resource}.{action}"
    return code
