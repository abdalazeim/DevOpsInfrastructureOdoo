from django.urls import path

from apps.containers import api_views

app_name = "docker"

urlpatterns = [
    path("engines/", api_views.docker_engines, name="engines"),
    path("engines/<int:engine_id>/", api_views.docker_engine_detail, name="engine-detail"),
    path("engines/<int:engine_id>/discover/", api_views.discover_docker_engine, name="discover"),
    path(
        "engines/<int:engine_id>/containers/<str:container_id>/<str:action>/",
        api_views.docker_container_action,
        name="container-action",
    ),
]
