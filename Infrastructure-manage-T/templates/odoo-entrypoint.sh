#!/bin/sh
# ==============================================================================
# Generic Odoo entrypoint wrapper (used by deployment/odoo17|18|19).
#
# The instance directory is laid out like the Odoo-MultiVersion-Deployment repo:
#   ./etc/odoo.conf   -> /etc/odoo/odoo.conf (rendered by install-odoo.sh)
#   ./addons          -> /mnt/extra-addons
#   ./postgresql      -> PostgreSQL data directory
#
# Compose passes the config path via `command: ["--config=/etc/odoo/odoo.conf"]`.
# ==============================================================================
set -eu

: "${HOST:=db}"
: "${PORT:=5432}"
: "${USER:=odoo}"
: "${PASSWORD:=}"

# Install extra Python requirements if the operator added some.
if [ -f /etc/odoo/requirements.txt ]; then
    pip3 install --no-cache-dir -r /etc/odoo/requirements.txt || true
fi

# Wait briefly for PostgreSQL to accept connections before starting Odoo.
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
