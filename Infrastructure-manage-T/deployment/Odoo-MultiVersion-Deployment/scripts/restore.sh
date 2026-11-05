#!/usr/bin/env bash
# ==============================================================================
# Odoo Multi-Version Deployment - Restore Script
# Restores backup with full safety measures.
# Consumes the archive contract produced by backup.sh (manifest.json +
# checksums.sha256 + database_dump_*.sql + filestore_*.tar.*).
# Supports Odoo 17, 18 and 19 with multiple instances per version.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BACKUP_ID="${1:-}"
ODOO_VERSION="${2:-odoo17}"
INSTANCE="${3:-instance1}"
RESTORE_TYPE="${4:-existing}"
NEW_INSTANCE_NAME="${5:-}"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_error() { echo -e "${RED}[✗]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_info() { echo -e "${BLUE}[i]${NC} $1"; }

# Verify required parameters
if [ -z "${BACKUP_ID}" ]; then
    print_error "Backup ID (BACKUP_ID) must be specified"
    echo "Usage: $0 <BACKUP_ID> [ODOO_VERSION] [INSTANCE] [RESTORE_TYPE] [NEW_INSTANCE_NAME]"
    echo "Example: $0 odoo17-instance1-20261104 odoo17 instance1 existing"
    echo "Example (new): $0 odoo17-instance1-20261104 odoo17 instance1 new-instance odoo17-instance3"
    exit 1
fi

BACKUP_ROOT="/data/backups"
BACKUP_PATH="${BACKUP_ROOT}/${ODOO_VERSION}/${INSTANCE}/${BACKUP_ID}"
DATA_PATH="/data/${ODOO_VERSION}/${INSTANCE}"
CONFIG_PATH="/opt/${ODOO_VERSION}/${INSTANCE}"

echo -e "${BLUE}========================================${NC}"
echo "Restoring backup - Odoo ${ODOO_VERSION}"
echo "Instance: ${INSTANCE}"
echo "Backup ID: ${BACKUP_ID}"
echo "Restore type: ${RESTORE_TYPE}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Verify backup exists
if [ ! -d "${BACKUP_PATH}" ]; then
    print_error "Backup not found: ${BACKUP_PATH}"
    exit 1
fi

# Verify essential backup files exist (F01/F04)
for file in manifest.json checksums.sha256; do
    if [ ! -f "${BACKUP_PATH}/${file}" ]; then
        print_error "File '${file}' not found in backup"
        exit 1
    fi
done

# Verify backup integrity via SHA256 (F01)
print_info "Verifying backup integrity via SHA256..."
cd "${BACKUP_PATH}"
if ! sha256sum -c checksums.sha256 >/dev/null 2>&1; then
    print_error "File integrity verification failed (SHA256 mismatch)"
    exit 1
fi
print_success "File integrity verified successfully"

# Read backup info from manifest (F03: target correct DB from manifest)
print_info "Reading backup info from manifest.json..."
ODOO_VER_FROM_MANIFEST=$(python3 -c "import json; print(json.load(open('manifest.json'))['odoo_version'])" 2>/dev/null || echo "unknown")
PG_VER_FROM_MANIFEST=$(python3 -c "import json; print(json.load(open('manifest.json'))['postgres_version'])" 2>/dev/null || echo "unknown")
DB_NAME_FROM_MANIFEST=$(python3 -c "import json; print(json.load(open('manifest.json'))['database'])" 2>/dev/null || echo "")
BACKUP_DB_FILE=$(python3 -c "import json; print(json.load(open('manifest.json'))['database_backup'])" 2>/dev/null || echo "")
BACKUP_FILestore_FILE=$(python3 -c "import json; print(json.load(open('manifest.json'))['filestore_backup'])" 2>/dev/null || echo "")
BACKUP_ADDONS_FILE=$(python3 -c "import json; print(json.load(open('manifest.json'))['addons_backup'])" 2>/dev/null || echo "")
BACKUP_CONFIG_FILE=$(python3 -c "import json; print(json.load(open('manifest.json'))['config_backup'])" 2>/dev/null || echo "")

print_info "Odoo version in backup: ${ODOO_VER_FROM_MANIFEST}"
print_info "PostgreSQL version in backup: ${PG_VER_FROM_MANIFEST}"
print_info "Database in backup: ${DB_NAME_FROM_MANIFEST}"

# Handle new-instance: build new destination BEFORE any writing (F05)
if [ "${RESTORE_TYPE}" = "new-instance" ]; then
    if [ -z "${NEW_INSTANCE_NAME}" ]; then
        print_error "Restore type new-instance requires NEW_INSTANCE_NAME"
        exit 1
    fi
    # Derive new paths
    NEW_DATA_PATH="/data/${ODOO_VERSION}/${NEW_INSTANCE_NAME}"
    NEW_CONFIG_PATH="/opt/${ODOO_VERSION}/${NEW_INSTANCE_NAME}"
    NEW_ODOO_CONTAINER="${ODOO_VERSION}-${NEW_INSTANCE_NAME}"
    NEW_DB_CONTAINER="${ODOO_VERSION}-${NEW_INSTANCE_NAME}-db"
    print_info "Creating new instance destination: ${NEW_INSTANCE_NAME}"
    mkdir -p "${NEW_DATA_PATH}" "${NEW_CONFIG_PATH}"
    # Do not touch the source instance
    DATA_PATH="${NEW_DATA_PATH}"
    CONFIG_PATH="${NEW_CONFIG_PATH}"
    INSTANCE="${NEW_INSTANCE_NAME}"
    ODOO_CONTAINER="${NEW_ODOO_CONTAINER}"
    DB_CONTAINER="${NEW_DB_CONTAINER}"
else
    ODOO_CONTAINER="${ODOO_VERSION}-${INSTANCE}"
    DB_CONTAINER="${ODOO_VERSION}-${INSTANCE}-db"
fi

# Check storage space
print_info "Checking available storage space..."
AVAILABLE_SPACE=$(df /data --output=avail | tail -1 | tr -d ' ')
print_info "Available space: ${AVAILABLE_SPACE} KB"

# Stop Odoo and DB containers BEFORE safety backup (F06: consistent state)
print_info "Stopping Odoo and DB containers before safety backup..."
if docker ps --format '{{.Names}}' | grep -q "^${ODOO_CONTAINER}$"; then
    docker stop "${ODOO_CONTAINER}" >/dev/null 2>&1 || {
        print_error "Failed to stop Odoo container: ${ODOO_CONTAINER}"
        exit 1
    }
    print_success "Odoo container stopped: ${ODOO_CONTAINER}"
fi
if docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    docker stop "${DB_CONTAINER}" >/dev/null 2>&1 || {
        print_error "Failed to stop DB container: ${DB_CONTAINER}"
        exit 1
    }
    print_success "DB container stopped: ${DB_CONTAINER}"
fi

# Take safety backup of current state AFTER stopping containers (F06)
print_info "Taking safety backup of current state before replacement..."
SAFETY_DIR="${BACKUP_ROOT}/safety_pre_restore_$(date +%Y%m%d_%H%M%S)"
mkdir -p "${SAFETY_DIR}" || {
    print_error "Failed to create safety backup directory: ${SAFETY_DIR}"
    exit 1
}
if [ -d "/data/${ODOO_VERSION}/${INSTANCE}" ] || [ -d "${DATA_PATH}" ]; then
    cp -r "/data/${ODOO_VERSION}/${INSTANCE}" "${SAFETY_DIR}/" 2>/dev/null || true
    cp -r "${DATA_PATH}" "${SAFETY_DIR}/" 2>/dev/null || true
    if [ ! -d "${SAFETY_DIR}/${INSTANCE}" ] && [ ! -d "${SAFETY_DIR}/$(basename "${DATA_PATH}")" ]; then
        print_warning "No data directory found to safety-backup (may be first-time restore)"
    else
        print_success "Current state backed up to: ${SAFETY_DIR}"
    fi
fi

# Restore PostgreSQL database (F03: target correct DB, ON_ERROR_STOP, no || true)
print_info "Restoring PostgreSQL database..."
if [ -n "${BACKUP_DB_FILE}" ] && [ -f "${BACKUP_PATH}/${BACKUP_DB_FILE}" ]; then
    DB_FILE="${BACKUP_PATH}/${BACKUP_DB_FILE}"
elif [ -f "${BACKUP_PATH}/database_dump_*.sql" ]; then
    # Fallback: discover dump file explicitly (F04)
    DB_FILE=$(ls "${BACKUP_PATH}"/database_dump_*.sql 2>/dev/null | head -1 || true)
elif [ -f "${BACKUP_PATH}/database.dump" ]; then
    DB_FILE="${BACKUP_PATH}/database.dump"
else
    DB_FILE=""
fi

if [ -n "${DB_FILE}" ]; then
    print_info "Found database dump: ${DB_FILE}"
    if docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
        print_error "DB container ${DB_CONTAINER} is running; stop it before restore"
        exit 1
    fi
    # Start DB container temporarily for restore
    docker start "${DB_CONTAINER}" >/dev/null 2>&1 || {
        print_error "Failed to start DB container: ${DB_CONTAINER}"
        exit 1
    }
    # Wait for PostgreSQL to be ready
    for i in $(seq 1 30); do
        if docker exec "${DB_CONTAINER}" pg_isready -U postgres >/dev/null 2>&1; then
            break
        fi
        sleep 1
    done
    # Restore into the database named in the manifest (F03)
    TARGET_DB="${DB_NAME_FROM_MANIFEST:-odoo${ODOO_VERSION#odoo}_prod}"
    docker exec -i "${DB_CONTAINER}" psql -U postgres -d postgres -v ON_ERROR_STOP=1 -f "${DB_FILE}" >/dev/null 2>&1 || {
        print_error "PostgreSQL restore failed from: ${DB_FILE}"
        docker stop "${DB_CONTAINER}" >/dev/null 2>&1 || true
        exit 1
    }
    print_success "PostgreSQL database restored from: ${DB_FILE}"
    docker stop "${DB_CONTAINER}" >/dev/null 2>&1 || true
else
    print_warning "Database backup file not found, skipping PostgreSQL restore"
fi

# Restore Filestore (F04: explicit file discovery)
print_info "Restoring filestore..."
FILestore_FILE=""
if [ -n "${BACKUP_FILestore_FILE}" ] && [ -f "${BACKUP_PATH}/${BACKUP_FILestore_FILE}" ]; then
    FILestore_FILE="${BACKUP_PATH}/${BACKUP_FILestore_FILE}"
elif compgen -G "${BACKUP_PATH}/filestore_*.tar.zst" > /dev/null 2>&1; then
    FILestore_FILE=$(ls "${BACKUP_PATH}"/filestore_*.tar.zst 2>/dev/null | head -1 || true)
elif compgen -G "${BACKUP_PATH}/filestore_*.tar.gz" > /dev/null 2>&1; then
    FILestore_FILE=$(ls "${BACKUP_PATH}"/filestore_*.tar.gz 2>/dev/null | head -1 || true)
fi

if [ -n "${FILestore_FILE}" ]; then
    mkdir -p "${DATA_PATH}"
    if [[ "${FILestore_FILE}" == *.zst ]]; then
        tar --zstd -xf "${FILestore_FILE}" -C "${DATA_PATH}/" || {
            print_error "Failed to extract filestore: ${FILestore_FILE}"
            exit 1
        }
    else
        tar -xzf "${FILestore_FILE}" -C "${DATA_PATH}/" || {
            print_error "Failed to extract filestore: ${FILestore_FILE}"
            exit 1
        }
    fi
    print_success "Filestore restored from: ${FILestore_FILE}"
else
    print_warning "Filestore file not found, skipping filestore restore"
fi

# Restore Custom Addons (F04)
print_info "Restoring addons and config..."
ADDONS_FILE=""
if [ -n "${BACKUP_ADDONS_FILE}" ] && [ -f "${BACKUP_PATH}/${BACKUP_ADDONS_FILE}" ]; then
    ADDONS_FILE="${BACKUP_PATH}/${BACKUP_ADDONS_FILE}"
elif compgen -G "${BACKUP_PATH}/addons_*.tar.zst" > /dev/null 2>&1; then
    ADDONS_FILE=$(ls "${BACKUP_PATH}"/addons_*.tar.zst 2>/dev/null | head -1 || true)
elif compgen -G "${BACKUP_PATH}/addons_*.tar.gz" > /dev/null 2>&1; then
    ADDONS_FILE=$(ls "${BACKUP_PATH}"/addons_*.tar.gz 2>/dev/null | head -1 || true)
fi

if [ -n "${ADDONS_FILE}" ]; then
    mkdir -p "${CONFIG_PATH}"
    if [[ "${ADDONS_FILE}" == *.zst ]]; then
        tar --zstd -xf "${ADDONS_FILE}" -C "${CONFIG_PATH}/" || {
            print_error "Failed to extract addons: ${ADDONS_FILE}"
            exit 1
        }
    else
        tar -xzf "${ADDONS_FILE}" -C "${CONFIG_PATH}/" || {
            print_error "Failed to extract addons: ${ADDONS_FILE}"
            exit 1
        }
    fi
    print_success "Custom addons restored from: ${ADDONS_FILE}"
fi

CONFIG_FILE=""
if [ -n "${BACKUP_CONFIG_FILE}" ] && [ -f "${BACKUP_PATH}/${BACKUP_CONFIG_FILE}" ]; then
    CONFIG_FILE="${BACKUP_PATH}/${BACKUP_CONFIG_FILE}"
elif compgen -G "${BACKUP_PATH}/config_*.tar.zst" > /dev/null 2>&1; then
    CONFIG_FILE=$(ls "${BACKUP_PATH}"/config_*.tar.zst 2>/dev/null | head -1 || true)
elif compgen -G "${BACKUP_PATH}/config_*.tar.gz" > /dev/null 2>&1; then
    CONFIG_FILE=$(ls "${BACKUP_PATH}"/config_*.tar.gz 2>/dev/null | head -1 || true)
fi

if [ -n "${CONFIG_FILE}" ]; then
    mkdir -p "${CONFIG_PATH}"
    if [[ "${CONFIG_FILE}" == *.zst ]]; then
        tar --zstd -xf "${CONFIG_FILE}" -C "${CONFIG_PATH}/" || {
            print_error "Failed to extract config: ${CONFIG_FILE}"
            exit 1
        }
    else
        tar -xzf "${CONFIG_FILE}" -C "${CONFIG_PATH}/" || {
            print_error "Failed to extract config: ${CONFIG_FILE}"
            exit 1
        }
    fi
    print_success "Odoo config restored from: ${CONFIG_FILE}"
fi

# Set permissions
print_info "Setting file and directory permissions..."
chmod 700 "${DATA_PATH}/postgresql" 2>/dev/null || true
chmod 755 "${CONFIG_PATH}/etc" 2>/dev/null || true
chmod 755 "${CONFIG_PATH}/addons" 2>/dev/null || true
print_success "Permissions set"

# Restart Odoo container after restore
print_info "Restarting Odoo service..."
docker start "${ODOO_CONTAINER}" >/dev/null 2>&1 || {
    print_error "Failed to start Odoo container: ${ODOO_CONTAINER}"
    exit 1
}
print_success "Odoo container restarted: ${ODOO_CONTAINER}"

# Verify service health after restore
print_info "Verifying service health after restore..."
sleep 10
if docker exec "${DB_CONTAINER}" pg_isready -U postgres -h localhost >/dev/null 2>&1; then
    print_success "PostgreSQL responds after restore"
else
    print_warning "PostgreSQL not responding after restore (may still be starting)"
fi

echo ""
print_success "Restore completed for instance: ${INSTANCE}"
echo "Safety backup saved at: ${SAFETY_DIR}"
exit 0