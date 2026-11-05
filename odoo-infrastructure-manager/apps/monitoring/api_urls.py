from django.urls import path

from apps.monitoring import api_views

app_name = "monitoring"

urlpatterns = [
    path("targets/", api_views.targets, name="targets"),
    path("samples/", api_views.samples, name="samples"),
    path("collections/", api_views.collections, name="collections"),
    path("rules/", api_views.rules, name="rules"),
    path("rules/<int:rule_id>/", api_views.rule_detail, name="rule-detail"),
    path("alerts/", api_views.alerts, name="alerts"),
    path("alerts/<int:event_id>/acknowledge/", api_views.acknowledge_alert, name="acknowledge"),
]
