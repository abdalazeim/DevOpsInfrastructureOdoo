"""Example module repository (data-access layer)."""

from apps.core.repositories import BaseRepository

from ..models import ExampleItem


class ExampleItemRepository(BaseRepository):
    """Repository for :class:`~apps.modules.example.models.ExampleItem`."""

    model = ExampleItem

    def search(self, term=""):
        qs = self.get_queryset()
        if term:
            from django.db.models import Q

            qs = qs.filter(Q(name__icontains=term) | Q(code__icontains=term))
        return qs

    def get_by_code(self, code):
        return self.get_queryset().filter(code=code).first()
