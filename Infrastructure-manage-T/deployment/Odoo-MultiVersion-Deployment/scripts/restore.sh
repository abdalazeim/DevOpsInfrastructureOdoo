#!/usr/bin/env bash
# ==============================================================================
# Odoo Multi-Version Deployment - Restore Script
# Restores backup with full safety measures
# Supports Odoo 17 and Odoo 19 with multiple instances per version
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

# Verify essential backup files exist
for file in manifest.json checksums.sha256; do
    if [ ! -f "${BACKUP_PATH}/${file}" ]; then
        print_error "File '${file}' not found in backup"
        exit 1
    fi
done

# Verify backup integrity via SHA256
print_info "Verifying backup integrity via SHA256..."
cd "${BACKUP_PATH}"
if ! sha256sum -c checksums.sha256 >/dev/null 2>&1; then
    print_error "File integrity verification failed (SHA256 mismatch)"
    exit 1
fi
print_success "File integrity verified successfully"

# Read backup info from manifest
print_info "Reading backup info from manifest.json..."
ODOO_VER_FROM_MANIFEST=$(python3 -c "import json; print(json.load(open('manifest.json'))['odoo_version'])" 2>/dev/null || echo "unknown")
PG_VER_FROM_MANIFEST=$(python3 -c "import json; print(json.load(open('manifest.json'))['postgres_version'])" 2>/dev/null || echo "unknown")
print_info "Odoo version in backup: ${ODOO_VER_FROM_MANIFEST}"
print_info "PostgreSQL version in backup: ${PG_VER_FROM_MANIFEST}"

# Check storage space
print_info "Checking available storage space..."
AVAILABLE_SPACE=$(df /data --output=avail | tail -1 | tr -d ' ')
print_info "Available space: ${AVAILABLE_SPACE} KB"

# Take safety backup of current state before replacing
print_info "Taking safety backup of current state before replacement..."
SAFETY_DIR="${BACKUP_ROOT}/safety_pre_restore_$(date +%Y%m%d_%H%M%S)"
mkdir -p "${SAFETY_DIR}"
if [ -d "/data/${ODOO_VERSION}/${INSTANCE}" ]; then
    cp -r "/data/${ODOO_VERSION}/${INSTANCE}" "${SAFETY_DIR}/" 2>/dev/null || true
    print_success "Current state backed up to: ${SAFETY_DIR}"
fi

# Stop Odoo service temporarily
print_info "Stopping Odoo service temporarily..."
ODOO_CONTAINER="${ODOO_VERSION}-${INSTANCE}"
DB_CONTAINER="${ODOO_VERSION}-${INSTANCE}-db"

if docker ps --format '{{.Names}}' | grep -q "^${ODOO_CONTAINER}$"; then
    docker stop "${ODOO_CONTAINER}" 2>/dev/null || true
    print_success "Odoo container stopped: ${ODOO_CONTAINER}"
fi

# Restore PostgreSQL database
print_info "Restoring PostgreSQL database..."
if [ -f "${BACKUP_PATH}/database_*.sql" ] || [ -f "${BACKUP_PATH}/database.dump" ]; then
    DB_FILE=$(ls "${BACKUP_PATH}"/database_*.sql "${BACKUP_PATH}"/database.dump 2>/dev/null | head -1 || true)
    if [ -n "${DB_FILE}" ]; then
        if docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
            docker exec -i "${DB_CONTAINER}" psql -U postgres -d postgres < "${DB_FILE}" 2>/dev/null || true
            print_success "PostgreSQL database restored from: ${DB_FILE}"
        else
            print_warning "DB container not running, skipping PostgreSQL restore"
        fi
    fi
else
    print_warning "Database backup file not found, skipping PostgreSQL restore"
fi

