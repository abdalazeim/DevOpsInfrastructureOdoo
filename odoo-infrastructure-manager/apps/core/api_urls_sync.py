"""Sync API routes for offline-first mobile (Android) clients.

Endpoint:
- POST /api/v1/sync/ - Push a batch of client mutations
- GET /api/v1/sync/?since=<timestamp> - Pull registered collections
"""

from django.urls import path

from .views import views_sync

urlpatterns = [
    path("", views_sync.sync_endpoint, name="sync"),
]
