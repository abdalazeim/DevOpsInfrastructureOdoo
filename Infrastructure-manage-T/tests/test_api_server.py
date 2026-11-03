"""
Tests for the local JSON API (app/api_server.py).

The HTTP tests bind an ephemeral port on 127.0.0.1 and use only read-only or
dry-run endpoints, so they do not require Docker or a live infrastructure.
"""
import json
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime
from enum import Enum
from http.server import ThreadingHTTPServer

from app.api_server import (
    ApiHandler,
    create_operation,
    list_profiles,
    to_jsonable,
)


class _SampleEnum(str, Enum):
    READY = "READY"


class TestSerialization(unittest.TestCase):
    def test_to_jsonable_handles_enum_datetime_and_containers(self):
        payload = {
            "status": _SampleEnum.READY,
            "at": datetime(2026, 1, 2, 3, 4, 5),
            "items": (_SampleEnum.READY, {"nested": [_SampleEnum.READY]}),
        }
        encoded = to_jsonable(payload)
        self.assertEqual(encoded["status"], "READY")
        self.assertEqual(encoded["at"], "2026-01-02T03:04:05")
        self.assertEqual(encoded["items"][0], "READY")
        self.assertEqual(encoded["items"][1]["nested"][0], "READY")


class TestApiHelpers(unittest.TestCase):
    def test_list_profiles_returns_at_least_one(self):
        profiles = list_profiles()
        self.assertGreaterEqual(len(profiles), 1)
        self.assertTrue(all(getattr(p, "profile_name", None) for p in profiles))

    def test_create_health_operation_is_pending_and_not_executed(self):
        record = create_operation(
            {"category": "health", "execute": False, "dryRun": True},
            "profiles/example.yaml",
        )
        self.assertTrue(record["id"].startswith("op-"))
        self.assertEqual(record["status"], "pending")
        self.assertEqual(record["operation"].category, "health")

    def test_create_backup_operation_uses_version(self):
        record = create_operation(
            {"category": "backup", "version": "18", "dbName": "odoo18_prod", "execute": False},
            "profiles/example.yaml",
        )
        operation = record["operation"]
        self.assertEqual(operation.category, "backup")
        self.assertIn("odoo18", operation.operation_id)
        step_ids = [step.id for step in operation.steps]
        self.assertIn("verify-db-container-running", step_ids)

    def test_create_odoo18_deploy_operation(self):
        record = create_operation(
            {"category": "odoo18", "execute": False, "dryRun": True},
            "profiles/example.yaml",
        )
        operation = record["operation"]
        self.assertEqual(record["status"], "pending")
        self.assertEqual(operation.category, "odoo18")
        self.assertIn("prepare-odoo18-instance", [step.id for step in operation.steps])

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            create_operation({"category": "not-a-real-action"}, "profiles/example.yaml")

    def test_missing_category_raises(self):
        with self.assertRaises(ValueError):
            create_operation({}, "profiles/example.yaml")


class TestApiHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ApiHandler.profile_path = "profiles/example.yaml"
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), ApiHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def _url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def test_health_endpoint(self):
        with urllib.request.urlopen(self._url("/api/health"), timeout=5) as response:
            payload = json.loads(response.read())
        self.assertEqual(response.status, 200)
        self.assertEqual(payload["status"], "ok")

    def test_profiles_endpoint_contains_odoo18(self):
        with urllib.request.urlopen(self._url("/api/profiles"), timeout=5) as response:
            payload = json.loads(response.read())
        self.assertEqual(response.status, 200)
        self.assertIsInstance(payload, list)
        self.assertTrue(any("odoo18" in profile for profile in payload))

    def test_post_health_operation_is_created(self):
        body = json.dumps({"category": "health", "execute": False, "dryRun": True}).encode()
        request = urllib.request.Request(
            self._url("/api/operations"),
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read())
        self.assertEqual(response.status, 201)
        self.assertEqual(payload["status"], "pending")
        operation_id = payload["id"]

        with urllib.request.urlopen(self._url(f"/api/operations/{operation_id}"), timeout=5) as response:
            fetched = json.loads(response.read())
        self.assertEqual(fetched["id"], operation_id)

    def test_unknown_endpoint_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(self._url("/api/does-not-exist"), timeout=5)
        self.assertEqual(context.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
