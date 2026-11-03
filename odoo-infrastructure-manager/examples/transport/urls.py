"""Transport module API URLs.

Mounted at /api/v1/modules/transport/ (and /api/modules/transport/ for legacy).
"""

from django.urls import path

from . import views

app_name = "transport"

urlpatterns = [
    # Meta / reference data
    path("meta/", views.transport_meta, name="transport-meta"),
    # Reference lists
    path("customers/", views.list_customers, name="customer-list"),
    path("vehicles/", views.list_vehicles, name="vehicle-list"),
    path("drivers/", views.list_drivers, name="driver-list"),
    path("routes/", views.list_routes, name="route-list"),
    path("payments/", views.list_payments, name="payment-list"),
    path("expenses/", views.list_expenses, name="expense-list"),
    # Goods (cargo types)
    path("goods/", views.list_goods, name="goods-list"),
    path("goods/add/", views.create_good, name="goods-create"),
    path("goods/<int:good_id>/", views.get_good, name="goods-detail"),
    path("goods/<int:good_id>/", views.update_good, name="goods-update"),
    path("goods/<int:good_id>/delete/", views.delete_good, name="goods-delete"),
    # Shipments
    path("shipments/", views.list_shipments, name="shipment-list"),
    path("shipments/add/", views.create_shipment, name="shipment-create"),
    path("shipments/<int:shipment_id>/", views.get_shipment, name="shipment-detail"),
    path(
        "shipments/<int:shipment_id>/edit/",
        views.update_shipment,
        name="shipment-update",
    ),
    path(
        "shipments/<int:shipment_id>/delete/",
        views.delete_shipment,
        name="shipment-delete",
    ),
    path(
        "shipments/<int:shipment_id>/advance/",
        views.advance_shipment,
        name="shipment-advance",
    ),
    path(
        "shipments/<int:shipment_id>/except/",
        views.shipment_exception,
        name="shipment-exception",
    ),
    path(
        "shipments/<int:shipment_id>/pod/",
        views.shipment_pod,
        name="shipment-pod",
    ),
    path(
        "shipments/<int:shipment_id>/unload/",
        views.shipment_unload,
        name="shipment-unload",
    ),
    # Drafts
    path("drafts/save/", views.save_draft, name="draft-save"),
    path("drafts/<int:draft_id>/submit/", views.submit_draft, name="draft-submit"),
    # Trips
    path("trips/", views.list_trips, name="trip-list"),
    path("trips/add/", views.create_trip, name="trip-create"),
    path("trips/<int:trip_id>/", views.get_trip, name="trip-detail"),
    path("trips/<int:trip_id>/edit/", views.update_trip, name="trip-update"),
    path("trips/<int:trip_id>/delete/", views.delete_trip, name="trip-delete"),
    path("trips/<int:trip_id>/advance/", views.advance_trip, name="trip-advance"),
    path("trips/<int:trip_id>/close/", views.close_trip, name="trip-close"),
    path("trips/<int:trip_id>/reopen/", views.reopen_trip, name="trip-reopen"),
    path("trips/<int:trip_id>/link/", views.link_shipments_to_trip, name="trip-link"),
    path("trips/<int:trip_id>/load/", views.load_trip, name="trip-load"),
    # Dashboard / reports
    path("dashboard/", views.transport_dashboard, name="transport-dashboard"),
    path("reports/", views.transport_reports, name="transport-reports"),
    path("reports/top/", views.transport_reports_top, name="transport-reports-top"),
]
