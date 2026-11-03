"""Single source of truth for input cleaning helpers."""
import json


def sanitize_str(val, max_length=500):
    if val is None:
        return ""
    return str(val).strip()[:max_length]


def sanitize_json(val):
    if val is None:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return []
    return []
