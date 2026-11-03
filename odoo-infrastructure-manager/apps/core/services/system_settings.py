"""Generic access to :class:`~apps.core.models.settings.SystemSetting`.

Settings are read heavily from templates/context processors, so lookups are
memoized per-process and invalidated on any write through this module.
"""

from django.core.cache import cache

from apps.core.models import SystemSetting

_CACHE_KEY = "system_settings:all"
_CACHE_TTL = 60 * 5  # 5 minutes


def get_all_settings():
    data = cache.get(_CACHE_KEY)
    if data is None:
        data = {
            s.key: s.value
            for s in SystemSetting.objects.filter(is_active=True).only(
                "key", "value"
            )
        }
        cache.set(_CACHE_KEY, data, _CACHE_TTL)
    return data


def get_setting(key, default=""):
    return get_all_settings().get(key, default)


def set_setting(key, value, *, description="", category="general"):
    """Create/update a setting and invalidate the memoized snapshot."""
    SystemSetting.objects.update_or_create(
        key=key,
        defaults={
            "value": str(value),
            "description": description,
            "category": category,
            "is_active": True,
        },
    )
    _invalidate()


def _invalidate():
    cache.delete(_CACHE_KEY)
