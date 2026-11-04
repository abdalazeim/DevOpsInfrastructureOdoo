#!/bin/sh
# ==============================================================================
# Odoo 17 Private Repository - Generic Entrypoint Wrapper
#
# يستمد الأفكار من Odoo-MultiVersion-Deployment مع تحسينات للأمان والتوافق.
# ==============================================================================
set -eu

: "${HOST:=db}"
: "${PORT:=5432}"
: "${USER:=odoo}"
: "${PASSWORD:=}"

# تثبيت متطلبات بايثون الإضافية إذا أضافها المشغل.
if [ -f /etc/odoo/requirements.txt ]; then
    pip3 install --no-cache-dir -r /etc/odoo/requirements.txt || true
fi

# الانتظار حتى تقبل PostgreSQL الاتصالات قبل تشغيل أودو.
if [ -n "${PASSWORD}" ]; then
    python3 - <<'PY' || true
import os
import socket
import time

host = os.environ.get("HOST", "db")
port = int(os.environ.get("PORT", "5432"))
for _ in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            break
    except OSError:
        time.sleep(1)
PY
fi

exec odoo "$@"
