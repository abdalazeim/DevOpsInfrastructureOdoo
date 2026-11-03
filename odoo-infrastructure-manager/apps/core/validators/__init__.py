"""Common domain-agnostic validators.

Raise :class:`django.core.exceptions.ValidationError` (or return cleaned
values) so they stay usable by both forms/serializers and services.
"""

import re

from django.core.exceptions import ValidationError

_RE_CODE = re.compile(r"^[A-Za-z0-9_\-]{2,100}$")
_RE_NAME = re.compile(r"^[\w\s\u0600-\u06FF\-\'\.]{2,200}$")


def validate_code(value):
    """Codes: latin letters, digits, underscore, dash (2-100 chars)."""
    value = (value or "").strip()
    if not _RE_CODE.match(value):
        raise ValidationError("الكود يجب أن يكون 2-100 حرفًا لاتينيًا أو رقمًا أو _ أو -")
    return value


def validate_name(value):
    """Human names: letters (Arabic/Latin), digits, spaces, basic punctuation."""
    value = (value or "").strip()
    if not _RE_NAME.match(value):
        raise ValidationError("الاسم يجب أن يكون 2-200 حرفًا")
    return value


def validate_required_text(value, label="الحقل", min_length=1):
    value = (value or "").strip()
    if len(value) < min_length:
        raise ValidationError(f"{label} مطلوب")
    return value


def validate_choice(value, choices, label="القيمة"):
    if value not in dict(choices):
        raise ValidationError(f"{label} غير صالحة")
    return value


def validate_positive_number(value, field_name="القيمة", allow_zero=False):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} يجب أن يكون رقمًا")
    if allow_zero:
        if number < 0:
            raise ValidationError(f"{field_name} يجب أن يكون 0 أو أكبر")
    elif number <= 0:
        raise ValidationError(f"{field_name} يجب أن يكون أكبر من 0")
    return number


def validate_phone(value):
    """Phone numbers: digits, +, -, spaces (8-20 chars)."""
    value = (value or "").strip()
    cleaned = re.sub(r"[^0-9+]", "", value)
    if not 8 <= len(cleaned) <= 20:
        raise ValidationError("رقم الهاتف غير صالح")
    return cleaned


def validate_email(value):
    from django.core.validators import validate_email as django_validate_email

    value = (value or "").strip()
    try:
        django_validate_email(value)
    except ValidationError:
        raise ValidationError("البريد الإلكتروني غير صالح")
    return value
