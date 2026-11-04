"""Validation for structured adapter arguments; raw command strings are not accepted."""

import json


class InvalidOperationParameters(ValueError):
    pass


def validate_structured_parameters(parameters, *, allowed_keys=(), max_payload_bytes=4096):
    if not isinstance(parameters, dict):
        raise InvalidOperationParameters("Operation parameters must be a JSON object.")
    unexpected = set(parameters) - set(allowed_keys)
    if unexpected:
        raise InvalidOperationParameters("Unsupported operation parameter(s): " + ", ".join(sorted(unexpected)))
    try:
        encoded = json.dumps(parameters, ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InvalidOperationParameters("Operation parameters must contain JSON-safe values.") from exc
    if len(encoded) > max_payload_bytes:
        raise InvalidOperationParameters("Operation parameters exceed the allowed size.")
    if _contains_nul(parameters):
        raise InvalidOperationParameters("NUL characters are not allowed in operation parameters.")
    return parameters


def _contains_nul(value):
    if isinstance(value, str):
        return "\x00" in value
    if isinstance(value, dict):
        return any(_contains_nul(key) or _contains_nul(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_nul(item) for item in value)
    return False
