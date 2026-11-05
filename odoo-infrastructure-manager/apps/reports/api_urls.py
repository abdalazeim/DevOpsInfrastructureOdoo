from django.urls import path

from apps.reports import api_views

app_name = "reports"

urlpatterns = [
    path("", api_views.catalog, name="catalog"),
    path("<slug:report_slug>/", api_views.preview, name="preview"),
    path("<slug:report_slug>/export/", api_views.export, name="export"),
]
