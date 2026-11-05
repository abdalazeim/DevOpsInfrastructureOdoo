#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
exec python3 "${PROJECT_ROOT}/app/services/instance_backup.py" backup "${2:?Odoo version required (odoo17/odoo18/odoo19)}" "${1:-instance1}" --root "${3:-/data/backups}"
