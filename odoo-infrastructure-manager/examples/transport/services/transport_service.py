"""Service layer for the transport module.

Business logic lives here, not in views. Each operation is transactional
and optionally writes an audit entry.
"""

import logging
from django.db import transaction

from apps.core.services.audit_service import log_audit
from apps.core.utils.exceptions import BusinessRuleError, ConflictError, NotFoundError

from examples.transport.models import Shipment, Trip
from examples.transport.repositories import TransportRepository

logger = logging.getLogger("apps.api")

repository = TransportRepository()


class ShipmentService:
    """Service for shipment operations."""

    def create(self, request=None, *, user, data):
        code = (data or {}).get("code", "").strip()
        if not code:
            raise BusinessRuleError("كود الشحنة مطلوب")

        if Shipment.objects.filter(code=code).exists():
            raise ConflictError("كود الشحنة مستخدم مسبقاً")

        with transaction.atomic():
            shipment = repository.create_shipment(user=user, data=data)
            log_audit(
                request,
                action="create",
                module="transport",
                object_id=str(shipment.pk),
                object_repr=shipment.code,
                new_value={"code": shipment.code, "status": shipment.status},
                user=user,
            )
        logger.info("Shipment created: %s", shipment.code)
        return shipment

    def update(self, obj_id, request=None, *, user, data):
        shipment = repository.get_shipment_by_id(obj_id)
        if not shipment:
            raise NotFoundError("الشحنة غير موجودة")

        old_value = {"code": shipment.code, "status": shipment.status}

        with transaction.atomic():
            shipment = repository.update_shipment(shipment, data=data)
            log_audit(
                request,
                action="update",
                module="transport",
                object_id=str(shipment.pk),
                object_repr=shipment.code,
                old_value=old_value,
                new_value={"code": shipment.code, "status": shipment.status},
                user=user,
            )
        return shipment

    def delete(self, obj_id, request=None, *, user):
        shipment = repository.get_shipment_by_id(obj_id)
        if not shipment:
            raise NotFoundError("الشحنة غير موجودة")

        with transaction.atomic():
            repository.delete_shipment(shipment)
            log_audit(
                request,
                action="delete",
                module="transport",
                object_id=str(obj_id),
                object_repr=shipment.code,
                user=user,
            )

    def advance(self, obj_id, request=None, *, user):
        shipment = repository.get_shipment_by_id(obj_id)
        if not shipment:
            raise NotFoundError("الشحنة غير موجودة")

        with transaction.atomic():
            shipment = repository.advance_shipment(shipment)
            log_audit(
                request,
                action="update",
                module="transport",
                object_id=str(shipment.pk),
                object_repr=shipment.code,
                new_value={"status": shipment.status},
                user=user,
            )
        return shipment

    def exception(self, obj_id, request=None, *, user, data):
        shipment = repository.get_shipment_by_id(obj_id)
        if not shipment:
            raise NotFoundError("الشحنة غير موجودة")
        reason = (data or {}).get("reason", "").strip()
        if not reason:
            raise BusinessRuleError("سبب الاستثناء مطلوب")

        with transaction.atomic():
            shipment = repository.shipment_exception(shipment, reason)
            log_audit(
                request,
                action="update",
                module="transport",
                object_id=str(shipment.pk),
                object_repr=shipment.code,
                new_value={"status": shipment.status, "exception_reason": reason},
                user=user,
            )
        return shipment

    def pod(self, obj_id, request=None, *, user, data):
        shipment = repository.get_shipment_by_id(obj_id)
        if not shipment:
            raise NotFoundError("الشحنة غير موجودة")

        with transaction.atomic():
            repository.shipment_pod(
                shipment,
                signature=(data or {}).get("signature", ""),
                photo=(data or {}).get("photo", ""),
            )
            log_audit(
                request,
                action="update",
                module="transport",
                object_id=str(shipment.pk),
                object_repr=shipment.code,
                new_value={"pod_saved": True},
                user=user,
            )
        return shipment

    def unload(self, obj_id, request=None, *, user):
        shipment = repository.get_shipment_by_id(obj_id)
        if not shipment:
            raise NotFoundError("الشحنة غير موجودة")

        with transaction.atomic():
            shipment = repository.shipment_unload(shipment)
            log_audit(
                request,
                action="update",
                module="transport",
                object_id=str(shipment.pk),
                object_repr=shipment.code,
                new_value={"status": shipment.status},
                user=user,
            )
        return shipment

    def save_draft(self, request=None, *, user, data):
        with transaction.atomic():
            draft = repository.save_draft(user=user, data=data)
            log_audit(
                request,
                action="create",
                module="transport",
                object_id=str(draft.pk),
                object_repr=draft.code,
                new_value={"code": draft.code, "is_draft": True},
                user=user,
            )
        return draft

    def submit_draft(self, obj_id, request=None, *, user):
        draft = repository.submit_draft(obj_id)
        if not draft:
            raise NotFoundError("المسودة غير موجودة")
        with transaction.atomic():
            log_audit(
                request,
                action="update",
                module="transport",
                object_id=str(draft.pk),
                object_repr=draft.code,
                new_value={"is_draft": False, "status": draft.status},
                user=user,
            )
        return draft


