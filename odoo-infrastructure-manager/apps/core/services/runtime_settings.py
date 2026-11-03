"""Validated, non-secret runtime settings with environment override precedence."""

from django.conf import settings

from apps.core.services.system_settings import get_setting


RUNTIME_SETTING_SCHEMA = {
    "ssh_timeout_seconds": {
        "label": "SSH connection timeout (seconds)", "help": "Maximum time for one SSH handshake and fixed metadata probe.",
        "default": 8, "minimum": 1, "maximum": 60, "env": "INFRA_SSH_TIMEOUT_SECONDS", "category": "infrastructure",
    },
    "operation_timeout_seconds": {
        "label": "Infrastructure operation timeout (seconds)", "help": "Default execution limit for future queued infrastructure operations.",
        "default": 300, "minimum": 1, "maximum": 3600, "env": "INFRA_OPERATION_TIMEOUT_SECONDS", "category": "execution",
    },
    "monitoring_collection_interval_seconds": {
        "label": "Monitoring collection interval (seconds)", "help": "Minimum interval for future scheduled metric collection.",
        "default": 60, "minimum": 15, "maximum": 3600, "env": "MONITORING_COLLECTION_INTERVAL_SECONDS", "category": "monitoring",
    },
    "metrics_retention_days": {
        "label": "Metrics retention (days)", "help": "Maximum default retention for resource samples.",
        "default": 30, "minimum": 1, "maximum": 3650, "env": "METRICS_RETENTION_DAYS", "category": "monitoring",
    },
}


class RuntimeSettingError(ValueError):
    """Raised when a configured runtime setting is not valid for its schema."""


def environment_override(key):
    value = getattr(settings, "RUNTIME_SETTING_ENV_OVERRIDES", {}).get(key)
    return value if value not in (None, "") else None


def get_runtime_setting(key):
    spec = RUNTIME_SETTING_SCHEMA[key]
    value = environment_override(key)
    if value is None:
        value = get_setting(key, "")
    if value in (None, ""):
        return spec["default"]
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeSettingError(f"{key} must be an integer.") from exc
    if not spec["minimum"] <= parsed <= spec["maximum"]:
        raise RuntimeSettingError(f"{key} must be between {spec['minimum']} and {spec['maximum']}.")
    return parsed


def get_runtime_settings():
    return {key: get_runtime_setting(key) for key in RUNTIME_SETTING_SCHEMA}
