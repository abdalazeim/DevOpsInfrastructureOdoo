from django.urls import path

from . import views

app_name = "example"

urlpatterns = [
    path("items/", views.list_items, name="item-list"),
    path("items/create/", views.create_item, name="item-create"),
    path("items/<int:item_id>/", views.get_item, name="item-detail"),
    path("items/<int:item_id>/update/", views.update_item, name="item-update"),
    path("items/<int:item_id>/delete/", views.delete_item, name="item-delete"),
]
