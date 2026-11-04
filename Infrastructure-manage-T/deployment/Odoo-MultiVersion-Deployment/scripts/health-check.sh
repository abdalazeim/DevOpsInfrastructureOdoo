#!/bin/bash
# ==============================================================================
# Odoo Multi-Version Deployment - Health Check Script
# يفحص صحة حاويات Odoo و PostgreSQL لنسخة معينة
# ==============================================================================
set -euo pipefail

INSTANCE="${1:-instance1}"
ODOO_PORT="${2:-8069}"
CHAT_PORT="${3:-8072}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }

echo "فحص صحة النسخة: ${INSTANCE}"

# Determine container prefix based on instance name
if echo "${INSTANCE}" | grep -q "odoo19"; then
    PREFIX="odoo19"
elif echo "${INSTANCE}" | grep -q "odoo17"; then
    PREFIX="odoo17"
else
    # Default: check both odoo17 and odoo19 containers matching instance
    PREFIX="${INSTANCE}"
fi

ODOO_CONTAINER="${PREFIX}-${INSTANCE}"
DB_CONTAINER="${PREFIX}-${INSTANCE}-db"

# Check if instance name itself matches container pattern
if [ "${ODOO_CONTAINER}" != "${INSTANCE}" ]; then
    # Try to find container matching the instance name directly
    if docker ps --format '{{.Names}}' | grep -q "^${INSTANCE}$"; then
        ODOO_CONTAINER="${INSTANCE}"
    fi
fi

echo "الحاوية: ${ODOO_CONTAINER}"
echo "حاوية DB: ${DB_CONTAINER}"

# Check Odoo container
if docker ps --format '{{.Names}}' | grep -q "^${ODOO_CONTAINER}$"; then
    STATUS=$(docker inspect --format='{{.State.Status}}' "${ODOO_CONTAINER}" 2>/dev/null || echo "unknown")
    if [ "${STATUS}" = "running" ]; then
        print_success "Odoo container تعمل: ${ODOO_CONTAINER} (${STATUS})"
    else
        print_error "Odoo container غير عاملة: ${ODOO_CONTAINER} (${STATUS})"
        exit 1
    fi
else
    print_error "Odoo container غير موجودة: ${ODOO_CONTAINER}"
    exit 1
fi

# Check DB container
if docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    DB_STATUS=$(docker inspect --format='{{.State.Status}}' "${DB_CONTAINER}" 2>/dev/null || echo "unknown")
    if [ "${DB_STATUS}" = "running" ]; then
        print_success "DB container تعمل: ${DB_CONTAINER} (${DB_STATUS})"
    else
        print_error "DB container غير عاملة: ${DB_CONTAINER} (${DB_STATUS})"
        exit 1
    fi
else
    print_error "DB container غير موجودة: ${DB_CONTAINER}"
    exit 1
fi

# Check PostgreSQL readiness
if docker exec "${DB_CONTAINER}" pg_isready -U odoo -h localhost >/dev/null 2>&1; then
    print_success "PostgreSQL يستجيب"
else
    print_warning "PostgreSQL لا يستجيب (قد يكون لا يزال يبدأ)"
fi

# Check Odoo HTTP health
if curl -sf "http://localhost:${ODOO_PORT}/web/database/selector" >/dev/null 2>&1 || \
   curl -sf "http://127.0.0.1:${ODOO_PORT}/web/database/selector" >/dev/null 2>&1; then
    print_success "Odoo HTTP يستجيب على المنفذ ${ODOO_PORT}"
else
    print_warning "Odoo HTTP لا يستجيب على المنفذ ${ODOO_PORT} (قد يكون لا يزال يبدأ)"
fi

echo ""
print_success "انتهت الفحوصات للنسخة: ${INSTANCE}"
exit 0