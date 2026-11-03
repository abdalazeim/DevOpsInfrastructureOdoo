"""Tests for the Example module (CRUD + permissions + service)."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.core.models import AuditLog

from ..models import ExampleItem

User = get_user_model()


@override_settings(ALLOWED_HOSTS=["*"])
class ExampleItemModelTests(TestCase):
    def test_create_item(self):
        item = ExampleItem.objects.create(name="عنصر اختبار", code="TST-001")
        self.assertEqual(item.name, "عنصر اختبار")
        self.assertEqual(item.code, "TST-001")
        self.assertTrue(item.is_active)

    def test_code_unique(self):
        ExampleItem.objects.create(name="أ", code="DUP")
        with self.assertRaises(Exception):
            ExampleItem.objects.create(name="ب", code="DUP")

    def test_str(self):
        item = ExampleItem.objects.create(name="اختبار", code="STR-1")
        self.assertIn("STR-1", str(item))


@override_settings(ALLOWED_HOSTS=["*"])
class ExampleApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="admin", password="adminpass123"
        )
        self.client.login(username="admin", password="adminpass123")

    def _url(self, path):
        return "/api/modules/example" + path

    def test_list_empty(self):
        resp = self.client.get(self._url("/items/"))
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["items"], [])

    def test_create_item(self):
        resp = self.client.post(
            self._url("/items/create/"),
            data={"name": "عنصر", "code": "ABC-1", "quantity": 5},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        payload = resp.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["code"], "ABC-1")
        self.assertTrue(ExampleItem.objects.filter(code="ABC-1").exists())
        self.assertTrue(AuditLog.objects.filter(action="create").exists())

    def test_create_duplicate_code(self):
        ExampleItem.objects.create(name="أ", code="DUP-1")
        resp = self.client.post(
            self._url("/items/create/"),
            data={"name": "ب", "code": "DUP-1"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 409)

    def test_create_rejects_invalid_quantity(self):
        resp = self.client.post(
            self._url("/items/create/"),
            data={"name": "Invalid", "code": "INVALID-1", "quantity": -1},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(ExampleItem.objects.filter(code="INVALID-1").exists())

    def test_create_rejects_non_integer_quantity(self):
        resp = self.client.post(
            self._url("/items/create/"),
            data={"name": "Invalid", "code": "INVALID-2", "quantity": "many"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(ExampleItem.objects.filter(code="INVALID-2").exists())

    def test_invalid_page_size_falls_back_to_default(self):
        resp = self.client.get(self._url("/items/?page_size=not-a-number"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["meta"]["page_size"], 20)

    def test_update_item(self):
        item = ExampleItem.objects.create(name="قديم", code="UPD-1")
        resp = self.client.patch(
            self._url(f"/items/{item.pk}/update/"),
            data={"name": "جديد"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.name, "جديد")
        self.assertTrue(AuditLog.objects.filter(action="update").exists())

    def test_delete_item(self):
        item = ExampleItem.objects.create(name="حذف", code="DEL-1")
        resp = self.client.delete(self._url(f"/items/{item.pk}/delete/"))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(ExampleItem.objects.filter(pk=item.pk).exists())
        self.assertTrue(AuditLog.objects.filter(action="delete").exists())

    def test_detail_404(self):
        resp = self.client.get(self._url("/items/999999/"))
        self.assertEqual(resp.status_code, 404)

    def test_permission_denied(self):
        from django.contrib.auth.models import Group

        group = Group.objects.create(name="readonly")
        user = User.objects.create_user(username="viewer", password="viewpass123")
        user.groups.add(group)
        self.client.logout()
        self.client.login(username="viewer", password="viewpass123")
        resp = self.client.post(
            self._url("/items/create/"),
            data={"name": "x", "code": "X-1"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)
