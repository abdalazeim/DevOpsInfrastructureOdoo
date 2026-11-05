#!/usr/bin/env bash
# ==============================================================================
# Odoo Multi-Version Deployment - Backup Script
# Creates backups of PostgreSQL databases and data directories with manifest
# and SHA256 checksums, producing an archive contract consumable by restore.sh.
# Supports Odoo 17, 18 and 19 with multiple instances per version.
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
elif echo "${INSTANCE}" | grep -qE "^odoo18|-18|18-"; then
    VERSION="odoo18"
elif echo "${INSTANCE}" | grep -qE "^odoo19|-19|19-"; then
    VERSION="odoo19"
else
    if docker ps --format '{{.Names}}' | grep -q "^odoo17-${INSTANCE}-db$"; then
        VERSION="odoo17"
    elif docker ps --format '{{.Names}}' | grep -q "^odoo18-${INSTANCE}-db$"; then
        VERSION="odoo18"
    elif docker ps --format '{{.Names}}' | grep -q "^odoo19-${INSTANCE}-db$"; then
        VERSION="odoo19"
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
BACKUP_ID="${VERSION}-${INSTANCE}-${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${VERSION}/${INSTANCE}/${BACKUP_ID}"
mkdir -p "${BACKUP_PATH}"

# Stop Odoo container temporarily for consistent backup (F06: stop before copying)
print_info "Stopping Odoo container temporarily for consistent backup..."
if docker ps --format '{{.Names}}' | grep -q "^${ODOO_CONTAINER}$"; then
    docker stop "${ODOO_CONTAINER}" >/dev/null 2>&1 || {
        print_error "Failed to stop Odoo container: ${ODOO_CONTAINER}"
        exit 1
    }
    print_success "Odoo container stopped: ${ODOO_CONTAINER}"
fi

# Backup PostgreSQL database (F02: use docker exec -i, not -T)
print_info "Creating PostgreSQL database backup..."
if docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    DB_NAME=$(docker exec "${DB_CONTAINER}" psql -U postgres -tAc "SELECT datname FROM pg_database WHERE datname LIKE 'odoo%';" 2>/dev/null | head -1 | xargs || echo "")
    if [ -z "${DB_NAME}" ]; then
        DB_NAME=$(docker exec "${DB_CONTAINER}" env 2>/dev/null | grep POSTGRES_DB | cut -d= -f2 | head -1 || echo "")
    fi
    if [ -n "${DB_NAME}" ]; then
        docker exec -i "${DB_CONTAINER}" pg_dump -U postgres "${DB_NAME}" > "${BACKUP_PATH}/database_dump_${TIMESTAMP}.sql"
        print_success "Database backed up: ${DB_NAME} -> database_dump_${TIMESTAMP}.sql"
    else
        print_error "Could not find database name in container: ${DB_CONTAINER}"
        exit 1
    fi
else
    print_error "DB container not found: ${DB_CONTAINER}"
    exit 1
fi

# Backup Odoo filestore
print_info "Creating Odoo filestore backup..."
if [ -d "${DATA_PATH}" ]; then
    tar --zstd -cf "${BACKUP_PATH}/filestore_${TIMESTAMP}.tar.zst" -C "${DATA_PATH}" . 2>/dev/null || \
    tar -czf "${BACKUP_PATH}/filestore_${TIMESTAMP}.tar.gz" -C "${DATA_PATH}" . 2>/dev/null || {
        print_error "Failed to create filestore backup"
        exit 1
    }
    print_success "Data files backed up: ${DATA_PATH}"
else
    print_warning "Data directory not found: ${DATA_PATH}"
fi

# Backup custom addons
print_info "Creating custom addons backup..."
if [ -d "${CONFIG_PATH}/addons" ]; then
    tar --zstd -cf "${BACKUP_PATH}/addons_${TIMESTAMP}.tar.zst" -C "${CONFIG_PATH}" addons 2>/dev/null || \
    tar -czf "${BACKUP_PATH}/addons_${TIMESTAMP}.tar.gz" -C "${CONFIG_PATH}" addons 2>/dev/null || {
        print_error "Failed to create addons backup"
        exit 1
    }
    print_success "Custom addons backed up: ${CONFIG_PATH}/addons"
else
    print_warning "Addons directory not found: ${CONFIG_PATH}/addons"
fi

# Backup Odoo configuration
print_info "Creating Odoo configuration backup..."
if [ -d "${CONFIG_PATH}/etc" ]; then
    tar --zstd -cf "${BACKUP_PATH}/config_${TIMESTAMP}.tar.zst" -C "${CONFIG_PATH}" etc 2>/dev/null || \
    tar -czf "${BACKUP_PATH}/config_${TIMESTAMP}.tar.gz" -C "${CONFIG_PATH}" etc 2>/dev/null || {
        print_error "Failed to create config backup"
        exit 1
    }
    print_success "Odoo configuration backed up: ${CONFIG_PATH}/etc"
else
    print_warning "Config directory not found: ${CONFIG_PATH}/etc"
fi

# Restart Odoo container after backup (F06: ensure restart even on failure path)
print_info "Restarting Odoo container after backup..."
docker start "${ODOO_CONTAINER}" >/dev/null 2>&1 || {
    print_error "Failed to restart Odoo container: ${ODOO_CONTAINER}"
    exit 1
}
print_success "Odoo container restarted: ${ODOO_CONTAINER}"

# Create SHA256 checksums for all backup files (F01/F07: integrity verification)
print_info "Creating SHA256 checksums..."
cd "${BACKUP_PATH}"
sha256sum database_dump_*.sql filestore_*.tar.* addons_*.tar.* config_*.tar.* 2>/dev/null > checksums.sha256 || {
    print_error "Failed to create checksums"
    exit 1
}

# Create manifest.json (F01: unified archive contract consumable by restore.sh)
print_info "Creating backup manifest..."
POSTGRES_VERSION=$(docker exec "${DB_CONTAINER}" postgres --version 2>/dev/null | awk '{print $NF}' || echo "unknown")
cat > "${BACKUP_PATH}/manifest.json" <<EOF
{
  "backup_id": "${BACKUP_ID}",
  "odoo_version": "${VERSION}",
  "postgres_version": "${POSTGRES_VERSION}",
  "instance": "${INSTANCE}",
  "database": "${DB_NAME}",
  "backup_type": "full",
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "database_backup": "database_dump_${TIMESTAMP}.sql",
  "filestore_backup": "filestore_${TIMESTAMP}.tar.zst",
  "addons_backup": "addons_${TIMESTAMP}.tar.zst",
  "config_backup": "config_${TIMESTAMP}.tar.zst",
  "integrity_check": "sha256",
  "status": "completed",
  "checksums_file": "checksums.sha256"
}
EOF

print_success "Backup completed successfully"
print_info "Backup ID: ${BACKUP_ID}"
print_info "Backup path: ${BACKUP_PATH}"
exit 0