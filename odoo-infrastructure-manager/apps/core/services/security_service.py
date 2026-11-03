"""Security utilities for input validation, sanitization, and audit logging."""

import re

# HTML/JS injection detection pattern
XSS_PATTERN = re.compile(
    r"<[^>]*script|javascript:|vbscript:|data:text/html|"
    r"on\w+\s*=|alert\(|prompt\(|confirm\(|"
    r"document\.cookie|document\.location|window\.location|"
    r"eval\(|setTimeout\(|setInterval\(|"
    r"Function\(|new Function",
    re.IGNORECASE,
)


def sanitize_html(value, max_length=None):
    """Strip or escape HTML/JS injection attempts."""
    if not isinstance(value, str):
        return value
    if max_length:
        value = value[:max_length]
    if XSS_PATTERN.search(value):
        return value.replace("<", "&lt;").replace(">", "&gt;")
    return value.strip()


def validate_string(value, min_len=0, max_len=None, required=False, field_name=""):
    """Validate and sanitize a string value."""
    if value is None:
        if required:
            raise ValueError(f"{field_name} مطلوب")
        return ""
    s = str(value).strip()
    if required and not s:
        raise ValueError(f"{field_name} مطلوب")
    if min_len and len(s) < min_len:
        raise ValueError(f"{field_name} يجب أن يكون {min_len} أحرف على الأقل")
    if max_len:
        s = s[:max_len]
    return sanitize_html(s)


def validate_email(email):
    """Validate email format."""
    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if email and not re.match(pattern, email.strip()):
        raise ValueError("البريد الإلكتروني غير صالح")
    return email.strip() if email else ""


def validate_password_strength(password):
    """Check password meets minimum strength requirements."""
    if len(password) < 8:
        raise ValueError("كلمة المرور يجب أن تكون 8 أحرف على الأقل")
    if len(password) > 128:
        raise ValueError("كلمة المرور طويلة جداً")
    return password


def sanitize_json_body(body):
    """Sanitize all string values in a parsed JSON body."""
    if isinstance(body, dict):
        return {k: sanitize_json_body(v) for k, v in body.items()}
    if isinstance(body, list):
        return [sanitize_json_body(v) for v in body]
    if isinstance(body, str):
        return sanitize_html(body)
    return body