class TripService:
    """Service for trip operations."""

    def create(self, request=None, *, user, data):
        code = (data or {}).get("code", "").strip()
        if not code:
            raise BusinessRuleError("كود الرحلة مطلوب")

        if Trip.objects.filter(code=code).exists():
            raise ConflictError("كود الرحلة مستخدم مسبقاً")

        with transaction.atomic():
            trip = repository.create_trip(user=user, data=data)
            log_audit(
                request,
                action="create",
                module="transport",
                object_id=str(trip.pk),
                object_repr=trip.code,
                new_value={"code": trip.code, "status": trip.status},
                user=user,
            )
        return trip

    def update(self, obj_id, request=None, *, user, data):
        trip = repository.get_trip_by_id(obj_id)
        if not trip:
            raise NotFoundError("الرحلة غير موجودة")

        old_value = {"code": trip.code, "status": trip.status}

        with transaction.atomic():
            trip = repository.update_trip(trip, data=data)
            log_audit(
                request,
                action="update",
                module="transport",
                object_id=str(trip.pk),
                object_repr=trip.code,
                old_value=old_value,
                new_value={"code": trip.code, "status": trip.status},
                user=user,
            )
        return trip

    def delete(self, obj_id, request=None, *, user):
        trip = repository.get_trip_by_id(obj_id)
        if not trip:
            raise NotFoundError("الرحلة غير موجودة")

        with transaction.atomic():
            repository.delete_trip(trip)
            log_audit(
                request,
                action="delete",
                module="transport",
                object_id=str(obj_id),
                object_repr=trip.code,
                user=user,
            )

    def advance(self, obj_id, request=None, *, user):
        trip = repository.get_trip_by_id(obj_id)
        if not trip:
            raise NotFoundError("الرحلة غير موجودة")

        with transaction.atomic():
            trip = repository.advance_trip(trip)
            log_audit(
                request,
                action="update",
                module="transport",
                object_id=str(trip.pk),
                object_repr=trip.code,
                new_value={"status": trip.status},
                user=user,
            )
        return trip

    def close(self, obj_id, request=None, *, user):
        trip = repository.get_trip_by_id(obj_id)
        if not trip:
            raise NotFoundError("الرحلة غير موجودة")

        with transaction.atomic():
            trip = repository.close_trip(trip)
            log_audit(
                request,
                action="update",
                module="transport",
                object_id=str(trip.pk),
                object_repr=trip.code,
                new_value={"status": trip.status},
                user=user,
            )
        return trip

    def reopen(self, obj_id, request=None, *, user):
        trip = repository.get_trip_by_id(obj_id)
        if not trip:
            raise NotFoundError("الرحلة غير موجودة")

        with transaction.atomic():
            trip = repository.reopen_trip(trip)
            log_audit(
                request,
                action="update",
                module="transport",
                object_id=str(trip.pk),
                object_repr=trip.code,
                new_value={"status": trip.status},
                user=user,
            )
        return trip

    def link_shipments(self, obj_id, request=None, *, user, data):
        trip = repository.get_trip_by_id(obj_id)
        if not trip:
            raise NotFoundError("الرحلة غير موجودة")
        shipment_ids = (data or {}).get("shipIds", [])
        if not isinstance(shipment_ids, list):
            raise BusinessRuleError("قائمة الشحنات غير صحيحة")

        with transaction.atomic():
            trip = repository.link_shipments_to_trip(trip, shipment_ids)
            log_audit(
                request,
                action="update",
                module="transport",
                object_id=str(trip.pk),
                object_repr=trip.code,
                new_value={"linked_shipment_ids": shipment_ids},
                user=user,
            )
        return trip

    def load(self, obj_id, request=None, *, user, data):
        trip = repository.get_trip_by_id(obj_id)
        if not trip:
            raise NotFoundError("الرحلة غير موجودة")
        shipment_ids = (data or {}).get("shipIds", [])
        if not isinstance(shipment_ids, list):
            raise BusinessRuleError("قائمة الشحنات غير صحيحة")

        with transaction.atomic():
            trip = repository.load_trip(trip, shipment_ids)
            log_audit(
                request,
                action="update",
                module="transport",
                object_id=str(trip.pk),
                object_repr=trip.code,
                new_value={"status": trip.status, "loaded_shipment_ids": shipment_ids},
                user=user,
            )
        return trip
