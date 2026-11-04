#!/bin/bash
# ==============================================================================
# Odoo Multi-Version Deployment - Verify Backups Script
# يتحقق من سلامة جميع النسخ الاحتياطية وملفات manifest
# ==============================================================================
set -euo pipefail

BACKUP_ROOT="${1:-/data/backups}"
ODOO_VERSION="${2:-all}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_error() { echo -e "${RED}[✗]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_info() { echo -e "${BLUE}[i]${NC} $1"; }

ERRORS=0
TOTAL=0

echo -e "${BLUE}========================================${NC}"
echo "فحص النسخ الاحتياطية - Odoo Multi-Version"
echo "جذر النسخ الاحتياطية: ${BACKUP_ROOT}"
echo -e "${BLUE}========================================${NC}"
echo ""

# البحث عن جميع ملفات manifest.json
MANIFESTS=$(find "${BACKUP_ROOT}" -name "manifest.json" -type f 2>/dev/null || true)

if [ -z "${MANIFESTS}" ]; then
    print_warning "لم يتم العثور على أي نسخ احتياطية في: ${BACKUP_ROOT}"
    exit 0
fi

for manifest in ${MANIFESTS}; do
    BACKUP_DIR=$(dirname "${manifest}")
    TOTAL=$((TOTAL + 1))
    
    echo ""
    print_info "فحص النسخة: ${BACKUP_DIR}"
    
    # التحقق من وجود ملفات أساسية
    for file in database.dump filestore.tar.zst manifest.json checksums.sha256; do
        if [ -f "${BACKUP_DIR}/${file}" ]; then
            print_success "  موجود: ${file}"
        else
            print_warning "  غير موجود: ${file}"
            ERRORS=$((ERRORS + 1))
        fi
    done
    
    # التحقق من checksums
    if [ -f "${BACKUP_DIR}/checksums.sha256" ]; then
        print_info "  التحقق من checksums..."
        cd "${BACKUP_DIR}"
        if sha256sum -c checksums.sha256 >/dev/null 2>&1; then
            print_success "  checksums صحيحة"
        else
            print_error "  checksums غير صحيحة"
            ERRORS=$((ERRORS + 1))
        fi
    fi
    
    # التحقق من صحة manifest.json
    if [ -f "${BACKUP_DIR}/manifest.json" ]; then
        if python3 -m json.tool "${BACKUP_DIR}/manifest.json" >/dev/null 2>&1; then
            print_success "  manifest.json صالح"
        else
            print_error "  manifest.json غير صالح"
            ERRORS=$((ERRORS + 1))
        fi
    fi
done

echo ""
echo -e "${BLUE}========================================${NC}"
echo "نتائج الفحص:"
echo "إجمالي النسخ المفحوصة: ${TOTAL}"
if [ ${ERRORS} -eq 0 ]; then
    print_success "جميع النسخ الاحتياطية سليمة (0 أخطاء)"
else
    print_error "تم العثور على ${ERRORS} خطأ في النسخ الاحتياطية"
fi
echo -e "${BLUE}========================================${NC}"

exit ${ERRORS}