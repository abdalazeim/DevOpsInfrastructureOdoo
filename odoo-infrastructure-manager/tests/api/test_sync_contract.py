import json
import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.core.models import SyncConflict, SyncOperation, SyncTombstone
from apps.core.services.sync_service import register_sync_collection, sync_collections
from apps.modules.example.models import ExampleItem
from apps.modules.example.serializers.example_serializer import serialize_example_item


@override_settings(ALLOWED_HOSTS=["*"])
class SyncContractTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            username="sync-admin", password="sync-admin-pass123"
        )
        self.client.force_login(self.user)
        self.url = "/api/v1/sync/"

    def _push(self, operations):
        return self.client.post(
            self.url,
            data=json.dumps({"operations": operations}),
            content_type="application/json",
        )

    def _operation(self, kind, payload, operation_id=None):
        return {
            "operation_id": str(operation_id or uuid.uuid4()),
            "kind": kind,
            "payload": payload,
        }

    def test_create_operation_is_applied_once_and_replayed(self):
        operation = self._operation(
            "example.item.create",
            {"data": {"name": "العنصر", "code": "SYNC-1", "quantity": 3}},
        )

        first = self._push([operation]).json()["data"]["results"][0]
        second = self._push([operation]).json()["data"]["results"][0]

        self.assertEqual(first["status"], "applied")
        self.assertFalse(first["replayed"])
        self.assertEqual(second["data"], first["data"])
        self.assertTrue(second["replayed"])
        self.assertEqual(ExampleItem.objects.filter(code="SYNC-1").count(), 1)
        self.assertEqual(SyncOperation.objects.count(), 1)

    def test_operation_result_is_not_disclosed_to_another_user(self):
        operation = self._operation(
            "example.item.create",
            {"data": {"name": "عنصر", "code": "SYNC-2"}},
        )
        self._push([operation])
        other = get_user_model().objects.create_superuser(
            username="other-admin", password="other-admin-pass123"
        )
        self.client.force_login(other)

        result = self._push([operation]).json()["data"]["results"][0]

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["code"], "operation_not_yours")
        self.assertNotIn("data", result)
        self.assertEqual(ExampleItem.objects.filter(code="SYNC-2").count(), 1)

    def test_unknown_operation_is_durably_rejected(self):
        operation = self._operation("not.registered", {})

        first = self._push([operation]).json()["data"]["results"][0]
        second = self._push([operation]).json()["data"]["results"][0]

        self.assertEqual(first["status"], "rejected")
        self.assertTrue(second["replayed"])
        self.assertEqual(first["error"], second["error"])
        self.assertEqual(SyncOperation.objects.count(), 1)

    def test_stale_update_persists_conflict_evidence(self):
        item = ExampleItem.objects.create(name="قديم", code="SYNC-3")
        operation = self._operation(
            "example.item.update",
            {
                "id": item.pk,
                "base_updated_at": (timezone.now() - timedelta(days=1)).isoformat(),
                "data": {"name": "تعديل الجهاز"},
            },
        )

        result = self._push([operation]).json()["data"]["results"][0]

        item.refresh_from_db()
        self.assertEqual(result["status"], "conflict")
        self.assertEqual(item.name, "قديم")
        self.assertEqual(SyncConflict.objects.count(), 1)
        self.assertEqual(SyncConflict.objects.get().object_pk, str(item.pk))

    def test_pull_returns_registered_rows_and_delete_tombstones(self):
        item = ExampleItem.objects.create(name="للمزامنة", code="SYNC-4")
        initial = self.client.get(
            self.url, {"models": "example.item"}
        ).json()["data"]
        self.assertEqual(initial["rows"]["example.item"][0]["id"], item.pk)

        deletion = self._operation(
            "example.item.delete", {"id": item.pk}
        )
        result = self._push([deletion]).json()["data"]["results"][0]
        self.assertEqual(result["status"], "applied")
        self.assertFalse(ExampleItem.objects.filter(pk=item.pk).exists())
        self.assertTrue(SyncTombstone.objects.filter(object_pk=str(item.pk)).exists())

        pulled = self.client.get(
            self.url,
            {
                "models": "example.item",
                "since": (timezone.now() - timedelta(seconds=1)).isoformat(),
            },
        ).json()["data"]
        self.assertEqual(pulled["tombstones"][0]["id"], str(item.pk))

    def test_sync_route_is_single_and_rejects_non_object_json(self):
        response = self.client.post(
            self.url, data="[]", content_type="application/json"
        )
        old_route = self.client.post("/api/v1/sync/push/")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(old_route.status_code, 404)

    def test_registered_queryset_and_scope_hide_other_tenant_data(self):
        user_model = get_user_model()
        other = user_model.objects.create_superuser(
            username="tenant-admin", password="tenant-admin-pass123"
        )
        own_item = ExampleItem.objects.create(
            name=f"visible-{self.user.pk}", code="SCOPE-OWN"
        )
        ExampleItem.objects.create(
            name=f"visible-{other.pk}", code="SCOPE-OTHER"
        )
        SyncTombstone.objects.create(
            model_label="example.item",
            object_pk="own-deletion",
            scope_key=str(self.user.pk),
        )
        SyncTombstone.objects.create(
            model_label="example.item",
            object_pk="other-deletion",
            scope_key=str(other.pk),
        )
        original = sync_collections()["example.item"]
        register_sync_collection(
            "example.item",
            model=ExampleItem,
            serializer=serialize_example_item,
            permission="example_view",
            model_label="example.item",
            queryset=lambda user: ExampleItem.objects.filter(
                name=f"visible-{user.pk}"
            ),
            scope_key=lambda user: str(user.pk),
        )
        try:
            result = self.client.get(
                self.url, {"models": "example.item"}
            ).json()["data"]
        finally:
            register_sync_collection(
                "example.item",
                model=original.model,
                serializer=original.serializer,
                permission=original.permission,
                model_label=original.model_label,
                queryset=original.queryset,
                scope_key=original.scope_key,
            )

        self.assertEqual(
            [row["id"] for row in result["rows"]["example.item"]],
            [own_item.pk],
        )
        self.assertEqual(
            [item["id"] for item in result["tombstones"]],
            ["own-deletion"],
        )

