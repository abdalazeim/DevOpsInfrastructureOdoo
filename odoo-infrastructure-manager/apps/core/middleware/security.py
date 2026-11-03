import json
import re

from django.conf import settings


class SecurityHeadersMiddleware:
    """Additional security headers not covered by Django's SecurityMiddleware."""

    def __init__(self, get_response):
        self.get_response = get_response

    SECURITY_HEADERS = {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "same-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }

    def __call__(self, request):
        response = self.get_response(request)
        if not getattr(settings, "DEBUG", False):
            for header, value in self.SECURITY_HEADERS.items():
                response.setdefault(header, value)
        return response


class InputSanitizationMiddleware:
    """Sanitize JSON request body inputs to prevent XSS and injection."""

    # Regex pattern to detect HTML/script injection
    XSS_PATTERN = re.compile(
        r"<[^>]*script|javascript:|on\w+\s*=|alert\(|prompt\(|confirm\(", re.IGNORECASE
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def _sanitize_value(self, value):
        if isinstance(value, str):
            stripped = value.strip()
            if self.XSS_PATTERN.search(stripped):
                return stripped.replace("<", "&lt;").replace(">", "&gt;")
            return stripped
        if isinstance(value, dict):
            return {k: self._sanitize_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._sanitize_value(v) for v in value]
        return value

    def __call__(self, request):
        content_type = request.META.get("CONTENT_TYPE", "")
        if (
            request.method in ("POST", "PUT", "PATCH")
            and "application/json" in content_type
        ):
            try:
                body = json.loads(request.body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return self.get_response(request)
            sanitized = self._sanitize_value(body)
            if sanitized != body:
                request._body = json.dumps(sanitized).encode("utf-8")
        return self.get_response(request)
