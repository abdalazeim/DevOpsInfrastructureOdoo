#!/bin/bash
# ==============================================================================
# Odoo 17 Multi-Instance Backup Script
# يقوم بعمل نسخة احتياطية لقواعد بيانات ومجلدات بيانات نسختي Odoo 17
# ==============================================================================
set -euo pipefail

INSTANCE_NAME="${1:?اسم النسخة مطلوب}"
BACKUP_ROOT="${2:-/data/backups/odoo17}"
ODOO_CONTAINER="odoo17-${INSTANCE_NAME}"
DB_CONTAINER="odoo17-${INSTANCE_NAME}-db"
DATA_PATH="${3:-/data/odoo17/${INSTANCE_NAME}}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_ROOT}/${INSTANCE_NAME}"
BACKUP_FILE="${BACKUP_DIR}/odoo17_${INSTANCE_NAME}_${TIMESTAMP}.tar.gz"

mkdir -p "${BACKUP_DIR}"

echo "=========================================="
echo " نسخ احتياطي للنسخة: ${INSTANCE_NAME}"
echo "=========================================="
echo "الوجهة: ${BACKUP_FILE}"
echo ""

# التحقق من وجود الحاويات
if ! docker ps -a --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    echo "خطأ: حاوية قاعدة البيانات غير موجودة: ${DB_CONTAINER}"
    exit 1
fi

# إنشاء نسخة احتياطية لقاعدة بيانات PostgreSQL
echo "جاري إنشاء نسخة احتياطية من قاعدة البيانات..."
DB_DUMP="${BACKUP_DIR}/odoo17_${INSTANCE_NAME}_${TIMESTAMP}_db.sql"
docker exec "${DB_CONTAINER}" pg_dumpall -U odoo > "${DB_DUMP}"
echo -e "✓ نسخة قاعدة البيانات محفوظة: ${DB_DUMP}"

# ضغط مجلد البيانات مع النسخة الاحتياطية لقاعدة البيانات
echo "جاري ضغط مجلد البيانات..."
tar -czf "${BACKUP_FILE}" \
    -C "${DATA_PATH}" postgresql/ \
    "${DB_DUMP}" 2>/dev/null || \
tar -czf "${BACKUP_FILE}" \
    postgresql/ \
    "${DB_DUMP}"

echo -e "✓ نسخة كاملة محفوظة: ${BACKUP_FILE}"

# حذف نسخة قاعدة البيانات المؤقتة
rm -f "${DB_DUMP}"

# الاحتفاظ بآخر 5 نسخ احتياطية فقط
echo "جاري تنظيف النسخ القديمة (الاحتفاظ بآخر 5)..."
ls -1t "${BACKUP_DIR}"/odoo17_${INSTANCE_NAME}_*.tar.gz 2>/dev/null | tail -n +6 | xargs -r rm -f

echo ""
echo -e "✓ اكتمال النسخ الاحتياطي للنسخة: ${INSTANCE_NAME}"
echo "=========================================="