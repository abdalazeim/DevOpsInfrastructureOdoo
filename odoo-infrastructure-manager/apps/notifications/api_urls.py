from django.urls import path

from apps.notifications import api_views

app_name = "notifications"

urlpatterns = [
    path("", api_views.notifications, name="list"),
    path("read-all/", api_views.mark_all_notifications_read, name="read-all"),
    path("<int:notification_id>/read/", api_views.mark_notification_read, name="read"),
    path("preferences/", api_views.preferences, name="preferences"),
]
