import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from django.conf import settings


class SemaphoreError(Exception):
    pass


class SemaphoreClient:
    """Small Semaphore API client: fixed endpoints, bounded timeouts, no shell."""

    def __init__(self):
        self.base_url = settings.SEMAPHORE_URL.rstrip("/")
        self.token = settings.SEMAPHORE_API_TOKEN
        if self.base_url:
            parts = urlsplit(self.base_url)
            local = parts.hostname in {"localhost", "127.0.0.1", "::1"}
            if parts.scheme != "https" and not local:
                raise SemaphoreError("Semaphore must use HTTPS except on localhost.")
            if parts.username or parts.password or parts.query or parts.fragment:
                raise SemaphoreError("Semaphore URL must not contain credentials or query parameters.")

    @property
    def configured(self):
        return bool(self.base_url and self.token)

    def _request(self, path, payload=None):
        if not self.configured:
            raise SemaphoreError("Semaphore is not configured.")
        request = Request(self.base_url + "/api/" + path.lstrip("/"), method="POST" if payload is not None else "GET")
        request.add_header("Authorization", f"Bearer {self.token}")
        request.add_header("Accept", "application/json, text/plain")
        if payload is not None:
            request.add_header("Content-Type", "application/json")
            request.data = json.dumps(payload).encode("utf-8")
        try:
            with urlopen(request, timeout=settings.SEMAPHORE_TIMEOUT_SECONDS) as response:
                body = response.read(1_000_000).decode("utf-8", errors="replace")
                if not body:
                    return None
                try:
                    return json.loads(body)
                except json.JSONDecodeError:
                    return body.strip()
        except HTTPError as exc:
            raise SemaphoreError(f"Semaphore returned HTTP {exc.code}.") from None
        except (URLError, TimeoutError, OSError):
            raise SemaphoreError("Could not reach Semaphore within the configured timeout.") from None

    def ping(self):
        # /api/ping is documented as a public PING endpoint in Semaphore API.
        # Send the configured token as well so proxies can authenticate it.
        if not self.base_url:
            raise SemaphoreError("Semaphore URL is not configured.")
        original = self.token
        if not self.token:
            self.token = ""
            try:
                request = Request(self.base_url + "/api/ping", headers={"Accept": "text/plain"})
                with urlopen(request, timeout=settings.SEMAPHORE_TIMEOUT_SECONDS) as response:
                    return response.status == 200 and response.read(256).decode("utf-8", "replace").strip().lower() == "pong"
            except (HTTPError, URLError, TimeoutError, OSError):
                raise SemaphoreError("Semaphore ping failed.") from None
            finally:
                self.token = original
        response = self._request("ping")
        return str(response).strip().lower() == "pong"

    def start_task(self, project_id, template_id, *, dry_run=True, limit=""):
        payload = {"template_id": int(template_id), "dry_run": bool(dry_run)}
        if limit:
            payload["limit"] = limit
        return self._request(f"project/{int(project_id)}/tasks", payload)

    def list_projects(self):
        return self._list("projects")

    def list_templates(self, project_id):
        return self._list(f"project/{int(project_id)}/templates")

    def _list(self, path):
        result = self._request(path)
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and isinstance(result.get("data"), list):
            return result["data"]
        raise SemaphoreError("Semaphore returned an unexpected catalog response.")

    def get_task(self, project_id, task_id):
        return self._request(f"project/{int(project_id)}/tasks/{int(task_id)}")

    def task_output(self, project_id, task_id):
        return self._request(f"project/{int(project_id)}/tasks/{int(task_id)}/output")
