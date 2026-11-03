"""Contract tests shared by the web UI and the Flutter template."""

import json

from django.test import TestCase, override_settings

from apps.accounts.models import User


class MobileAPIContractTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = "Contract-pass-123"
        cls.user = User.objects.create_superuser(
            username="mobile_admin",
            email="mobile_admin@localhost",
            password=cls.password,
        )

    def _json(self, response):
        return response.status_code, json.loads(response.content)

    def test_capabilities_lists_example_not_transport_by_default(self):
        code, body = self._json(self.client.get("/api/v1/capabilities/"))
        self.assertEqual(code, 200)
        self.assertTrue(body["success"])
        modules = body["data"]["modules"]
        self.assertIn("example", modules)
        self.assertNotIn("transport", modules)

    def test_jwt_login_refresh_and_me(self):
        code, body = self._json(
            self.client.post(
                "/api/v1/auth/token/",
                data=json.dumps(
                    {"username": "mobile_admin", "password": self.password}
                ),
                content_type="application/json",
            )
        )
        self.assertEqual(code, 200)
        self.assertTrue(body["success"])
        access = body["data"]["access"]
        refresh = body["data"]["refresh"]
        self.assertTrue(access)
        self.assertTrue(refresh)
        self.assertEqual(body["data"]["user"]["username"], "mobile_admin")
        self.assertEqual(body["access"], access)

        me = self.client.get(
            "/api/v1/auth/me",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )
        code, body = self._json(me)
        self.assertEqual(code, 200)
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["user"]["username"], "mobile_admin")

        refresh_resp = self.client.post(
            "/api/v1/auth/token/refresh/",
            data=json.dumps({"refresh": refresh}),
            content_type="application/json",
        )
        code, body = self._json(refresh_resp)
        self.assertEqual(code, 200)
        self.assertTrue(body["success"])
        self.assertTrue(body["data"]["access"])

    def test_example_items_crud_via_jwt(self):
        login = self.client.post(
            "/api/v1/auth/token/",
            data=json.dumps(
                {"username": "mobile_admin", "password": self.password}
            ),
            content_type="application/json",
        )
        access = json.loads(login.content)["data"]["access"]
        headers = {"HTTP_AUTHORIZATION": f"Bearer {access}"}

        created = self.client.post(
            "/api/v1/modules/example/items/create/",
            data=json.dumps(
                {"name": "Record A", "code": "REC-001", "quantity": 2}
            ),
            content_type="application/json",
            **headers,
        )
        code, body = self._json(created)
        self.assertEqual(code, 201)
        item_id = body["data"]["id"]

        listed = self.client.get(
            "/api/v1/modules/example/items/?q=Record",
            **headers,
        )
        code, body = self._json(listed)
        self.assertEqual(code, 200)
        self.assertGreaterEqual(len(body["data"]["items"]), 1)
        self.assertIn("meta", body["data"])

        deleted = self.client.delete(
            f"/api/v1/modules/example/items/{item_id}/delete/",
            **headers,
        )
        self.assertEqual(deleted.status_code, 200)

    def test_unauthenticated_me_is_401(self):
        code, body = self._json(self.client.get("/api/v1/auth/me"))
        self.assertEqual(code, 401)
        self.assertFalse(body["success"])

    @override_settings()
    def test_transport_routes_absent_by_default(self):
        self.client.force_login(self.user)
        response = self.client.get("/api/v1/modules/transport/shipments/")
        self.assertEqual(response.status_code, 404)
