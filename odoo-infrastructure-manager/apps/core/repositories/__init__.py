"""Generic Repository Pattern base.

Provides a thin, reusable data-access layer on top of Django ORM.
Modules create their own repositories by inheriting ``BaseRepository`` and
declare the model — keeping services/views free of direct ORM calls when a
repository is warranted.
"""

from django.db import transaction

from apps.core.utils.exceptions import NotFoundError


class BaseRepository:
    """CRUD + queryset helpers for a single model class."""

    model = None

    def __init__(self, model=None):
        if model is not None:
            self.model = model
        if self.model is None:
            raise ValueError("BaseRepository requires a model")

    # ─── Query helpers ────────────────────────────────────────────────
    def get_queryset(self):
        return self.model.objects.all()

    def get_all(self):
        return self.get_queryset()

    def get_by_id(self, obj_id):
        try:
            return self.get_queryset().get(pk=obj_id)
        except self.model.DoesNotExist:
            raise NotFoundError(f"{self.model._meta.verbose_name} غير موجود")

    def filter(self, *args, **kwargs):
        return self.get_queryset().filter(*args, **kwargs)

    def exists(self, *args, **kwargs):
        return self.get_queryset().filter(*args, **kwargs).exists()

    def count(self, *args, **kwargs):
        return self.get_queryset().filter(*args, **kwargs).count()

    # ─── Write helpers ─────────────────────────────────────────────────
    def create(self, **kwargs):
        return self.model.objects.create(**kwargs)

    @transaction.atomic
    def bulk_create(self, objs, **kwargs):
        return self.model.objects.bulk_create(objs, **kwargs)

    def update(self, obj_id, **kwargs):
        obj = self.get_by_id(obj_id)
        for field, value in kwargs.items():
            setattr(obj, field, value)
        obj.save()
        return obj

    def delete(self, obj_id):
        obj = self.get_by_id(obj_id)
        obj.delete()
        return obj

    def get_or_none(self, obj_id):
        try:
            return self.get_queryset().get(pk=obj_id)
        except self.model.DoesNotExist:
            return None
