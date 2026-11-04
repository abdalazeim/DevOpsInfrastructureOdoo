#!/bin/bash
# ==============================================================================
# Odoo 19 Multi-Instance Health Check Script
# يفحص صحة نسختي Odoo 19 وقواعد بيانات PostgreSQL
# يستخدم من قبل كل من Jenkins و Terminal
# ==============================================================================
set -euo pipefail

INSTANCE_NAME="${1:?اسم النسخة مطلوب (instance1 أو instance2)}"
ODOO_PORT="${2:-10019}"
CHAT_PORT="${3:-20019}"
ODOO_CONTAINER="odoo19-${INSTANCE_NAME}"
DB_CONTAINER="odoo19-${INSTANCE_NAME}-db"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo " فحص صحة النسخة: ${INSTANCE_NAME}"
echo "=========================================="

# فحص وجود الحاويات
if ! docker ps -a --format '{{.Names}}' | grep -q "^${ODOO_CONTAINER}$"; then
    echo -e "${RED}[FAIL]${NC} حاوية أودو غير موجودة: ${ODOO_CONTAINER}"
    exit 1
fi

if ! docker ps -a --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    echo -e "${RED}[FAIL]${NC} حاوية قاعدة البيانات غير موجودة: ${DB_CONTAINER}"
    exit 1
fi

# فحص حالة حاوية أودو
ODOO_STATUS=$(docker inspect --format='{{.State.Status}}' "${ODOO_CONTAINER}" 2>/dev/null || echo "unknown")
if [ "${ODOO_STATUS}" = "running" ]; then
    echo -e "${GREEN}[OK]${NC} حاوية أودو تعمل: ${ODOO_CONTAINER} (${ODOO_STATUS})"
else
    echo -e "${RED}[FAIL]${NC} حاوية أودو غير عاملة: ${ODOO_CONTAINER} (${ODOO_STATUS})"
    exit 1
fi

# فحص حالة حاوية قاعدة البيانات
DB_STATUS=$(docker inspect --format='{{.State.Status}}' "${DB_CONTAINER}" 2>/dev/null || echo "unknown")
if [ "${DB_STATUS}" = "running" ]; then
    echo -e "${GREEN}[OK]${NC} حاوية قاعدة البيانات تعمل: ${DB_CONTAINER} (${DB_STATUS})"
else
    echo -e "${RED}[FAIL]${NC} حاوية قاعدة البيانات غير عاملة: ${DB_CONTAINER} (${DB_STATUS})"
    exit 1
fi

# فحص الاتصال بقاعدة بيانات PostgreSQL 18
if docker exec "${DB_CONTAINER}" pg_isready -U odoo -h localhost >/dev/null 2>&1; then
    echo -e "${GREEN}[OK]${NC} قاعدة بيانات PostgreSQL 18 تستجيب للاتصالات"
else
    echo -e "${RED}[FAIL]${NC} قاعدة بيانات PostgreSQL 18 لا تستجيب"
    exit 1
fi

# فحص منافذ أودو الداخلية عبر exec
if docker exec "${ODOO_CONTAINER}" sh -c "command -v nc >/dev/null 2>&1 || command -v netcat >/dev/null 2>&1" 2>/dev/null; then
    if docker exec "${ODOO_CONTAINER}" nc -z localhost 8069 2>/dev/null; then
        echo -e "${GREEN}[OK]${NC} منفذ أودو 8069 مفتوح داخلياً"
    else
        echo -e "${YELLOW}[WARN]${NC} منفذ أودو 8069 غير مفتوح داخلياً"
    fi
fi

if docker exec "${ODOO_CONTAINER}" sh -c "command -v nc >/dev/null 2>&1 || command -v netcat >/dev/null 2>&1" 2>/dev/null; then
    if docker exec "${ODOO_CONTAINER}" nc -z localhost 8072 2>/dev/null; then
        echo -e "${GREEN}[OK]${NC} منفذ الدردشة 8072 مفتوح داخلياً"
    else
        echo -e "${YELLOW}[WARN]${NC} منفذ الدردشة 8072 غير مفتوح داخلياً"
    fi
fi

echo ""
echo -e "${GREEN}✓ اكتمال فحص صحة النسخة: ${INSTANCE_NAME}${NC}"
echo "=========================================="