from django.urls import path

from . import views

app_name = "dashboard"
urlpatterns = [
    path("", views.index, name="index"),
    path("settings/", views.global_settings, name="global_settings"),
    path("containers/", views.containers, name="containers"),
    path("inventory/", views.inventory, name="inventory"),
    path("inventory/<str:item_type>/create/", views.create_inventory_item, name="create_inventory_item"),
    path("inventory/hosts/<int:host_id>/test-connection/", views.test_server_connection, name="test_server_connection"),
    path("security/credentials/create/", views.create_credential, name="create_credential"),
    path("security/credentials/<int:credential_id>/toggle/", views.toggle_credential, name="toggle_credential"),
    path("inventory/<str:item_type>/<int:item_id>/update/", views.update_inventory_item, name="update_inventory_item"),
    path("automation/templates/", views.automation_templates, name="automation_templates"),
    path("automation/templates/create/", views.create_automation_template, name="create_automation_template"),
    path("automation/templates/<int:template_id>/toggle/", views.toggle_automation_template, name="toggle_automation_template"),
    path("docker/<str:resource_type>/", views.docker_resources, name="docker_resources"),
    path("containers/<str:container_name>/logs/", views.container_logs, name="container_logs"),
    path("services/odoo/", views.odoo_services, name="odoo_services"),
    path("services/django/", views.django_projects, name="django_projects"),
    path("databases/", views.database_services, name="database_services"),
    path("backups/", views.backups, name="backups"),
    path("backups/policies/save/", views.save_backup_policy, name="save_backup_policy"),
    path("alerts/", views.alerts, name="alerts"),
    path("alerts/rules/save/", views.save_alert_rule, name="save_alert_rule"),
    path("audit/", views.audit_log, name="audit"),
    path("alerts/<int:event_id>/acknowledge/", views.acknowledge_alert, name="acknowledge_alert"),
    path("traefik/", views.traefik, name="traefik"),
    path("api/overview/", views.overview_api, name="overview_api"),
    path("automation/ping/", views.semaphore_ping, name="semaphore_ping"),
    path("automation/templates/<int:template_id>/run/", views.run_approved_template, name="run_template"),
    path("automation/runs/<int:run_id>/refresh/", views.refresh_run, name="refresh_run"),
    path("automation/runs/<int:run_id>/", views.run_detail, name="run_detail"),
]
