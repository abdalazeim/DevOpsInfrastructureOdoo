#!/bin/bash
# ==============================================================================
# Odoo Multi-Version Deployment - List Backups Script
# يعرض جميع النسخ الاحتياطية المتوفرة مع تفاصيلها
# ==============================================================================
set -euo pipefail

BACKUP_ROOT="${1:-/data/backups}"
ODOO_VERSION="${2:-all}"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[i]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }

echo -e "${BLUE}================================================================================${NC}"
echo "النسخ الاحتياطية المتوفرة - Odoo Multi-Version Deployment"
echo "جذر النسخ الاحتياطية: ${BACKUP_ROOT}"
echo -e "${BLUE}================================================================================${NC}"
echo ""

if [ ! -d "${BACKUP_ROOT}" ]; then
    print_info "مجلد النسخ الاحتياطية غير موجود: ${BACKUP_ROOT}"
    exit 0
fi

# عرض النسخ لكل إصدار
for version in odoo17 odoo18 odoo19; do
    if [ "${ODOO_VERSION}" != "all" ] && [ "${ODOO_VERSION}" != "${version}" ]; then
        continue
    fi
    
    VERSION_DIR="${BACKUP_ROOT}/${version}"
    if [ ! -d "${VERSION_DIR}" ]; then
        continue
    fi
    
    echo -e "${GREEN}📦 الإصدار: ${version}${NC}"
    echo "--------------------------------------------------------------------------------"
    
    for instance_dir in "${VERSION_DIR}"/*/; do
        if [ ! -d "${instance_dir}" ]; then
            continue
        fi
        
        instance_name=$(basename "${instance_dir}")
        
        for backup_dir in "${instance_dir}"/*/; do
            if [ ! -d "${backup_dir}" ]; then
                continue
            fi
            
            backup_name=$(basename "${backup_dir}")
            
            # قراءة معلومات من manifest.json إذا موجود
            if [ -f "${backup_dir}/manifest.json" ]; then
                backup_type=$(python3 -c "import json; print(json.load(open('${backup_dir}/manifest.json')).get('backup_type', 'غير معروف'))" 2>/dev/null || echo "غير معروف")
                created_at=$(python3 -c "import json; print(json.load(open('${backup_dir}/manifest.json')).get('created_at', 'غير معروف'))" 2>/dev/null || echo "غير معروف")
                database=$(python3 -c "import json; print(json.load(open('${backup_dir}/manifest.json')).get('database', 'غير معروف'))" 2>/dev/null || echo "غير معروف")
                status=$(python3 -c "import json; print(json.load(open('${backup_dir}/manifest.json')).get('status', 'غير معروف'))" 2>/dev/null || echo "غير معروف")
            else
                backup_type="غير معروف"
                created_at="غير معروف"
                database="غير معروف"
                status="غير معروف"
            fi
            
            # حساب حجم النسخة
            backup_size=$(du -sh "${backup_dir}" 2>/dev/null | cut -f1 || echo "غير معروف")
            
            echo ""
            echo "  📁 النسخة: ${backup_name}"
            echo "     النسخة (Instance): ${instance_name}"
            echo "     نوع النسخ: ${backup_type}"
            echo "     التاريخ: ${created_at}"
            echo "     قاعدة البيانات: ${database}"
            echo "     الحالة: ${status}"
            echo "     الحجم: ${backup_size}"
            echo "     المسار: ${backup_dir}"
        done
    done
    echo ""
done

echo -e "${BLUE}================================================================================${NC}"
print_success "اكتمل عرض جميع النسخ الاحتياطية المتوفرة"
exit 0