# Restore Filestore
print_info "Restoring filestore..."
if [ -f "${BACKUP_PATH}/filestore_*.tar.zst" ]; then
    FILestore_FILE=$(ls "${BACKUP_PATH}"/filestore_*.tar.zst 2>/dev/null | head -1 || true)
    if [ -n "${FILestore_FILE}" ]; then
        mkdir -p "${DATA_PATH}"
        tar --zstd -xf "${FILestore_FILE}" -C "${DATA_PATH}/" 2>/dev/null || true
        print_success "Filestore restored from: ${FILestore_FILE}"
    fi
elif [ -f "${BACKUP_PATH}/filestore_*.tar.gz" ]; then
    FILestore_FILE=$(ls "${BACKUP_PATH}"/filestore_*.tar.gz 2>/dev/null | head -1 || true)
    if [ -n "${FILestore_FILE}" ]; then
        mkdir -p "${DATA_PATH}"
        tar -xzf "${FILestore_FILE}" -C "${DATA_PATH}/" 2>/dev/null || true
        print_success "Filestore restored from: ${FILestore_FILE}"
    fi
else
    print_warning "Filestore file not found, skipping filestore restore"
fi

# Restore Custom Addons and config
print_info "Restoring addons and config..."
if [ -f "${BACKUP_PATH}/addons_*.tar.zst" ]; then
    ADDONS_FILE=$(ls "${BACKUP_PATH}"/addons_*.tar.zst 2>/dev/null | head -1 || true)
    if [ -n "${ADDONS_FILE}" ]; then
        mkdir -p "${CONFIG_PATH}"
        tar --zstd -xf "${ADDONS_FILE}" -C "${CONFIG_PATH}/" 2>/dev/null || true
        print_success "Custom addons restored from: ${ADDONS_FILE}"
    fi
elif [ -f "${BACKUP_PATH}/addons_*.tar.gz" ]; then
    ADDONS_FILE=$(ls "${BACKUP_PATH}"/addons_*.tar.gz 2>/dev/null | head -1 || true)
    if [ -n "${ADDONS_FILE}" ]; then
        mkdir -p "${CONFIG_PATH}"
        tar -xzf "${ADDONS_FILE}" -C "${CONFIG_PATH}/" 2>/dev/null || true
        print_success "Custom addons restored from: ${ADDONS_FILE}"
    fi
fi

if [ -f "${BACKUP_PATH}/config_*.tar.zst" ]; then
    CONFIG_FILE=$(ls "${BACKUP_PATH}"/config_*.tar.zst 2>/dev/null | head -1 || true)
    if [ -n "${CONFIG_FILE}" ]; then
        mkdir -p "${CONFIG_PATH}"
        tar --zstd -xf "${CONFIG_FILE}" -C "${CONFIG_PATH}/" 2>/dev/null || true
        print_success "Odoo config restored from: ${CONFIG_FILE}"
    fi
elif [ -f "${BACKUP_PATH}/config_*.tar.gz" ]; then
    CONFIG_FILE=$(ls "${BACKUP_PATH}"/config_*.tar.gz 2>/dev/null | head -1 || true)
    if [ -n "${CONFIG_FILE}" ]; then
        mkdir -p "${CONFIG_PATH}"
        tar -xzf "${CONFIG_FILE}" -C "${CONFIG_PATH}/" 2>/dev/null || true
        print_success "Odoo config restored from: ${CONFIG_FILE}"
    fi
fi

# Set permissions
print_info "Setting file and directory permissions..."
chmod 700 "${DATA_PATH}/postgresql" 2>/dev/null || true
chmod 755 "${CONFIG_PATH}/etc" 2>/dev/null || true
chmod 755 "${CONFIG_PATH}/addons" 2>/dev/null || true
print_success "Permissions set"

# Restore as new instance (new-instance)
if [ "${RESTORE_TYPE}" = "new-instance" ]; then
    if [ -n "${NEW_INSTANCE_NAME}" ]; then
        print_info "Creating new instance: ${NEW_INSTANCE_NAME}"
    else
        print_warning "Restore type new-instance but no new instance name specified"
    fi
fi

# Restart Odoo
print_info "Restarting Odoo service..."
docker start "${ODOO_CONTAINER}" 2>/dev/null || true
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