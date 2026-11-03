from django.urls import path

from . import views

urlpatterns = [
    # Auth
    path("auth/login", views.auth_login, name="auth_login"),
    path("auth/logout", views.auth_logout, name="auth_logout"),
    path("auth/status", views.auth_status, name="auth_status"),
    path("auth/me", views.auth_me, name="auth_me"),
    # Users
    path("users", views.list_users, name="list_users"),
    path("users/<int:user_id>", views.edit_user, name="edit_user"),
    path("users/groups", views.list_groups, name="list_groups"),
    path("users/groups/<int:group_id>", views.edit_group, name="edit_group"),
    path("users/roles/seed", views.seed_default_roles, name="seed_default_roles"),
    path("users/roles", views.list_roles, name="list_roles"),
    path("users/roles/<int:role_id>", views.edit_role, name="edit_role"),
    path("users/permissions", views.list_permissions, name="list_permissions"),
]
