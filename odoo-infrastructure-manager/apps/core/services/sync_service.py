"""Registry and transaction boundary for generic offline mutations."""

import logging
import uuid
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.services.permission_service import has_permission
from apps.core.models import SyncConflict, SyncOperation, SyncTombstone
from apps.core.utils.exceptions import AppError, PermissionDenied, ValidationError

logger = logging.getLogger("apps.api")


@dataclass(frozen=True)
class SyncHandler:
    callback: object
    permission: str


@dataclass(frozen=True)
class SyncCollection:
    model: object
    serializer: object
    permission: str
    model_label: str
    queryset: object
    scope_key: object


class SyncConflictError(Exception):
    def __init__(self, message, evidence):
        self.message = message
        self.evidence = evidence
        super().__init__(message)


_handlers = {}
_collections = {}


def register_sync_handler(kind, callback, *, permission):
    """Register one module-owned operation kind."""
    if kind in _handlers and _handlers[kind].callback is not callback:
        raise ValueError(f"Sync handler already registered: {kind}")
    _handlers[kind] = SyncHandler(callback=callback, permission=permission)


def register_sync_collection(
    name,
    *,
    model,
    serializer,
    permission,
    model_label=None,
    queryset=None,
    scope_key=None,
):
    """Register one pull collection without coupling core to its model."""
    if name in _collections and _collections[name].model is not model:
        raise ValueError(f"Sync collection already registered: {name}")
    _collections[name] = SyncCollection(
        model=model,
        serializer=serializer,
        permission=permission,
        model_label=model_label or name,
        queryset=queryset,
        scope_key=scope_key,
    )


def sync_collections():
    return dict(_collections)


def execute_once(user, operation):
    """Apply an operation once; duplicate IDs replay the original outcome."""
    operation_id_raw = operation.get("operation_id")
    kind = operation.get("kind")
    payload = operation.get("payload", {})
    try:
        operation_id = uuid.UUID(str(operation_id_raw))
    except (ValueError, TypeError, AttributeError):
        return _ephemeral_rejection(operation_id_raw, "operation_id must be a UUID", "invalid_operation_id")
    if not isinstance(kind, str) or not kind:
        return _ephemeral_rejection(operation_id, "kind is required", "invalid_kind")
    if not isinstance(payload, dict):
        return _ephemeral_rejection(operation_id, "payload must be an object", "invalid_payload")

    previous = SyncOperation.objects.filter(operation_id=operation_id).first()
    if previous is not None:
        return _replay(previous, user)

    handler = _handlers.get(kind)
    try:
        with transaction.atomic():
            record = SyncOperation.objects.create(
                operation_id=operation_id,
                user=user,
                kind=kind,
                status=SyncOperation.PROCESSING,
            )
            try:
                with transaction.atomic():
                    if handler is None:
                        raise AppError(f"Unknown sync operation: {kind}")
                    if not has_permission(user, handler.permission):
                        raise PermissionDenied()
                    result = handler.callback(user=user, payload=payload)
            except SyncConflictError as exc:
                result = {
                    "status": SyncOperation.CONFLICT,
                    "error": exc.message,
                    "code": "stale_write",
                }
                record.status = SyncOperation.CONFLICT
                record.error = exc.message
                record.result = result
                record.applied_at = timezone.now()
                record.save(update_fields=["status", "error", "result", "applied_at"])
                SyncConflict.objects.create(
                    operation_id=operation_id,
                    user=user,
                    kind=kind,
                    message=exc.message,
                    **exc.evidence,
                )
            except AppError as exc:
                result = {
                    "status": SyncOperation.REJECTED,
                    "error": exc.message,
                    "code": "operation_rejected",
                }
                record.status = SyncOperation.REJECTED
                record.error = exc.message
                record.result = result
                record.applied_at = timezone.now()
                record.save(update_fields=["status", "error", "result", "applied_at"])
            else:
                result = {"status": SyncOperation.APPLIED, "data": result}
                record.status = SyncOperation.APPLIED
                record.result = result
                record.applied_at = timezone.now()
                record.save(update_fields=["status", "result", "applied_at"])
    except IntegrityError:
        # The unique operation ID is the cross-request concurrency barrier.
        winner = SyncOperation.objects.filter(operation_id=operation_id).first()
        if winner is None:
            raise
        return _replay(winner, user)

    return {"operation_id": str(operation_id), **result, "replayed": False}


def _replay(record, user):
    if record.user_id != getattr(user, "id", None):
        logger.warning("Sync operation replay attempted by a different user")
        return _ephemeral_rejection(
            record.operation_id,
            "This operation ID belongs to another user.",
            "operation_not_yours",
        )
    handler = _handlers.get(record.kind)
    if handler is not None and not has_permission(user, handler.permission):
        return _ephemeral_rejection(
            record.operation_id,
            "You no longer have permission to read this operation result.",
            "permission_revoked",
        )
    return {
        "operation_id": str(record.operation_id),
        **record.result,
        "replayed": True,
    }


def _ephemeral_rejection(operation_id, message, code):
    return {
        "operation_id": str(operation_id) if operation_id is not None else None,
        "status": SyncOperation.REJECTED,
        "error": message,
        "code": code,
        "replayed": False,
    }


def pull_changes(user, *, since, cursor, requested_models):
    """Read registered collections and deletion records visible to this user."""
    allowed = {}
    for name in requested_models or _collections.keys():
        collection = _collections.get(name)
        if collection is None:
            raise ValidationError(f"Unknown sync collection: {name}")
        if not has_permission(user, collection.permission):
            raise PermissionDenied()
        allowed[name] = collection

    rows = {}
    for name, collection in allowed.items():
        queryset = (
            collection.queryset(user=user)
            if collection.queryset is not None
            else collection.model.objects.all()
        )
        queryset = queryset.filter(updated_at__lte=cursor)
        if since is not None:
            queryset = queryset.filter(updated_at__gt=since)
        queryset = queryset.order_by("updated_at", "pk")
        rows[name] = [collection.serializer(item) for item in queryset]
    tombstones = []
    for collection in allowed.values():
        scope_key = (
            collection.scope_key(user=user)
            if collection.scope_key is not None
            else ""
        )
        queryset = SyncTombstone.objects.filter(
            model_label=collection.model_label,
            scope_key=str(scope_key),
            deleted_at__lte=cursor,
        ).order_by("deleted_at", "pk")
        if since is not None:
            queryset = queryset.filter(deleted_at__gt=since)
        tombstones.extend(
            {
                "model": item.model_label,
                "id": item.object_pk,
                "deleted_at": item.deleted_at.isoformat(),
            }
            for item in queryset
        )
    return {"rows": rows, "tombstones": tombstones, "cursor": cursor.isoformat()}
