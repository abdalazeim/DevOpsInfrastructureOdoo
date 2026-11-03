"""Public capabilities document for API clients (web / Android)."""

from django.conf import settings
from django.http import JsonResponse

from apps.core.utils.http import api_response
from apps.core.services.sync_service import sync_collections


def api_capabilities(request):
    modules = []
    for app in settings.INSTALLED_APPS:
        if app.startswith("apps.modules.") or app.startswith("examples."):
            modules.append(app.rsplit(".", 1)[-1])
    payload = {
        "api_version": "v1",
        "envelope": {"success": True, "message": "", "data": {}, "errors": None},
        "auth": {
            "session": "/api/v1/auth/login",
            "jwt_obtain": "/api/v1/auth/token/",
            "jwt_refresh": "/api/v1/auth/token/refresh/",
            "me": "/api/v1/auth/me",
            "logout": "/api/v1/auth/logout",
        },
        "pagination": {
            "page_param": "page",
            "page_size_param": "page_size",
            "default_page_size": 20,
            "max_page_size": 100,
            "list_shape": "data.items + data.meta",
        },
        "sync": {
            "url": "/api/v1/sync/",
            "push_method": "POST",
            "pull_method": "GET",
            "operation_id": "client-generated UUID; duplicate results are replayed for the same user",
            "collections": sorted(sync_collections()),
            "pull_query": ["since", "models"],
            "batch_limit": 100,
        },
        "modules": modules,
        "sample_module": "example",
    }
    if request.GET.get("raw") == "1":
        return JsonResponse(payload)
    return api_response(payload, message="capabilities")
