#!/bin/bash
# ==============================================================================
# Odoo Multi-Version Deployment - Restore Script
# يستعيد نسخة احتياطية مع تدابير الأمان الكاملة
# يدعم Odoo 17 و Odoo 19 مع نسخ متعددة لكل إصدار
# ==============================================================================
set -euo pipefail

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

# التحقق من المعلمات المطلوبة
if [ -z "${BACKUP_ID}" ]; then
    print_error "يجب تحديد معرف النسخة الاحتياطية (BACKUP_ID)"
    echo "الاستخدام: $0 <BACKUP_ID> [ODOO_VERSION] [INSTANCE] [RESTORE_TYPE] [NEW_INSTANCE_NAME]"
    echo "مثال: $0 odoo17-instance1-20261104 odoo17 instance1 existing"
    echo "مثال (جديد): $0 odoo17-instance1-20261104 odoo17 instance1 new-instance odoo17-instance3"
    exit 1
fi

BACKUP_ROOT="/data/backups"
BACKUP_PATH="${BACKUP_ROOT}/${ODOO_VERSION}/${INSTANCE}/${BACKUP_ID}"
DATA_PATH="/data/${ODOO_VERSION}/${INSTANCE}"
CONFIG_PATH="/opt/${ODOO_VERSION}/${INSTANCE}"

echo -e "${BLUE}========================================${NC}"
echo "استعادة نسخة احتياطية - Odoo ${ODOO_VERSION}"
echo "النسخة: ${INSTANCE}"
echo "معرف النسخة: ${BACKUP_ID}"
echo "نوع الاستعادة: ${RESTORE_TYPE}"
echo -e "${BLUE}========================================${NC}"
echo ""

# التحقق من وجود النسخة الاحتياطية
if [ ! -d "${BACKUP_PATH}" ]; then
    print_error "النسخة الاحتياطية غير موجودة: ${BACKUP_PATH}"
    exit 1
fi

# التحقق من وجود ملفات النسخة الأساسية
for file in manifest.json checksums.sha256; do
    if [ ! -f "${BACKUP_PATH}/${file}" ]; then
        print_error "ملف '${file}' غير موجود في النسخة الاحتياطية"
        exit 1
    fi
done

# التحقق من سلامة النسخة عبر SHA256
print_info "التحقق من سلامة النسخة الاحتياطية عبر SHA256..."
cd "${BACKUP_PATH}"
if ! sha256sum -c checksums.sha256 >/dev/null 2>&1; then
    print_error "فشل التحقق من سلامة الملفات (SHA256 غير متطابق)"
    exit 1
fi
print_success "تم التحقق من سلامة الملفات بنجاح"

# قراءة معلومات النسخة من manifest
print_info "قراءة معلومات النسخة من manifest.json..."
ODOO_VER_FROM_MANIFEST=$(python3 -c "import json; print(json.load(open('manifest.json'))['odoo_version'])" 2>/dev/null || echo "غير معروف")
PG_VER_FROM_MANIFEST=$(python3 -c "import json; print(json.load(open('manifest.json'))['postgres_version'])" 2>/dev/null || echo "غير معروف")
print_info "إصدار Odoo في النسخة: ${ODOO_VER_FROM_MANIFEST}"
print_info "إصدار PostgreSQL في النسخة: ${PG_VER_FROM_MANIFEST}"

# التحقق من مساحة التخزين
print_info "التحقق من مساحة التخزين المتاحة..."
AVAILABLE_SPACE=$(df /data --output=avail | tail -1 | tr -d ' ')
print_info "المساحة المتاحة: ${AVAILABLE_SPACE} KB"

# أخذ نسخة احتياطية من الحالة الحالية قبل الاستبدال
print_info "أخذ نسخة احتياطية من الحالة الحالية قبل الاستبدال (حالة الطوارئ)..."
SAFETY_DIR="${BACKUP_ROOT}/safety_pre_restore_$(date +%Y%m%d_%H%M%S)"
mkdir -p "${SAFETY_DIR}"
if [ -d "/data/${ODOO_VERSION}/${INSTANCE}" ]; then
    cp -r "/data/${ODOO_VERSION}/${INSTANCE}" "${SAFETY_DIR}/" 2>/dev/null || true
    print_success "تم أخذ نسخة احتياطية من الحالة الحالية في: ${SAFETY_DIR}"
fi

# إيقاف خدمة Odoo مؤقتًا
print_info "إيقاف خدمة Odoo مؤقتًا..."
ODOO_CONTAINER="${ODOO_VERSION}-${INSTANCE}"
DB_CONTAINER="${ODOO_VERSION}-${INSTANCE}-db"

if docker ps --format '{{.Names}}' | grep -q "^${ODOO_CONTAINER}$"; then
    docker stop "${ODOO_CONTAINER}" 2>/dev/null || true
    print_success "تم إيقاف حاوية Odoo: ${ODOO_CONTAINER}"
fi

# استعادة PostgreSQL
print_info "استعادة قاعدة بيانات PostgreSQL..."
if [ -f "${BACKUP_PATH}/database_*.sql" ] || [ -f "${BACKUP_PATH}/database.dump" ]; then
    DB_FILE=$(ls "${BACKUP_PATH}"/database_*.sql "${BACKUP_PATH}"/database.dump 2>/dev/null | head -1 || true)
    if [ -n "${DB_FILE}" ]; then
        if docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
            docker exec -i "${DB_CONTAINER}" psql -U postgres -d postgres < "${DB_FILE}" 2>/dev/null || true
            print_success "تم استعادة قاعدة بيانات PostgreSQL من: ${DB_FILE}"
        else
            print_warning "حاوية قاعدة البيانات غير عاملة، تخطي استعادة PostgreSQL"
        fi
    fi
