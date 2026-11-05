from django.urls import path

from . import api_views

app_name = "servers"

urlpatterns = [
    path("", api_views.server_list, name="list"),
    path("<int:host_id>/", api_views.server_detail, name="detail"),
    path("groups/", api_views.server_groups, name="groups"),
    path("tags/", api_views.server_tags, name="tags"),
    path("<int:host_id>/sync-history/", api_views.sync_history, name="sync-history"),
    path("<int:host_id>/test-connection/", api_views.test_connection, name="test-connection"),
    path("<int:host_id>/discover/", api_views.discover, name="discover"),
]
