import re
import time

from django.conf import settings
from django.http import JsonResponse


class RateLimitMiddleware:
    """Simple in-memory rate limiter (no Redis dependency)."""

    def __init__(self, get_response):
        self.get_response = get_response
        self._store = {}

    def _get_client_ip(self, request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "127.0.0.1")

    def _check_rate(self, key, limit_spec, cost=1):
        match = re.match(r"^(\d+)/([smhd])$", limit_spec)
        if not match:
            return True
        max_requests = int(match.group(1))
        unit = match.group(2)
        window_map = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        window = window_map.get(unit, 60)

        now = time.time()
        entry = self._store.get(key)
        if not entry:
            self._store[key] = {"tokens": [(now, cost)]}
            return True

        cutoff = now - window
        entry["tokens"] = [(t, c) for (t, c) in entry["tokens"] if t > cutoff]
        total = sum(c for _, c in entry["tokens"])
        if total + cost > max_requests:
            return False
        entry["tokens"].append((now, cost))
        return True

    def __call__(self, request):
        # Clean old entries periodically
        if len(self._store) > 10000:
            cutoff = time.time() - 3600
            self._store = {
                k: v for k, v in self._store.items() if v["tokens"][-1][0] > cutoff
            }

        path = request.path_info
        client_ip = self._get_client_ip(request)

        # Rate limit login endpoint
        if path == "/api/auth/login" and request.method == "POST":
            limit = getattr(settings, "RATE_LIMIT_LOGIN", "10/m")
            if not self._check_rate(f"login:{client_ip}", limit):
                return JsonResponse(
                    {
                        "success": False,
                        "error": "محاولات كثيرة جداً. الرجاء الانتظار قبل المحاولة مرة أخرى.",
                    },
                    status=429,
                )

        # Rate limit API endpoints
        elif path.startswith("/api/") and request.method in (
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        ):
            limit = getattr(settings, "RATE_LIMIT_API", "60/m")
            if not self._check_rate(f"api:{client_ip}", limit):
                return JsonResponse(
                    {"success": False, "error": "طلبات كثيرة جداً. الرجاء الانتظار."},
                    status=429,
                )

        response = self.get_response(request)
        return response
