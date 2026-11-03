"""Example sync adapter; domain modules can register their own operations."""

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.core.models import SyncTombstone
from apps.core.services.sync_service import (
    SyncConflictError,
    register_sync_collection,
    register_sync_handler,
)
from apps.core.utils.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)

from .models import ExampleItem
from .repositories import ExampleItemRepository
from .serializers.example_serializer import serialize_example_item
from .services import ExampleItemService

_service = ExampleItemService()
_repository = ExampleItemRepository()
_SYNC_MODEL = "example.item"


def _data(payload):
    value = payload.get("data", {})
    if not isinstance(value, dict):
        raise ValidationError("data must be an object")
    return value


def _create(*, user, payload):
    try:
        item = _service.create(user=user, data=_data(payload))
    except IntegrityError as exc:
        # The unique code constraint can win a race after the preflight check.
        raise ConflictError("الكود مستخدم مسبقاً") from exc
    return serialize_example_item(item)


def _update(*, user, payload):
    item_id = payload.get("id")
    if item_id in (None, ""):
        raise ValidationError("id is required")
    with transaction.atomic():
        item = _repository.get_queryset().select_for_update().filter(pk=item_id).first()
        if item is None:
            raise NotFoundError("العنصر غير موجود")
        base_raw = payload.get("base_updated_at")
        if base_raw is not None:
            base_updated_at = parse_datetime(str(base_raw))
            if base_updated_at is None:
                raise ValidationError("base_updated_at must be an ISO timestamp")
            if timezone.is_naive(base_updated_at):
                base_updated_at = timezone.make_aware(
                    base_updated_at, timezone.get_current_timezone()
                )
            if item.updated_at and item.updated_at > base_updated_at:
                raise SyncConflictError(
                    "The item changed on the server after this device last read it.",
                    {
                        "model_label": _SYNC_MODEL,
                        "object_pk": str(item.pk),
                        "base_updated_at": base_updated_at,
                        "server_updated_at": item.updated_at,
                        "payload": payload,
                    },
                )
        updated = _service.update(
            item.pk,
            user=user,
            data=_data(payload),
        )
        return serialize_example_item(updated)


def _delete(*, user, payload):
    item_id = payload.get("id")
    if item_id in (None, ""):
        raise ValidationError("id is required")
    item = _repository.get_by_id(item_id)
    with transaction.atomic():
        tombstone, _ = SyncTombstone.objects.update_or_create(
            model_label=_SYNC_MODEL,
            object_pk=str(item.pk),
            scope_key="",
            defaults={"deleted_by": user},
        )
        _service.delete(item.pk, user=user)
    return {
        "id": str(item.pk),
        "deleted": True,
        "deleted_at": tombstone.deleted_at.isoformat(),
    }


def register_example_sync():
    register_sync_handler(
        "example.item.create", _create, permission="example_manage"
    )
    register_sync_handler(
        "example.item.update", _update, permission="example_manage"
    )
    register_sync_handler(
        "example.item.delete", _delete, permission="example_manage"
    )
    register_sync_collection(
        _SYNC_MODEL,
        model=ExampleItem,
        serializer=serialize_example_item,
        permission="example_view",
        model_label=_SYNC_MODEL,
    )
