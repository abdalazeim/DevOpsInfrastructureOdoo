"""Serialization helpers for the transport module.

Each model has two helpers:
- serialize_<model>(obj) -> dict for single detail
- serialize_<model>_list(objs) -> list[dict] for list responses
"""

from decimal import Decimal
from django.utils import timezone


def _format_decimal(value):
    """Format a Decimal to a JSON-safe number."""
    if value is None:
        return None
    return float(value)


def _format_datetime(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _format_date(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


# ──────────────────────────────────────────────────────────────────────
# Customer
# ──────────────────────────────────────────────────────────────────────

def serialize_customer(customer):
    return {
        "id": customer.id,
        "code": customer.code,
        "name": customer.name,
        "phone": customer.phone or "",
        "email": customer.email or "",
        "address": customer.address or "",
        "is_active": customer.is_active,
        "created_at": _format_datetime(customer.created_at),
        "updated_at": _format_datetime(customer.updated_at),
    }


def serialize_customer_list(customers):
    return [serialize_customer(c) for c in customers]


# ──────────────────────────────────────────────────────────────────────
# Vehicle
# ──────────────────────────────────────────────────────────────────────

def serialize_vehicle(vehicle):
    return {
        "id": vehicle.id,
        "code": vehicle.code,
        "plate": vehicle.plate,
        "capacity_weight": _format_decimal(vehicle.capacity_weight),
        "capacity_volume": _format_decimal(vehicle.capacity_volume),
        "type": vehicle.type or "",
        "is_active": vehicle.is_active,
        "created_at": _format_datetime(vehicle.created_at),
        "updated_at": _format_datetime(vehicle.updated_at),
    }


def serialize_vehicle_list(vehicles):
    return [serialize_vehicle(v) for v in vehicles]


# ──────────────────────────────────────────────────────────────────────
# Driver
# ──────────────────────────────────────────────────────────────────────

def serialize_driver(driver):
    return {
        "id": driver.id,
        "code": driver.code,
        "name": driver.name,
        "phone": driver.phone or "",
        "license_number": driver.license_number or "",
        "hire_date": _format_date(driver.hire_date),
        "is_active": driver.is_active,
        "created_at": _format_datetime(driver.created_at),
        "updated_at": _format_datetime(driver.updated_at),
    }


def serialize_driver_list(drivers):
    return [serialize_driver(d) for d in drivers]


# ──────────────────────────────────────────────────────────────────────
# Route
# ──────────────────────────────────────────────────────────────────────

def serialize_route(route):
    return {
        "id": route.id,
        "code": route.code,
        "name": route.name,
        "origin": route.origin,
        "destination": route.destination,
        "distance_km": _format_decimal(route.distance_km),
        "is_active": route.is_active,
        "created_at": _format_datetime(route.created_at),
        "updated_at": _format_datetime(route.updated_at),
    }


def serialize_route_list(routes):
    return [serialize_route(r) for r in routes]


# ──────────────────────────────────────────────────────────────────────
# Good (cargo type)
# ──────────────────────────────────────────────────────────────────────

def serialize_good(good):
    return {
        "id": good.id,
        "code": good.code,
        "name": good.name,
        "description": good.description or "",
        "unit": good.unit or "pcs",
        "is_active": good.is_active,
        "created_at": _format_datetime(good.created_at),
        "updated_at": _format_datetime(good.updated_at),
    }


def serialize_good_list(goods):
    return [serialize_good(g) for g in goods]


# ──────────────────────────────────────────────────────────────────────
# Shipment
# ──────────────────────────────────────────────────────────────────────

def serialize_shipment(shipment):
    customer = shipment.customer
    return {
        "id": shipment.id,
        "code": shipment.code,
        "customer_id": customer.id if customer else None,
        "customer_code": customer.code if customer else None,
        "customer_name": customer.name if customer else None,
        "status": shipment.status,
        "origin": shipment.origin,
        "destination": shipment.destination,
        "weight": _format_decimal(shipment.weight),
        "volume": _format_decimal(shipment.volume),
        "notes": shipment.notes or "",
        "is_draft": shipment.is_draft,
        "is_active": shipment.is_active,
        "created_at": _format_datetime(shipment.created_at),
        "updated_at": _format_datetime(shipment.updated_at),
        "created_by": shipment.created_by_id,
        "updated_by": shipment.updated_by_id,
    }


def serialize_shipment_list(shipments):
    return [serialize_shipment(s) for s in shipments]


# ──────────────────────────────────────────────────────────────────────
# Trip
# ──────────────────────────────────────────────────────────────────────

def serialize_trip(trip):
    vehicle = trip.vehicle
    driver = trip.driver
    return {
        "id": trip.id,
        "code": trip.code,
        "vehicle_id": vehicle.id if vehicle else None,
        "vehicle_plate": vehicle.plate if vehicle else None,
        "driver_id": driver.id if driver else None,
        "driver_name": driver.name if driver else None,
        "status": trip.status,
        "origin": trip.origin,
        "destination": trip.destination,
        "planned_date": _format_datetime(trip.planned_date),
        "notes": trip.notes or "",
        "is_active": trip.is_active,
        "created_at": _format_datetime(trip.created_at),
        "updated_at": _format_datetime(trip.updated_at),
        "created_by": trip.created_by_id,
        "updated_by": trip.updated_by_id,
    }


def serialize_trip_list(trips):
    return [serialize_trip(t) for t in trips]


# ──────────────────────────────────────────────────────────────────────
# Payment
# ──────────────────────────────────────────────────────────────────────

def serialize_payment(payment):
    shipment = payment.shipment
    return {
        "id": payment.id,
        "code": payment.code,
        "shipment_id": shipment.id if shipment else None,
        "shipment_code": shipment.code if shipment else None,
        "amount": _format_decimal(payment.amount),
        "payment_date": _format_datetime(payment.payment_date),
        "method": payment.method or "",
        "is_active": payment.is_active,
        "created_at": _format_datetime(payment.created_at),
        "updated_at": _format_datetime(payment.updated_at),
    }


def serialize_payment_list(payments):
    return [serialize_payment(p) for p in payments]


# ──────────────────────────────────────────────────────────────────────
# Expense
# ──────────────────────────────────────────────────────────────────────

def serialize_expense(expense):
    trip = expense.trip
    return {
        "id": expense.id,
        "code": expense.code,
        "trip_id": trip.id if trip else None,
        "trip_code": trip.code if trip else None,
        "amount": _format_decimal(expense.amount),
        "expense_date": _format_datetime(expense.expense_date),
        "category": expense.category or "",
        "description": expense.description or "",
        "is_active": expense.is_active,
        "created_at": _format_datetime(expense.created_at),
        "updated_at": _format_datetime(expense.updated_at),
    }


def serialize_expense_list(expenses):
    return [serialize_expense(e) for e in expenses]


# ──────────────────────────────────────────────────────────────────────
# Meta / reference data (for Flutter dropdowns)
# ──────────────────────────────────────────────────────────────────────

def serialize_transport_meta():
    """Reference data for Flutter transport screens (statuses, types, etc.)."""
    from examples.transport.models import Shipment, Trip

    return {
        "shipment_statuses": [
            {"code": c, "label": lbl} for c, lbl in Shipment.Status.choices
        ],
        "trip_statuses": [
            {"code": c, "label": lbl} for c, lbl in Trip.Status.choices
        ],
        "goods_units": ["pcs", "kg", "ton", "box", "pallet", "liter", "meter"],
        "payment_methods": ["cash", "bank_transfer", "check", "credit", "other"],
        "expense_categories": [
            "fuel", "maintenance", "toll", "insurance", "loading",
            "unloading", "accommodation", "food", "other",
        ],
    }


# ──────────────────────────────────────────────────────────────────────
# Dashboard / reports
# ──────────────────────────────────────────────────────────────────────

def serialize_transport_dashboard(stats):
    return {
        "total_shipments": stats.get("total_shipments", 0),
        "pending_shipments": stats.get("pending_shipments", 0),
        "in_transit_shipments": stats.get("in_transit_shipments", 0),
        "delivered_shipments": stats.get("delivered_shipments", 0),
        "exception_shipments": stats.get("exception_shipments", 0),
        "total_trips": stats.get("total_trips", 0),
        "active_trips": stats.get("active_trips", 0),
        "completed_trips": stats.get("completed_trips", 0),
        "total_revenue": _format_decimal(stats.get("total_revenue")),
        "total_expenses": _format_decimal(stats.get("total_expenses")),
    }


def serialize_transport_reports(report_data):
    return {
        "throughput": report_data.get("throughput", []),
        "expenses": report_data.get("expenses", []),
        "income": report_data.get("income", []),
        "payment_methods": report_data.get("payment_methods", []),
        "status_distribution": report_data.get("status_distribution", []),
        "top_customers": report_data.get("top_customers", []),
    }


def serialize_transport_reports_top(top_data):
    return {
        "top_customers": top_data.get("top_customers", []),
        "top_vehicles": top_data.get("top_vehicles", []),
        "top_drivers": top_data.get("top_drivers", []),
    }
