"""Integration smoke tests for the API (self-contained Django TestCase)."""
import io
import json

from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models import User


class APISmokeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username="smoke_admin",
            email="smoke_admin@localhost",
            password="smoke-pass-123",
        )

    def setUp(self):
        self.client.force_login(self.user)

    def jresp(self, resp):
        return resp.status_code, json.loads(resp.content)

    def test_auth_login(self):
        resp = self.client.post(
            "/api/auth/login",
            data=json.dumps(
                {"username": "smoke_admin", "password": "smoke-pass-123"}
            ),
            content_type="application/json",
        )
        code, data = self.jresp(resp)
        self.assertEqual(code, 200)
        self.assertTrue(data.get("success"))

    def test_dashboard_stats(self):
        code, data = self.jresp(self.client.get("/api/dashboard/stats"))
        self.assertEqual(code, 200)
        payload = data.get("data", data)
        self.assertIn("total_users", payload)

    def test_system_settings_crud(self):
        code, data = self.jresp(self.client.get("/api/settings/system"))
        self.assertEqual(code, 200)
        payload = data.get("data", data)
        self.assertTrue("settings" in data or "settings" in payload)

    def test_example_items_crud(self):
        code, data = self.jresp(self.client.get("/api/modules/example/items/"))
        self.assertEqual(code, 200)

        code, data = self.jresp(
            self.client.post(
                "/api/modules/example/items/create/",
                data=json.dumps(
                    {"name": "Smoke Item", "code": "SMOKE_001", "quantity": 1}
                ),
                content_type="application/json",
            )
        )
        self.assertEqual(code, 201)
        item_id = data["data"]["id"]

        code, data = self.jresp(
            self.client.get(f"/api/modules/example/items/{item_id}/")
        )
        self.assertEqual(code, 200)

        code, data = self.jresp(
            self.client.patch(
                f"/api/modules/example/items/{item_id}/update/",
                data=json.dumps({"name": "Smoke Item Updated"}),
                content_type="application/json",
            )
        )
        self.assertEqual(code, 200)

        code, data = self.jresp(
            self.client.delete(f"/api/modules/example/items/{item_id}/delete/")
        )
        self.assertEqual(code, 200)

    def test_django_system_check(self):
        out = io.StringIO()
        call_command("check", stdout=out, stderr=out)
        self.assertIn("System check identified no issues", out.getvalue())

    def test_all_migrations_applied(self):
        out = io.StringIO()
        call_command("showmigrations", stdout=out)
        unapplied = [
            l.strip() for l in out.getvalue().splitlines() if l.strip().startswith("[ ]")
        ]
        self.assertEqual(unapplied, [], f"Unapplied migrations: {unapplied}")
