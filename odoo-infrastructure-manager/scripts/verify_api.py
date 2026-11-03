import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django

django.setup()

from django.test import Client

username = os.environ.get("VERIFY_API_USERNAME")
password = os.environ.get("VERIFY_API_PASSWORD")
if not username or not password:
    raise SystemExit("Set VERIFY_API_USERNAME and VERIFY_API_PASSWORD to run the API smoke check.")

c = Client()
r = c.post(
    "/api/v1/auth/token/",
    data=json.dumps({"username": username, "password": password}),
    content_type="application/json",
    HTTP_HOST="localhost",
)
print("login:", r.status_code, r.content.decode()[:120])

if r.status_code != 200:
    raise SystemExit(f"JWT login failed ({r.status_code}); check the supplied credentials.")

payload = r.json()
access_token = payload.get("access") or (payload.get("data") or {}).get("access")
if not access_token:
    raise SystemExit("JWT login response did not include an access token.")
c.defaults["HTTP_AUTHORIZATION"] = f"Bearer {access_token}"

for path in [
    "/api/v1/dashboard/stats",
    "/api/v1/settings/lookups",
    "/api/v1/settings/system",
    "/api/v1/modules/example/items/",
]:
    resp = c.get(path, HTTP_HOST="localhost")
    body = resp.content.decode()
    summary = body[:140].replace("\n", " ")
    print(resp.status_code, path, "->", summary)
