"""Central API route table.

All API endpoints are registered here without the ``api/`` prefix and
mounted twice from ``config/urls.py``:

- ``/api/``    -> legacy/default version (keeps the existing frontend working)
- ``/api/v1/`` -> explicit versioned namespace

Business modules should register their URLs here when added to the project.
"""

from django.conf import settings
from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.api_urls")),
    path("", include("apps.accounts.urls")),
    path("modules/example/", include("apps.modules.example.urls")),
    # Sync endpoints (offline-first for Android/mobile)
    path("sync/", include("apps.core.api_urls_sync")),
]

if "examples.transport" in settings.INSTALLED_APPS:
    urlpatterns.append(
        path("modules/transport/", include("examples.transport.urls")),
    )
