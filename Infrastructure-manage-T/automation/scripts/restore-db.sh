#!/usr/bin/env bash
# ==============================================================================
# Odoo Infrastructure Manager - Database & Filestore Safe Restore Engine
# Usage: ./restore-db.sh <17|19> <backup_file_path> <target_database> [--force]
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

log_info() { echo -e "\033[0;34m[INFO]\033[0m $*"; }
log_ok()   { echo -e "\033[0;32m[OK]\033[0m $*"; }
log_warn() { echo -e "\033[0;33m[WARN]\033[0m $*"; }
log_err()  { echo -e "\033[0;31m[ERROR]\033[0m $*" >&2; }

trap 'log_err "Restore operation aborted at line ${LINENO}"' ERR

VERSION="${1:-}"
DUMP_FILE="${2:-}"
TARGET_DB="${3:-}"
FORCE_FLAG="${4:-}"

if [[ -z "${VERSION}" || -z "${DUMP_FILE}" || -z "${TARGET_DB}" ]]; then
  log_err "Usage: $0 <17|19> <backup_file_path> <target_database> [--force]"
  exit 1
fi

if [[ ! -f "${DUMP_FILE}" ]]; then
  log_err "Backup file does not exist: ${DUMP_FILE}"
  exit 1
fi

DB_CONTAINER="odoo${VERSION}-db"
ODOO_CONTAINER="odoo${VERSION}"
DB_USER="${POSTGRES_USER:-odoo}"
DATA_ROOT="${ODOO_DATA_ROOT:-/opt/odoo-infrastructure}"

# Verify DB container
if ! docker inspect --format='{{.State.Status}}' "${DB_CONTAINER}" 2>/dev/null | grep -q "running"; then
  log_err "Database container ${DB_CONTAINER} is not running!"
  exit 1
fi

# Pre-restore safety check: Does target DB exist?
EXISTS=$(docker exec "${DB_CONTAINER}" psql -U "${DB_USER}" -tAc "SELECT 1 FROM pg_database WHERE datname='${TARGET_DB}';" || true)

if [[ "${EXISTS}" == "1" ]]; then
  log_warn "Target database '${TARGET_DB}' already exists!"
  if [[ "${FORCE_FLAG}" != "--force" ]]; then
    log_err "Explicit safety flag '--force' required to overwrite existing database '${TARGET_DB}'."
    exit 2
  fi
  
  # Step 1: Pre-restore Safety Backup
  SAFETY_BACKUP_DIR="${DATA_ROOT}/backups/safety_pre_restore"
  mkdir -p "${SAFETY_BACKUP_DIR}"
  SAFETY_FILE="${SAFETY_BACKUP_DIR}/safety_${TARGET_DB}_$(date +%Y%m%d_%H%M%S).sql.gz"
  log_info "Creating automated pre-restore safety backup to: ${SAFETY_FILE}..."
  docker exec "${DB_CONTAINER}" pg_dump -U "${DB_USER}" -d "${TARGET_DB}" --clean | gzip > "${SAFETY_FILE}"
  log_ok "Safety backup preserved."

  # Step 2: Terminate active connections to target DB
  log_info "Terminating active connections to '${TARGET_DB}'..."
  docker exec "${DB_CONTAINER}" psql -U "${DB_USER}" -c "
    SELECT pg_terminate_backend(pid) 
    FROM pg_stat_activity 
    WHERE datname = '${TARGET_DB}' AND pid <> pg_backend_pid();" >/dev/null 2>&1 || true
    
  log_info "Dropping existing database '${TARGET_DB}'..."
  docker exec "${DB_CONTAINER}" dropdb -U "${DB_USER}" --if-exists "${TARGET_DB}"
fi

# Step 3: Create fresh target database
log_info "Creating database '${TARGET_DB}' with UTF-8 encoding..."
docker exec "${DB_CONTAINER}" createdb -U "${DB_USER}" -E UTF8 "${TARGET_DB}"

# Step 4: Stream restoration
log_info "Restoring SQL dump into '${TARGET_DB}'..."
if [[ "${DUMP_FILE}" == *.gz ]]; then
  gunzip -c "${DUMP_FILE}" | docker exec -i "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${TARGET_DB}" >/dev/null
else
  docker exec -i "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${TARGET_DB}" < "${DUMP_FILE}" >/dev/null
fi
log_ok "Database SQL schema and data restored successfully."

# Step 5: Check for companion filestore archive
DIRNAME=$(dirname "${DUMP_FILE}")
FILENAME=$(basename "${DUMP_FILE}")
FILESTORE_CANDIDATE="${DIRNAME}/${FILENAME/dump_/filestore_}"
FILESTORE_CANDIDATE="${FILESTORE_CANDIDATE%.sql.gz}.tar.gz"

if [[ -f "${FILESTORE_CANDIDATE}" ]]; then
  log_info "Companion filestore archive detected: $(basename "${FILESTORE_CANDIDATE}")"
  TARGET_FILESTORE="${DATA_ROOT}/odoo${VERSION}/data/filestore/${TARGET_DB}"
  mkdir -p "${TARGET_FILESTORE}"
  tar -xzf "${FILESTORE_CANDIDATE}" -C "${DATA_ROOT}/odoo${VERSION}/data/filestore"
  log_ok "Filestore restored successfully."
fi

# Step 6: Verify restored tables count
TABLE_COUNT=$(docker exec "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${TARGET_DB}" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
log_ok "Verification: Database '${TARGET_DB}' contains ${TABLE_COUNT} public tables."

if [[ "${TABLE_COUNT}" -gt 0 ]]; then
  log_ok "Restore operation completed with status: SUCCESS"
else
  log_warn "Restore completed, but no tables were detected in target database."
fi