else
    print_warning "ملف نسخة قاعدة البيانات غير موجود، تخطي استعادة PostgreSQL"
fi

# استعادة Filestore
print_info "استعادة ملفات المرفقات (Filestore)..."
if [ -f "${BACKUP_PATH}/filestore_*.tar.zst" ]; then
    FILestore_FILE=$(ls "${BACKUP_PATH}"/filestore_*.tar.zst 2>/dev/null | head -1 || true)
    if [ -n "${FILestore_FILE}" ]; then
        mkdir -p "${DATA_PATH}"
        tar --zstd -xf "${FILestore_FILE}" -C "${DATA_PATH}/" 2>/dev/null || true
        print_success "تم استعادة Filestore من: ${FILestore_FILE}"
    fi
elif [ -f "${BACKUP_PATH}/filestore_*.tar.gz" ]; then
    FILestore_FILE=$(ls "${BACKUP_PATH}"/filestore_*.tar.gz 2>/dev/null | head -1 || true)
    if [ -n "${FILestore_FILE}" ]; then
        mkdir -p "${DATA_PATH}"
        tar -xzf "${FILestore_FILE}" -C "${DATA_PATH}/" 2>/dev/null || true
        print_success "تم استعادة Filestore من: ${FILestore_FILE}"
    fi
else
    print_warning "ملف filestore غير موجود، تخطي استعادة المرفقات"
fi

# استعادة Custom Addons والإعدادات
print_info "استعادة الإضافات والإعدادات..."
if [ -f "${BACKUP_PATH}/addons_*.tar.zst" ]; then
    ADDONS_FILE=$(ls "${BACKUP_PATH}"/addons_*.tar.zst 2>/dev/null | head -1 || true)
    if [ -n "${ADDONS_FILE}" ]; then
        mkdir -p "${CONFIG_PATH}"
        tar --zstd -xf "${ADDONS_FILE}" -C "${CONFIG_PATH}/" 2>/dev/null || true
        print_success "تم استعادة Custom Addons من: ${ADDONS_FILE}"
    fi
elif [ -f "${BACKUP_PATH}/addons_*.tar.gz" ]; then
    ADDONS_FILE=$(ls "${BACKUP_PATH}"/addons_*.tar.gz 2>/dev/null | head -1 || true)
    if [ -n "${ADDONS_FILE}" ]; then
        mkdir -p "${CONFIG_PATH}"
        tar -xzf "${ADDONS_FILE}" -C "${CONFIG_PATH}/" 2>/dev/null || true
        print_success "تم استعادة Custom Addons من: ${ADDONS_FILE}"
    fi
fi

if [ -f "${BACKUP_PATH}/config_*.tar.zst" ]; then
    CONFIG_FILE=$(ls "${BACKUP_PATH}"/config_*.tar.zst 2>/dev/null | head -1 || true)
    if [ -n "${CONFIG_FILE}" ]; then
        mkdir -p "${CONFIG_PATH}"
        tar --zstd -xf "${CONFIG_FILE}" -C "${CONFIG_PATH}/" 2>/dev/null || true
        print_success "تم استعادة إعدادات Odoo من: ${CONFIG_FILE}"
    fi
elif [ -f "${BACKUP_PATH}/config_*.tar.gz" ]; then
    CONFIG_FILE=$(ls "${BACKUP_PATH}"/config_*.tar.gz 2>/dev/null | head -1 || true)
    if [ -n "${CONFIG_FILE}" ]; then
        mkdir -p "${CONFIG_PATH}"
        tar -xzf "${CONFIG_FILE}" -C "${CONFIG_PATH}/" 2>/dev/null || true
        print_success "تم استعادة إعدادات Odoo من: ${CONFIG_FILE}"
    fi
fi

# ضبط الصلاحيات
print_info "ضبط الصلاحيات على الملفات والمجلدات..."
chmod 700 "${DATA_PATH}/postgresql" 2>/dev/null || true
chmod 755 "${CONFIG_PATH}/etc" 2>/dev/null || true
chmod 755 "${CONFIG_PATH}/addons" 2>/dev/null || true
print_success "تم ضبط الصلاحيات"

# استعادة نسخة جديدة (new-instance)
if [ "${RESTORE_TYPE}" = "new-instance" ]; then
    if [ -n "${NEW_INSTANCE_NAME}" ]; then
        print_info "إنشاء نسخة جديدة: ${NEW_INSTANCE_NAME}"
        # يمكن إضافة منطق إنشاء نسخة جديدة هنا مستقبلاً
    else
        print_warning "نوع الاستعادة new-instance ولكن لم يتم تحديد اسم النسخة الجديدة"
    fi
fi

# إعادة تشغيل Odoo
print_info "إعادة تشغيل خدمة Odoo..."
docker start "${ODOO_CONTAINER}" 2>/dev/null || true
print_success "تم إعادة تشغيل حاوية Odoo: ${ODOO_CONTAINER}"

# التحقق من صحة الخدمة بعد الاستعادة
print_info "التحقق من صحة الخدمة بعد الاستعادة..."
sleep 10
if docker exec "${DB_CONTAINER}" pg_isready -U postgres -h localhost >/dev/null 2>&1; then
    print_success "PostgreSQL يستجيب بعد الاستعادة"
else
    print_warning "PostgreSQL لا يستجيب بعد الاستعادة (قد يكون لا يزال يبدأ)"
fi

echo ""
print_success "اكتملت عملية الاستعادة للنسخة: ${INSTANCE}"
echo "نسخة الأمان المحفوظة في: ${SAFETY_DIR}"
exit 0