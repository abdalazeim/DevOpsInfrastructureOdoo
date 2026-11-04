#!/bin/bash
# ==============================================================================
# Odoo Multi-Version Deployment - Backup Script
# ينشئ نسخًا احتياطية لقواعد بيانات PostgreSQL ومجلدات البيانات
# يدعم Odoo 17 و Odoo 19 مع نسخ متعددة لكل إصدار
# ==============================================================================
set -euo pipefail

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
    # Default: check running containers to determine version
    if docker ps --format '{{.Names}}' | grep -q "^odoo17-${INSTANCE}-db$"; then
        VERSION="odoo17"
    elif docker ps --format '{{.Names}}' | grep -q "^odoo19-${INSTANCE}-db$"; then
        VERSION="odoo19"
    elif docker ps --format '{{.Names}}' | grep -q "^odoo18-${INSTANCE}-db$"; then
        VERSION="odoo18"
    else
        print_error "لا يمكن تحديد إصدار Odoo للنسخة: ${INSTANCE}"
        print_info "الاستخدام: $0 <INSTANCE> [ODOO_VERSION] [BACKUP_DIR]"
        print_info "مثال: $0 instance1 odoo17 /data/backups"
        exit 1
    fi
fi

ODOO_CONTAINER="${VERSION}-${INSTANCE}"
DB_CONTAINER="${VERSION}-${INSTANCE}-db"
DATA_PATH="/data/${VERSION}/${INSTANCE}"
CONFIG_PATH="/opt/${VERSION}/${INSTANCE}"

print_info "الإصدار المحدد: ${VERSION}"
print_info "حاوية Odoo: ${ODOO_CONTAINER}"
print_info "حاوية DB: ${DB_CONTAINER}"
print_info "مسار البيانات: ${DATA_PATH}"
print_info "مسار الإعدادات: ${CONFIG_PATH}"

mkdir -p "${BACKUP_DIR}/${VERSION}/${INSTANCE}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup PostgreSQL database
print_info "إنشاء نسخة احتياطية لقاعدة بيانات PostgreSQL..."
if docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    # Get database name from environment or list
    DB_NAME=$(docker exec "${DB_CONTAINER}" psql -U postgres -tAc "SELECT datname FROM pg_database WHERE datname LIKE 'odoo%';" 2>/dev/null | head -1 | xargs || echo "")
    if [ -z "${DB_NAME}" ]; then
        # Try to get from container env
        DB_NAME=$(docker exec "${DB_CONTAINER}" env 2>/dev/null | grep POSTGRES_DB | cut -d= -f2 | head -1 || echo "")
    fi
    if [ -n "${DB_NAME}" ]; then
        docker exec -T "${DB_CONTAINER}" pg_dump -U postgres "${DB_NAME}" > "${BACKUP_DIR}/${VERSION}/${INSTANCE}/database_${TIMESTAMP}.sql"
        print_success "تم نسخ قاعدة البيانات: ${DB_NAME}"
    else
        print_warning "لم يتم العثور على اسم قاعدة بيانات في حاوية: ${DB_CONTAINER}"
    fi
else
    print_error "حاوية DB غير موجودة: ${DB_CONTAINER}"
    exit 1
fi

# Backup Odoo filestore
print_info "إنشاء نسخة احتياطية لملفات Odoo (filestore)..."
if [ -d "${DATA_PATH}" ]; then
    tar --zstd -cf "${BACKUP_DIR}/${VERSION}/${INSTANCE}/filestore_${TIMESTAMP}.tar.zst" -C "${DATA_PATH}" . 2>/dev/null || \
    tar -czf "${BACKUP_DIR}/${VERSION}/${INSTANCE}/filestore_${TIMESTAMP}.tar.gz" -C "${DATA_PATH}" . 2>/dev/null || true
    print_success "تم نسخ ملفات البيانات: ${DATA_PATH}"
else
    print_warning "مجلد البيانات غير موجود: ${DATA_PATH}"
fi

# Backup custom addons
print_info "إنشاء نسخة احتياطية للإضافات المخصصة..."
if [ -d "${CONFIG_PATH}/addons" ]; then
    tar --zstd -cf "${BACKUP_DIR}/${VERSION}/${INSTANCE}/addons_${TIMESTAMP}.tar.zst" -C "${CONFIG_PATH}" addons 2>/dev/null || \
    tar -czf "${BACKUP_DIR}/${VERSION}/${INSTANCE}/addons_${TIMESTAMP}.tar.gz" -C "${CONFIG_PATH}" addons 2>/dev/null || true
    print_success "تم نسخ الإضافات المخصصة: ${CONFIG_PATH}/addons"
else
    print_warning "مجلد الإضافات غير موجود: ${CONFIG_PATH}/addons"
fi

# Backup Odoo configuration
print_info "إنشاء نسخة احتياطية لإعدادات Odoo..."
if [ -d "${CONFIG_PATH}/etc" ]; then
    tar --zstd -cf "${BACKUP_DIR}/${VERSION}/${INSTANCE}/config_${TIMESTAMP}.tar.zst" -C "${CONFIG_PATH}" etc 2>/dev/null || \
    tar -czf "${BACKUP_DIR}/${VERSION}/${INSTANCE}/config_${TIMESTAMP}.tar.gz" -C "${CONFIG_PATH}" etc 2>/dev/null || true
    print_success "تم نسخ إعدادات Odoo: ${CONFIG_PATH}/etc"
else
    print_warning "مجلد الإعدادات غير موجود: ${CONFIG_PATH}/etc"
fi

# List backups
print_info "النسخ الاحتياطية المتاحة:"
ls -lh "${BACKUP_DIR}/${VERSION}/${INSTANCE}/" 2>/dev/null || true

echo ""
print_success "اكتملت النسخة الاحتياطية للنسخة: ${INSTANCE} (الإصدار: ${VERSION})"
exit 0