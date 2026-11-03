"""Example module serializers.

Plain dict serializers (framework-agnostic). If the project adopts DRF,
replace these with ``rest_framework.serializers.ModelSerializer`` subclasses
while keeping the same field names.
"""

from rest_framework import serializers


class ExampleItemInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    code = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(
        max_length=10_000,
        required=False,
        allow_blank=True,
    )
    quantity = serializers.IntegerField(
        required=False,
        min_value=0,
        max_value=2_147_483_647,
    )
    sort_order = serializers.IntegerField(required=False)


def serialize_example_item(item):
    return {
        "id": item.pk,
        "name": item.name,
        "code": item.code,
        "description": item.description,
        "quantity": item.quantity,
        "sort_order": item.sort_order,
        "is_active": item.is_active,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def serialize_example_item_list(items):
    return [serialize_example_item(item) for item in items]
