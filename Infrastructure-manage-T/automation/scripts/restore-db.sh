#!/usr/bin/env bash
# ==============================================================================
# Odoo Infrastructure Manager - Database & Filestore Safe Restore Engine
# Usage: ./restore-db.sh <17|18|19> <backup_file_path> <target_database> [--force]
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
[[ "${TARGET_DB}" =~ ^[a-zA-Z0-9_][a-zA-Z0-9_-]*$ ]] || { echo "Invalid database identifier" >&2; exit 1; }
FORCE_FLAG="${4:-}"

if [[ -z "${VERSION}" || -z "${DUMP_FILE}" || -z "${TARGET_DB}" ]]; then
  log_err "Usage: $0 <17|18|19> <backup_file_path> <target_database> [--force]"
  exit 1
fi

if [[ "${VERSION}" != "17" && "${VERSION}" != "18" && "${VERSION}" != "19" ]]; then
  log_err "Invalid version. Supported: 17, 18, 19"
  exit 1
fi

if [[ ! -f "${DUMP_FILE}" ]]; then
  log_err "Backup file does not exist: ${DUMP_FILE}"
  exit 1
fi

# F12: Verify checksum before any destructive operation
# Derive meta/filestore filenames from dump filename by pattern replacement:
# dump_<DB>_<TS>.sql.gz  ->  meta_<DB>_<TS>.json  /  filestore_<DB>_<TS>.tar.gz
DIRNAME=$(dirname "${DUMP_FILE}")
BASENAME=$(basename "${DUMP_FILE}")
META_FILE="${DIRNAME}/meta_${BASENAME#dump_}"
META_FILE="${META_FILE%.sql.gz}.json"
FILESTORE_FILE="${DIRNAME}/filestore_${BASENAME#dump_}"
FILESTORE_FILE="${FILESTORE_FILE%.sql.gz}.tar.gz"
if [[ -f "${META_FILE}" ]]; then
  log_info "Verifying SHA256 checksum from metadata..."
  EXPECTED_SHA=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sha256"])' "${META_FILE}")
  if [[ ! "${EXPECTED_SHA}" =~ ^[a-fA-F0-9]{64}$ ]]; then
    log_err "Invalid checksum metadata"
    exit 1
  fi
  if [[ -n "${EXPECTED_SHA}" ]]; then
    ACTUAL_SHA=$(sha256sum "${DUMP_FILE}" | awk '{print $1}')
    if [[ "${ACTUAL_SHA}" != "${EXPECTED_SHA}" ]]; then
      log_err "Checksum mismatch! Expected ${EXPECTED_SHA}, got ${ACTUAL_SHA}. Aborting."
      exit 1
    fi
    log_ok "Checksum verified: ${ACTUAL_SHA:0:16}..."
  fi
else
  log_err "Required metadata missing: ${META_FILE}"
  exit 1
fi

# Reject damaged or unsafe archives before touching the database.
if [[ -f "${FILESTORE_FILE}" ]]; then
  python3 - "${FILESTORE_FILE}" "${META_FILE}" <<'PY'
import hashlib, json, pathlib, sys, tarfile
archive, metadata = map(pathlib.Path, sys.argv[1:])
expected = json.loads(metadata.read_text()).get('filestore_sha256')
with archive.open('rb') as stream:
    checksum = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        checksum.update(chunk)
if not expected or checksum.hexdigest() != expected:
    raise SystemExit('Filestore checksum missing/mismatched; legacy backup requires manual review')
with tarfile.open(archive, 'r:gz') as tar:
    roots = set()
    for member in tar.getmembers():
        path = pathlib.PurePosixPath(member.name)
        if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
            raise SystemExit('Unsafe filestore archive')
        if path.parts:
            roots.add(path.parts[0])
    if len(roots) != 1:
        raise SystemExit('Expected a single database directory in filestore archive')
PY
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
EXISTS=$(docker exec "${DB_CONTAINER}" psql -U "${DB_USER}" -tAc "SELECT 1 FROM pg_database WHERE datname='${TARGET_DB}';")

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

# Step 4: Stream restoration with ON_ERROR_STOP (F12: stop on SQL error)
log_info "Restoring SQL dump into '${TARGET_DB}'..."
if [[ "${DUMP_FILE}" == *.gz ]]; then
  gunzip -c "${DUMP_FILE}" | docker exec -i "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${TARGET_DB}" -v ON_ERROR_STOP=1 >/dev/null
else
  docker exec -i "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${TARGET_DB}" -v ON_ERROR_STOP=1 < "${DUMP_FILE}" >/dev/null
fi
log_ok "Database SQL schema and data restored successfully."

# Step 5: Restore companion filestore linked to target DB name (F12/N04: not source name, no nesting)
DIRNAME=$(dirname "${DUMP_FILE}")
FILESTORE_FILE="${DIRNAME}/filestore_${BASENAME#dump_}"
FILESTORE_FILE="${FILESTORE_FILE%.sql.gz}.tar.gz"

if [[ -f "${FILESTORE_FILE}" ]]; then
  log_info "Companion filestore archive detected: $(basename "${FILESTORE_FILE}")"
  # F12: Restore filestore under the TARGET database name, not the source name
  # Extract contents directly so archive's internal DB_NAME dir becomes TARGET_DB contents
  TARGET_FILESTORE_ROOT="${DATA_ROOT}/odoo${VERSION}/data/filestore"
  TARGET_FILESTORE="${TARGET_FILESTORE_ROOT}/${TARGET_DB}"
  mkdir -p "${TARGET_FILESTORE_ROOT}"
  mkdir -p "${TARGET_FILESTORE}"
  # Extract archive (contains source DB dir) into target filestore root, then rename
  TMP_EXTRACT_DIR="${TARGET_FILESTORE_ROOT}/._extract_${TARGET_DB}_$$"
  mkdir -p "${TMP_EXTRACT_DIR}"
  tar -xzf "${FILESTORE_FILE}" -C "${TMP_EXTRACT_DIR}"
  # The archive contains one top-level dir (source DB name); move its contents to TARGET_DB
  EXTRACTED_DIR=$(ls -1 "${TMP_EXTRACT_DIR}" | head -1)
  if [[ -n "${EXTRACTED_DIR}" && -d "${TMP_EXTRACT_DIR}/${EXTRACTED_DIR}" ]]; then
    cp -a "${TMP_EXTRACT_DIR}/${EXTRACTED_DIR}/." "${TARGET_FILESTORE}/"
    rm -rf "${TMP_EXTRACT_DIR}"
    log_ok "Filestore restored to target name: ${TARGET_DB}"
  else
    rm -rf "${TMP_EXTRACT_DIR}"
    log_err "Filestore archive structure unexpected; restore incomplete."
    exit 1
  fi
else
  log_warn "No filestore archive found at ${FILESTORE_FILE}; skipping filestore restore."
fi

# Step 6: Verify restored tables count
TABLE_COUNT=$(docker exec "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${TARGET_DB}" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
log_ok "Verification: Database '${TARGET_DB}' contains ${TABLE_COUNT} public tables."

if [[ "${TABLE_COUNT}" -gt 0 ]]; then
  log_ok "Restore operation completed with status: SUCCESS"
else
  log_err "Restore completed, but no tables were detected in target database. Possible incomplete restore."
  exit 1
fi
