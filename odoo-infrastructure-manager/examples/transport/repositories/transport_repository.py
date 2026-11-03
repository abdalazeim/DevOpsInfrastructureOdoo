"""Repository layer for the transport module.

Encapsulates all database queries for transport models.
Follows the BaseRepository pattern from core.
"""

from django.db.models import Q, Sum
from django.utils import timezone

from examples.transport.models import (
    Shipment, Trip, Good, Customer, Vehicle, Driver,
    Route, Payment, Expense, ShipmentException, ShipmentPOD,
    TripShipment,
)


class TransportRepository:
    """Repository for all transport domain entities.

    Handles multiple models; does not inherit BaseRepository (which is
    designed for single-model repositories).
    """

    # ─── Customer ────────────────────────────────────────────────────

    def get_customer_by_id(self, customer_id):
        return Customer.objects.filter(id=customer_id, is_active=True).first()

    def list_customers(self, search=""):
        qs = Customer.objects.filter(is_active=True)
        if search:
            qs = qs.filter(Q(code__icontains=search) | Q(name__icontains=search))
        return qs.order_by("name")

    def create_customer(self, *, user, data):
        customer = Customer.objects.create(
            code=data["code"],
            name=data["name"],
            phone=data.get("phone", ""),
            email=data.get("email", ""),
            address=data.get("address", ""),
            created_by=user,
        )
        return customer

    def update_customer(self, customer, *, data):
        for field in ("code", "name", "phone", "email", "address", "is_active"):
            if field in data:
                setattr(customer, field, data[field])
        customer.save()
        return customer

    def delete_customer(self, customer):
        if hasattr(customer, "soft_delete"):
            customer.soft_delete()
        else:
            customer.delete()

    # ─── Vehicle ─────────────────────────────────────────────────────

    def get_vehicle_by_id(self, vehicle_id):
        return Vehicle.objects.filter(id=vehicle_id, is_active=True).first()

    def list_vehicles(self, search=""):
        qs = Vehicle.objects.filter(is_active=True)
        if search:
            qs = qs.filter(Q(code__icontains=search) | Q(plate__icontains=search))
        return qs.order_by("plate")

    def create_vehicle(self, *, user, data):
        return Vehicle.objects.create(
            code=data["code"],
            plate=data["plate"],
            capacity_weight=data.get("capacity_weight", 0),
            capacity_volume=data.get("capacity_volume", 0),
            type=data.get("type", ""),
            created_by=user,
        )

    def update_vehicle(self, vehicle, *, data):
        for field in ("code", "plate", "capacity_weight", "capacity_volume", "type", "is_active"):
            if field in data:
                setattr(vehicle, field, data[field])
        vehicle.save()
        return vehicle

    def delete_vehicle(self, vehicle):
        if hasattr(vehicle, "soft_delete"):
            vehicle.soft_delete()
        else:
            vehicle.delete()

    # ─── Driver ──────────────────────────────────────────────────────

    def get_driver_by_id(self, driver_id):
        return Driver.objects.filter(id=driver_id, is_active=True).first()

    def list_drivers(self, search=""):
        qs = Driver.objects.filter(is_active=True)
        if search:
            qs = qs.filter(Q(code__icontains=search) | Q(name__icontains=search))
        return qs.order_by("name")

    def create_driver(self, *, user, data):
        return Driver.objects.create(
            code=data["code"],
            name=data["name"],
            phone=data.get("phone", ""),
            license_number=data.get("license_number", ""),
            hire_date=data.get("hire_date"),
            created_by=user,
        )

    def update_driver(self, driver, *, data):
        for field in ("code", "name", "phone", "license_number", "hire_date", "is_active"):
            if field in data:
                setattr(driver, field, data[field])
        driver.save()
        return driver

    def delete_driver(self, driver):
        if hasattr(driver, "soft_delete"):
            driver.soft_delete()
        else:
            driver.delete()

    # ─── Route ───────────────────────────────────────────────────────

    def get_route_by_id(self, route_id):
        return Route.objects.filter(id=route_id, is_active=True).first()

    def list_routes(self, search=""):
        qs = Route.objects.filter(is_active=True)
        if search:
            qs = qs.filter(Q(code__icontains=search) | Q(name__icontains=search))
        return qs.order_by("name")

    def create_route(self, *, user, data):
        return Route.objects.create(
            code=data["code"],
            name=data["name"],
            origin=data["origin"],
            destination=data["destination"],
            distance_km=data.get("distance_km", 0),
            created_by=user,
        )

    def update_route(self, route, *, data):
        for field in ("code", "name", "origin", "destination", "distance_km", "is_active"):
            if field in data:
                setattr(route, field, data[field])
        route.save()
        return route

    def delete_route(self, route):
        if hasattr(route, "soft_delete"):
            route.soft_delete()
        else:
            route.delete()

    # ─── Good ────────────────────────────────────────────────────────

    def get_good_by_id(self, good_id):
        return Good.objects.filter(id=good_id, is_active=True).first()

    def list_goods(self, search=""):
        qs = Good.objects.filter(is_active=True)
        if search:
            qs = qs.filter(Q(code__icontains=search) | Q(name__icontains=search))
        return qs.order_by("name")

    def create_good(self, *, user, data):
        return Good.objects.create(
            code=data["code"],
            name=data["name"],
            description=data.get("description", ""),
            unit=data.get("unit", "pcs"),
            created_by=user,
        )

    def update_good(self, good, *, data):
        for field in ("code", "name", "description", "unit", "is_active"):
            if field in data:
                setattr(good, field, data[field])
        good.save()
        return good

    def delete_good(self, good):
        if hasattr(good, "soft_delete"):
            good.soft_delete()
        else:
            good.delete()

    # ─── Shipment ────────────────────────────────────────────────────

    def get_shipment_by_id(self, shipment_id):
        return Shipment.objects.filter(id=shipment_id).first()

    def list_shipments(self, search="", status=None, drafts=False):
        qs = Shipment.objects.all()
        if drafts:
            qs = qs.filter(is_draft=True)
        if status:
            qs = qs.filter(status=status)
        if search:
            qs = qs.filter(
                Q(code__icontains=search)
                | Q(customer__name__icontains=search)
                | Q(origin__icontains=search)
                | Q(destination__icontains=search)
            )
        return qs.select_related("customer").order_by("-created_at")

    def create_shipment(self, *, user, data):
        return Shipment.objects.create(
            code=data["code"],
            customer_id=data["customer_id"],
            status=data.get("status", Shipment.Status.DRAFT),
            origin=data.get("origin", ""),
            destination=data.get("destination", ""),
            weight=data.get("weight", 0),
            volume=data.get("volume", 0),
            notes=data.get("notes", ""),
            is_draft=data.get("is_draft", True),
            created_by=user,
        )

    def update_shipment(self, shipment, *, data):
        for field in ("code", "customer_id", "status", "origin", "destination",
                      "weight", "volume", "notes", "is_draft", "is_active"):
            if field in data:
                setattr(shipment, field, data[field])
        shipment.save()
        return shipment

    def delete_shipment(self, shipment):
        if hasattr(shipment, "soft_delete"):
            shipment.soft_delete()
        else:
            shipment.delete()

    def advance_shipment(self, shipment):
        """Move shipment to next status."""
        status_order = [
            Shipment.Status.DRAFT,
            Shipment.Status.PENDING,
            Shipment.Status.LOADED,
            Shipment.Status.IN_TRANSIT,
            Shipment.Status.DELIVERED,
        ]
        try:
            current_idx = status_order.index(shipment.status)
        except ValueError:
            current_idx = 0
        if current_idx + 1 < len(status_order):
            shipment.status = status_order[current_idx + 1]
            shipment.save()
        return shipment

    def shipment_exception(self, shipment, reason):
        ShipmentException.objects.create(shipment=shipment, reason=reason)
        shipment.status = Shipment.Status.EXCEPTION
        shipment.save()
        return shipment

    def shipment_pod(self, shipment, signature, photo):
        pod, _ = ShipmentPOD.objects.update_or_create(
            shipment=shipment,
            defaults={"signature": signature, "photo": photo},
        )
        return pod

    def shipment_unload(self, shipment):
        shipment.status = Shipment.Status.DELIVERED
        shipment.save()
        return shipment

    # ─── Drafts ──────────────────────────────────────────────────────

    def save_draft(self, *, user, data):
        return Shipment.objects.create(
            code=data.get("code", f"DRAFT-{timezone.now().strftime('%Y%m%d%H%M%S')}"),
            customer_id=data.get("customer_id"),
            status=Shipment.Status.DRAFT,
            origin=data.get("origin", ""),
            destination=data.get("destination", ""),
            weight=data.get("weight", 0),
            volume=data.get("volume", 0),
            notes=data.get("notes", ""),
            is_draft=True,
            created_by=user,
        )

    def submit_draft(self, draft_id):
        draft = Shipment.objects.filter(id=draft_id, is_draft=True).first()
        if not draft:
            return None
        draft.is_draft = False
        draft.status = Shipment.Status.PENDING
        draft.save()
        return draft

    # ─── Trip ────────────────────────────────────────────────────────

    def get_trip_by_id(self, trip_id):
        return Trip.objects.filter(id=trip_id).first()

    def list_trips(self, search="", status=None):
        qs = Trip.objects.all()
        if status:
            qs = qs.filter(status=status)
        if search:
            qs = qs.filter(
                Q(code__icontains=search)
                | Q(vehicle__plate__icontains=search)
                | Q(driver__name__icontains=search)
            )
        return qs.select_related("vehicle", "driver").order_by("-created_at")

    def create_trip(self, *, user, data):
        return Trip.objects.create(
            code=data["code"],
            vehicle_id=data["vehicle_id"],
            driver_id=data["driver_id"],
            status=data.get("status", Trip.Status.PLANNED),
            origin=data.get("origin", ""),
            destination=data.get("destination", ""),
            planned_date=data.get("planned_date"),
            notes=data.get("notes", ""),
            created_by=user,
        )

    def update_trip(self, trip, *, data):
        for field in ("code", "vehicle_id", "driver_id", "status", "origin",
                      "destination", "planned_date", "notes", "is_active"):
            if field in data:
                setattr(trip, field, data[field])
        trip.save()
        return trip

    def delete_trip(self, trip):
        if hasattr(trip, "soft_delete"):
            trip.soft_delete()
        else:
            trip.delete()

    def advance_trip(self, trip):
        status_order = [
            Trip.Status.PLANNED,
            Trip.Status.LOADING,
            Trip.Status.IN_PROGRESS,
            Trip.Status.COMPLETED,
        ]
        try:
            current_idx = status_order.index(trip.status)
        except ValueError:
            current_idx = 0
        if current_idx + 1 < len(status_order):
            trip.status = status_order[current_idx + 1]
            trip.save()
        return trip

    def close_trip(self, trip):
        trip.status = Trip.Status.CLOSED
        trip.save()
        return trip

    def reopen_trip(self, trip):
        trip.status = Trip.Status.IN_PROGRESS
        trip.save()
        return trip

    def link_shipments_to_trip(self, trip, shipment_ids):
        TripShipment.objects.filter(trip=trip).exclude(
            shipment_id__in=shipment_ids
        ).delete()
        for sid in shipment_ids:
            TripShipment.objects.get_or_create(trip=trip, shipment_id=sid)
        return trip

    def load_trip(self, trip, shipment_ids):
        """Load shipments onto trip with capacity enforcement."""
        total_weight = Shipment.objects.filter(
            id__in=shipment_ids
        ).aggregate(total=Sum("weight"))["total"] or 0
        total_volume = Shipment.objects.filter(
            id__in=shipment_ids
        ).aggregate(total=Sum("volume"))["total"] or 0

        if total_weight > trip.vehicle.capacity_weight:
            raise ValueError("الوزن الإجمالي يتجاوز سعة المركبة")
        if total_volume > trip.vehicle.capacity_volume:
            raise ValueError("الحجم الإجمالي يتجاوز سعة المركبة")

        self.link_shipments_to_trip(trip, shipment_ids)
        trip.status = Trip.Status.LOADING
        trip.save()
        return trip

    # ─── Payment ─────────────────────────────────────────────────────

    def get_payment_by_id(self, payment_id):
        return Payment.objects.filter(id=payment_id).first()

    def list_payments(self, search=""):
        qs = Payment.objects.all()
        if search:
            qs = qs.filter(
                Q(code__icontains=search)
                | Q(shipment__code__icontains=search)
            )
        return qs.select_related("shipment").order_by("-payment_date")

    def create_payment(self, *, user, data):
        return Payment.objects.create(
            code=data["code"],
            shipment_id=data["shipment_id"],
            amount=data["amount"],
            payment_date=data.get("payment_date", timezone.now()),
            method=data.get("method", ""),
            created_by=user,
        )

    def update_payment(self, payment, *, data):
        for field in ("code", "shipment_id", "amount", "payment_date", "method", "is_active"):
            if field in data:
                setattr(payment, field, data[field])
        payment.save()
        return payment

    def delete_payment(self, payment):
        if hasattr(payment, "soft_delete"):
            payment.soft_delete()
        else:
            payment.delete()

    # ─── Expense ─────────────────────────────────────────────────────

    def get_expense_by_id(self, expense_id):
        return Expense.objects.filter(id=expense_id).first()

    def list_expenses(self, search=""):
        qs = Expense.objects.all()
        if search:
            qs = qs.filter(
                Q(code__icontains=search)
                | Q(trip__code__icontains=search)
            )
        return qs.select_related("trip").order_by("-expense_date")

    def create_expense(self, *, user, data):
        return Expense.objects.create(
            code=data["code"],
            trip_id=data["trip_id"],
            amount=data["amount"],
            expense_date=data.get("expense_date", timezone.now()),
            category=data.get("category", ""),
            description=data.get("description", ""),
            created_by=user,
        )

    def update_expense(self, expense, *, data):
        for field in ("code", "trip_id", "amount", "expense_date", "category",
                      "description", "is_active"):
            if field in data:
                setattr(expense, field, data[field])
        expense.save()
        return expense

    def delete_expense(self, expense):
        if hasattr(expense, "soft_delete"):
            expense.soft_delete()
        else:
            expense.delete()

    # ─── Dashboard / Reports ─────────────────────────────────────────

    def dashboard_stats(self):
        return {
            "total_shipments": Shipment.objects.count(),
            "pending_shipments": Shipment.objects.filter(status=Shipment.Status.PENDING).count(),
            "in_transit_shipments": Shipment.objects.filter(status=Shipment.Status.IN_TRANSIT).count(),
            "delivered_shipments": Shipment.objects.filter(status=Shipment.Status.DELIVERED).count(),
            "exception_shipments": Shipment.objects.filter(status=Shipment.Status.EXCEPTION).count(),
            "total_trips": Trip.objects.count(),
            "active_trips": Trip.objects.filter(status__in=[Trip.Status.IN_PROGRESS, Trip.Status.LOADING]).count(),
            "completed_trips": Trip.objects.filter(status=Trip.Status.COMPLETED).count(),
            "total_revenue": Payment.objects.aggregate(total=Sum("amount"))["total"] or 0,
            "total_expenses": Expense.objects.aggregate(total=Sum("amount"))["total"] or 0,
        }

    def transport_reports(self):
        return {
            "throughput": [],
            "expenses": [],
            "income": [],
            "payment_methods": [],
            "status_distribution": [],
            "top_customers": [],
        }

    def transport_reports_top(self):
        return {
            "top_customers": [],
            "top_vehicles": [],
            "top_drivers": [],
        }
