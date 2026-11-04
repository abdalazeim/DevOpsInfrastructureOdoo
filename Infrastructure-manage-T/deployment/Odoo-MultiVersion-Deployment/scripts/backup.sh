#!/usr/bin/env bash
# ==============================================================================
# Odoo Multi-Version Deployment - Backup Script
# Creates backups of PostgreSQL databases and data directories
# Supports Odoo 17 and Odoo 19 with multiple instances per version
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

INSTANCE="${1:-instance1}"
ODOO_VERSION="${2:-}"
BACKUP_DIR="${3:-/data/backups}"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[i]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }

echo -e "${BLUE}========================================${NC}"
echo "Backup Odoo Instance: ${INSTANCE}"
echo "Time: $(date +%Y%m%d_%H%M%S)"
echo -e "${BLUE}========================================${NC}"

# Determine Odoo version from parameter or instance name
if [ -n "${ODOO_VERSION}" ]; then
    VERSION="${ODOO_VERSION}"
elif echo "${INSTANCE}" | grep -qE "^odoo17|-17|17-"; then
    VERSION="odoo17"
elif echo "${INSTANCE}" | grep -qE "^odoo19|-19|19-"; then
    VERSION="odoo19"
elif echo "${INSTANCE}" | grep -qE "^odoo18|-18|18-"; then
    VERSION="odoo18"
else
    if docker ps --format '{{.Names}}' | grep -q "^odoo17-${INSTANCE}-db$"; then
        VERSION="odoo17"
    elif docker ps --format '{{.Names}}' | grep -q "^odoo19-${INSTANCE}-db$"; then
        VERSION="odoo19"
    elif docker ps --format '{{.Names}}' | grep -q "^odoo18-${INSTANCE}-db$"; then
        VERSION="odoo18"
    else
        print_error "Cannot determine Odoo version for instance: ${INSTANCE}"
        print_info "Usage: $0 <INSTANCE> [ODOO_VERSION] [BACKUP_DIR]"
        print_info "Example: $0 instance1 odoo17 /data/backups"
        exit 1
    fi
fi

ODOO_CONTAINER="${VERSION}-${INSTANCE}"
DB_CONTAINER="${VERSION}-${INSTANCE}-db"
DATA_PATH="/data/${VERSION}/${INSTANCE}"
CONFIG_PATH="/opt/${VERSION}/${INSTANCE}"

print_info "Version selected: ${VERSION}"
print_info "Odoo container: ${ODOO_CONTAINER}"
print_info "DB container: ${DB_CONTAINER}"
print_info "Data path: ${DATA_PATH}"
print_info "Config path: ${CONFIG_PATH}"

mkdir -p "${BACKUP_DIR}/${VERSION}/${INSTANCE}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup PostgreSQL database
print_info "Creating PostgreSQL database backup..."
if docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    DB_NAME=$(docker exec "${DB_CONTAINER}" psql -U postgres -tAc "SELECT datname FROM pg_database WHERE datname LIKE 'odoo%';" 2>/dev/null | head -1 | xargs || echo "")
    if [ -z "${DB_NAME}" ]; then
        DB_NAME=$(docker exec "${DB_CONTAINER}" env 2>/dev/null | grep POSTGRES_DB | cut -d= -f2 | head -1 || echo "")
    fi
    if [ -n "${DB_NAME}" ]; then
        docker exec -T "${DB_CONTAINER}" pg_dump -U postgres "${DB_NAME}" > "${BACKUP_DIR}/${VERSION}/${INSTANCE}/database_${TIMESTAMP}.sql"
        print_success "Database backed up: ${DB_NAME}"
    else
        print_warning "Could not find database name in container: ${DB_CONTAINER}"
    fi
else
    print_error "DB container not found: ${DB_CONTAINER}"
    exit 1
fi

# Backup Odoo filestore
print_info "Creating Odoo filestore backup..."
if [ -d "${DATA_PATH}" ]; then
    tar --zstd -cf "${BACKUP_DIR}/${VERSION}/${INSTANCE}/filestore_${TIMESTAMP}.tar.zst" -C "${DATA_PATH}" . 2>/dev/null || \
    tar -czf "${BACKUP_DIR}/${VERSION}/${INSTANCE}/filestore_${TIMESTAMP}.tar.gz" -C "${DATA_PATH}" . 2>/dev/null || true
    print_success "Data files backed up: ${DATA_PATH}"
else
    print_warning "Data directory not found: ${DATA_PATH}"
fi

# Backup custom addons
print_info "Creating custom addons backup..."
if [ -d "${CONFIG_PATH}/addons" ]; then
    tar --zstd -cf "${BACKUP_DIR}/${VERSION}/${INSTANCE}/addons_${TIMESTAMP}.tar.zst" -C "${CONFIG_PATH}" addons 2>/dev/null || \
    tar -czf "${BACKUP_DIR}/${VERSION}/${INSTANCE}/addons_${TIMESTAMP}.tar.gz" -C "${CONFIG_PATH}" addons 2>/dev/null || true
    print_success "Custom addons backed up: ${CONFIG_PATH}/addons"
else
    print_warning "Addons directory not found: ${CONFIG_PATH}/addons"
fi

# Backup Odoo configuration
print_info "Creating Odoo configuration backup..."
if [ -d "${CONFIG_PATH}/etc" ]; then
    tar --zstd -cf "${BACKUP_DIR}/${VERSION}/${INSTANCE}/config_${TIMESTAMP}.tar.zst" -C "${CONFIG_PATH}" etc 2>/dev/null || \
    tar -czf "${BACKUP_DIR}/${VERSION}/${INSTANCE}/config_${TIMESTAMP}.tar.gz" -C "${CONFIG_PATH}" etc 2>/dev/null || true
    print_success "Odoo configuration backed up: ${CONFIG_PATH}/etc"
else
    print_warning "Config directory not found: ${CONFIG_PATH}/etc"
fi

# List backups
print_info "Available backups:"
ls -lh "${BACKUP_DIR}/${VERSION}/${INSTANCE}/" 2>/dev/null || true

echo ""
print_success "Backup completed for instance: ${INSTANCE} (version: ${VERSION})"
exit 0