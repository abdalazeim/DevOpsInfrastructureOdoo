#!/bin/sh
# ==============================================================================
# Odoo 17 Multi-Instance Entry Point Wrapper
# يبدأ تشغيل أودو بعد التأكد من توفر قاعدة بيانات PostgreSQL
# يستخدمه كل من Jenkins Pipeline و Terminal Script بشكل موحد
# ==============================================================================
set -eu

: "${HOST:=db}"
: "${PORT:=5432}"
: "${USER:=odoo}"
: "${PASSWORD:=}"
: "${ODOO_RC:=/etc/odoo/odoo.conf}"

# تثبيت متطلبات بايثون الإضافية إذا كانت موجودة
if [ -f /etc/odoo/requirements.txt ]; then
    pip3 install --no-cache-dir -r /etc/odoo/requirements.txt || true
fi

# انتظار قاعدة بيانات PostgreSQL حتى تصبح جاهزة
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

# تشغيل أودو مع الإعدادات المحددة
exec odoo --config="${ODOO_RC}" "$@"