from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login_page, name="login"),
    path("example/", views.example_page, name="example_page"),
    # Health checks
    path("health/", views.health_check, name="health_check"),
    path("health/db/", views.health_db, name="health_db"),
]
