#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
BACKUP_ROOT="${BACKUP_ROOT:-/data/backups}"
args=(restore "${BACKUP_ROOT}/${2:-odoo17}/${3:-instance1}/${1:?Backup ID required}" --root "${BACKUP_ROOT}")
if [[ "${4:-existing}" == new-instance ]]; then
  args+=(--new-instance "${5:?New instance name required}")
  [[ -z "${RESTORE_HTTP_PORT:-}" ]] || args+=(--http-port "${RESTORE_HTTP_PORT}")
  [[ -z "${RESTORE_DOMAIN:-}" ]] || args+=(--domain "${RESTORE_DOMAIN}")
elif [[ "${4:-existing}" == existing ]]; then
  [[ "${CONFIRM_RESTORE:-}" == yes ]] || { echo "Set CONFIRM_RESTORE=yes after reviewing replacement" >&2; exit 1; }
  args+=(--confirm-replace)
elif [[ "${4:-existing}" != existing ]]; then
  echo "Invalid restore type" >&2; exit 1
fi
exec python3 "${PROJECT_ROOT}/app/services/instance_backup.py" "${args[@]}"
