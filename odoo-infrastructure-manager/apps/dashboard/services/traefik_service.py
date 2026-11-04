import json
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.conf import settings


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


class TraefikReadOnlyService:
    ENDPOINTS = {
        "overview": "/api/overview",
        "routers": "/api/http/routers",
        "services": "/api/http/services",
        "middlewares": "/api/http/middlewares",
    }

    @classmethod
    def inspect(cls):
        base = settings.TRAEFIK_API_URL
        if not base:
            return {"available": False, "reason": "Traefik API is not configured.", "overview": None,
                    "routers": [], "services": [], "middlewares": []}
        parts = urlsplit(base)
        if (not parts.hostname or parts.username or parts.password or parts.query or parts.fragment
                or (parts.scheme != "https" and parts.hostname not in {"localhost", "127.0.0.1", "::1"})):
            return {"available": False, "reason": "Traefik API must use HTTPS, with no URL credentials or query parameters.",
                    "overview": None, "routers": [], "services": [], "middlewares": []}

        def fetch(key):
            request = Request(base + cls.ENDPOINTS[key], headers={"Accept": "application/json"})
            if settings.TRAEFIK_API_TOKEN:
                request.add_header("Authorization", f"Bearer {settings.TRAEFIK_API_TOKEN}")
            try:
                with build_opener(_NoRedirect).open(request, timeout=5) as response:
                    value = json.loads(response.read(500_000).decode("utf-8"))
                if key == "overview":
                    return key, value if isinstance(value, dict) else None
                return key, value if isinstance(value, list) else []
            except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError):
                return key, None if key == "overview" else []

        with ThreadPoolExecutor(max_workers=4) as executor:
            data = dict(executor.map(fetch, cls.ENDPOINTS))
        overview = data.get("overview")
        lists = {key: data.get(key) or [] for key in ("routers", "services", "middlewares")}
        available = overview is not None or any(lists.values())
        return {"available": available,
                "reason": "" if available else "Traefik API did not return data; verify API access and token.",
                "overview": overview, **lists}
