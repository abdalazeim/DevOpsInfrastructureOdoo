"""Example module service layer.

Business logic lives here (not in views). Each operation is transactional and
optionally writes an audit entry, following the Master Template conventions.
"""

import logging

from django.db import transaction

from apps.core.services.audit_service import log_audit
from apps.core.utils.exceptions import (
    BusinessRuleError,
    ConflictError,
    ValidationError as AppValidationError,
)

from ..models import ExampleItem
from ..repositories import ExampleItemRepository
from ..serializers.example_serializer import ExampleItemInputSerializer

logger = logging.getLogger("apps.api")

repository = ExampleItemRepository()


class ExampleItemService:
    """Service for :class:`~apps.modules.example.models.ExampleItem`."""

    def create(self, request=None, *, user=None, data=None):
        payload = self._validate_payload(data, partial=False)
        name = payload.get("name", "").strip()
        code = payload.get("code", "").strip()
        if not name or not code:
            raise AppValidationError("الاسم والرمز مطلوبان")

        if repository.exists(code=code):
            raise ConflictError("الكود مستخدم مسبقاً")

        with transaction.atomic():
            item = repository.create(
                name=name,
                code=code,
                description=payload.get("description", ""),
                quantity=payload.get("quantity", 0),
                sort_order=payload.get("sort_order", 0),
            )
            log_audit(
                request,
                action="create",
                module="example",
                object_id=str(item.pk),
                object_repr=item.name,
                new_value={"code": item.code, "name": item.name},
                user=user,
            )
        logger.info("Example item created: %s (%s)", item.name, item.code)
        return item

    def update(self, obj_id, request=None, *, user=None, data=None):
        item = repository.get_by_id(obj_id)
        payload = self._validate_payload(data, partial=True)
        if not payload:
            raise AppValidationError("أرسل حقلاً واحداً على الأقل للتحديث")
        old_value = {"code": item.code, "name": item.name}

        name = payload.get("name")
        code = payload.get("code")
        if code and repository.get_queryset().filter(code=code).exclude(pk=item.pk).exists():
            raise ConflictError("الكود مستخدم مسبقاً")

        with transaction.atomic():
            if name is not None:
                item.name = name.strip()
            if code is not None:
                item.code = code.strip()
            if "description" in payload:
                item.description = payload["description"]
            if "quantity" in payload:
                item.quantity = payload["quantity"]
            if "sort_order" in payload:
                item.sort_order = payload["sort_order"]
            if not item.name or not item.code:
                raise AppValidationError("الاسم والرمز مطلوبان")
            item.save()
            log_audit(
                request,
                action="update",
                module="example",
                object_id=str(item.pk),
                object_repr=item.name,
                old_value=old_value,
                new_value={"code": item.code, "name": item.name},
                user=user,
            )
        return item

    def delete(self, obj_id, request=None, *, user=None):
        item = repository.get_by_id(obj_id)
        with transaction.atomic():
            item.delete()
            log_audit(
                request,
                action="delete",
                module="example",
                object_id=str(obj_id),
                object_repr=item.name,
                user=user,
            )
        return item

    def list(self, *, term="", page=1, page_size=20):
        qs = repository.search(term)
        return qs, repository.count()

    @staticmethod
    def _validate_payload(data, *, partial):
        serializer = ExampleItemInputSerializer(
            data=data if isinstance(data, dict) else {},
            partial=partial,
        )
        if not serializer.is_valid():
            raise AppValidationError("بيانات غير صالحة")
        return serializer.validated_data
