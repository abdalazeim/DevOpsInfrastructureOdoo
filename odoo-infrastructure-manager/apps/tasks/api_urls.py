from django.urls import path

from apps.tasks import api_views

app_name = "tasks"

urlpatterns = [
    path("", api_views.task_list, name="list"),
    path("<uuid:task_id>/", api_views.task_detail, name="detail"),
    path("<uuid:task_id>/cancel/", api_views.cancel_task, name="cancel"),
    path("<uuid:task_id>/retry/", api_views.retry_task, name="retry"),
]
