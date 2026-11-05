#!/usr/bin/env bash
# ==============================================================================
# Odoo Infrastructure Manager - Database & Filestore Backup Engine
# Usage: ./backup-db.sh <17|19> [database_name] [retention_count]
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

log_info() { echo -e "\033[0;34m[INFO]\033[0m $*"; }
log_ok()   { echo -e "\033[0;32m[OK]\033[0m $*"; }
log_warn() { echo -e "\033[0;33m[WARN]\033[0m $*"; }
log_err()  { echo -e "\033[0;31m[ERROR]\033[0m $*" >&2; }

trap 'log_err "Backup failed at line ${LINENO}"' ERR

VERSION="${1:-}"
if [[ -z "${VERSION}" || ( "${VERSION}" != "17" && "${VERSION}" != "18" && "${VERSION}" != "19" ) ]]; then
  log_err "Invalid version. Usage: $0 <17|18|19> [database_name] [retention_count]"
  exit 1
fi

DB_CONTAINER="odoo${VERSION}-db"
ODOO_CONTAINER="odoo${VERSION}"
DB_NAME="${2:-odoo${VERSION}_prod}"
RETENTION="${3:-7}"
DATA_ROOT="${ODOO_DATA_ROOT:-/opt/odoo-infrastructure}"
BACKUP_DIR="${DATA_ROOT}/backups/odoo${VERSION}"

mkdir -p "${BACKUP_DIR}"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DUMP_FILE="${BACKUP_DIR}/dump_${DB_NAME}_${TIMESTAMP}.sql.gz"
FILESTORE_FILE="${BACKUP_DIR}/filestore_${DB_NAME}_${TIMESTAMP}.tar.gz"
META_FILE="${BACKUP_DIR}/meta_${DB_NAME}_${TIMESTAMP}.json"

log_info "Initiating safe backup for Odoo ${VERSION} (Database: ${DB_NAME})..."

# Verify DB container is running
if ! docker inspect --format='{{.State.Status}}' "${DB_CONTAINER}" 2>/dev/null | grep -q "running"; then
  log_err "Container ${DB_CONTAINER} is not running! Aborting backup."
  exit 1
fi

# Determine DB user from environment
DB_USER="${POSTGRES_USER:-odoo}"

# Execute pg_dump inside container streamed directly to gzip
log_info "Dumping PostgreSQL database '${DB_NAME}'..."
docker exec "${DB_CONTAINER}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists --no-owner --no-privileges | gzip > "${DUMP_FILE}"

# Verify dump file
if [[ ! -s "${DUMP_FILE}" ]]; then
  log_err "Backup file is empty or was not created: ${DUMP_FILE}"
  rm -f "${DUMP_FILE}"
  exit 1
fi
DUMP_SIZE=$(stat -c%s "${DUMP_FILE}" 2>/dev/null || stat -f%z "${DUMP_FILE}" 2>/dev/null || wc -c < "${DUMP_FILE}")
log_ok "Database dump created: $(basename "${DUMP_FILE}") (Size: ${DUMP_SIZE} bytes)"

# Backup filestore if directory exists (F13: explicit host mount + container fallback)
ODOO_DATA_DIR="${DATA_ROOT}/odoo${VERSION}/data/filestore/${DB_NAME}"
FILestore_FOUND=false
if [[ -d "${ODOO_DATA_DIR}" ]]; then
  log_info "Archiving Odoo filestore for '${DB_NAME}' from host path..."
  tar -czf "${FILESTORE_FILE}" -C "${DATA_ROOT}/odoo${VERSION}/data/filestore" "${DB_NAME}"
  log_ok "Filestore archived: $(basename "${FILESTORE_FILE}")"
  FILestore_FOUND=true
else
  # F13: Fallback - check container volume for filestore when host mount is unknown
  log_info "Host filestore path not found: ${ODOO_DATA_DIR}; checking container volume..."
  if docker exec "${DB_CONTAINER}" test -d /var/lib/odoo/filestore 2>/dev/null; then
    log_info "Found filestore in container volume at /var/lib/odoo/filestore"
    # Create a temporary archive from container
    docker exec "${DB_CONTAINER}" tar -czf /tmp/filestore_backup.tar.gz -C /var/lib/odoo filestore 2>/dev/null || true
    docker cp "${DB_CONTAINER}:/tmp/filestore_backup.tar.gz" "${FILESTORE_FILE}" 2>/dev/null || true
    docker exec "${DB_CONTAINER}" rm -f /tmp/filestore_backup.tar.gz 2>/dev/null || true
    if [[ -f "${FILESTORE_FILE}" ]]; then
      log_ok "Filestore archived from container: $(basename "${FILESTORE_FILE}")"
      FILestore_FOUND=true
    fi
  fi
fi
if [[ "${FILestore_FOUND}" == "false" ]]; then
  log_warn "Filestore directory not found at ${ODOO_DATA_DIR} or container volume; skipping filestore archive."
fi

# Calculate SHA256 checksum for integrity check
CHECKSUM=$(sha256sum "${DUMP_FILE}" | awk '{print $1}')

# Write metadata
cat <<EOF > "${META_FILE}"
{
  "version": "odoo${VERSION}",
  "database": "${DB_NAME}",
  "timestamp": "${TIMESTAMP}",
  "dump_file": "$(basename "${DUMP_FILE}")",
  "dump_size_bytes": ${DUMP_SIZE},
  "sha256": "${CHECKSUM}",
  "status": "success"
}
EOF

# Retention enforcement: Keep only newest $RETENTION dumps
log_info "Enforcing retention policy (keeping newest ${RETENTION} backups)..."
find "${BACKUP_DIR}" -name "dump_${DB_NAME}_*.sql.gz" -type f | sort -r | tail -n +"$((RETENTION + 1))" | while read -r old_dump; do
  log_warn "Removing expired backup: ${old_dump}"
  rm -f "${old_dump}"
  # Remove associated filestore and meta using correct extensions
  old_basename="$(basename "${old_dump}")"
  old_stem="${old_basename%.sql.gz}"
  old_prefix="${old_stem#dump_}"
  rm -f "${BACKUP_DIR}/filestore_${old_prefix}.tar.gz"
  rm -f "${BACKUP_DIR}/meta_${old_prefix}.json"
done

log_ok "Backup completed successfully! SHA256: ${CHECKSUM:0:16}..."
