#!/bin/bash
# ==============================================================================
# Odoo Multi-Version Deployment - Backup Script
# ينشئ نسخًا احتياطية لقواعد بيانات PostgreSQL ومجلدات البيانات
# ==============================================================================
set -euo pipefail

INSTANCE="${1:-instance1}"
BACKUP_DIR="${2:-/data/backups}"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

print_info() { echo -e "${BLUE}[i]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }

echo -e "${BLUE}========================================${NC}"
echo "Backup Odoo Instance: ${INSTANCE}"
echo "Time: ${TIMESTAMP}"
echo -e "${BLUE}========================================${NC}"

mkdir -p "${BACKUP_DIR}/${INSTANCE}"

# Determine container prefix
if echo "${INSTANCE}" | grep -q "odoo19"; then
    PREFIX="odoo19"
elif echo "${INSTANCE}" | grep -q "odoo17"; then
    PREFIX="odoo17"
else
    PREFIX="${INSTANCE}"
fi

ODOO_CONTAINER="${PREFIX}-${INSTANCE}"
DB_CONTAINER="${PREFIX}-${INSTANCE}-db"

# Backup PostgreSQL database
print_info "إنشاء نسخة احتياطية لقاعدة بيانات PostgreSQL..."
if docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    DB_NAME=$(docker exec "${DB_CONTAINER}" psql -U postgres -tAc "SELECT datname FROM pg_database WHERE datname LIKE 'odoo%';" 2>/dev/null | head -1 | xargs || echo "")
    if [ -n "${DB_NAME}" ]; then
        docker exec "${DB_CONTAINER}" pg_dump -U postgres "${DB_NAME}" > "${BACKUP_DIR}/${INSTANCE}/${DB_NAME}_${TIMESTAMP}.sql"
        print_success "تم نسخ قاعدة البيانات: ${DB_NAME}"
    else
        print_warning "لم يتم العثور على قاعدة بيانات Odoo"
    fi
else
    print_error "حاوية DB غير موجودة: ${DB_CONTAINER}"
    exit 1
fi

# Backup Odoo filestore
print_info "إنشاء نسخة احتياطية لملفات Odoo (filestore)..."
DATA_PATH="/data/${INSTANCE}"
if [ -d "${DATA_PATH}" ]; then
    tar -czf "${BACKUP_DIR}/${INSTANCE}/filestore_${TIMESTAMP}.tar.gz" -C "${DATA_PATH}" . 2>/dev/null || true
    print_success "تم نسخ ملفات البيانات: ${DATA_PATH}"
else
    print_warning "مجلد البيانات غير موجود: ${DATA_PATH}"
fi

# List backups
print_info "النسخ الاحتياطية المتاحة:"
ls -lh "${BACKUP_DIR}/${INSTANCE}/" 2>/dev/null || true

echo ""
print_success "اكتملت النسخة الاحتياطية للنسخة: ${INSTANCE}"
exit 0