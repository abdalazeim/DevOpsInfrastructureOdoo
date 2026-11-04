#!/usr/bin/env bash
# ==============================================================================
# Odoo Multi-Version Deployment - Launch Infrastructure
# يشغل المشروع بجميع الصلاحيات اللازمة
# Launches the project with all necessary permissions
# ==============================================================================
set -Eeuo pipefail

# ألوان الإخراج
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}================================================================${NC}"
    echo ""
}

print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_error()   { echo -e "${RED}[✗]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_info()    { echo -e "${BLUE}[i]${NC} $1"; }

# التحقق من صلاحيات الجذر
if [[ $EUID -ne 0 ]]; then
    print_error "هذا السكربت يتطلب صلاحيات الجذر (root/sudo)."
    echo ""
    echo "الاستخدام: sudo $0"
    echo "أو:         bash $0 (مع sudo)"
    exit 1
fi

# تحديد المسارات ديناميكياً بناءً على موقع السكربت
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

BOOTSTRAP_SCRIPT="${SCRIPT_DIR}/bootstrap-odoo-infra.sh"
INSTALL_ODOO17="${SCRIPT_DIR}/install-odoo17.sh"
INSTALL_ODOO19="${SCRIPT_DIR}/install-odoo19.sh"
HEALTH_CHECK="${SCRIPT_DIR}/health-check.sh"

print_header "Odoo Multi-Version Deployment - Launcher"
print_info "بدء تشغيل المشروع بجميع الصلاحيات المطلوبة..."
print_info "مجلد السكربتات: ${SCRIPT_DIR}"
print_info "مجلد المشروع: ${PROJECT_DIR}"

# ==============================================================================
# الخطوة 1: تشغيل Bootstrapper لتثبيت الملاحقات وإعداد البيئة
# ==============================================================================
print_header "الخطوة 1: تثبيت الملاحقات وإعداد البيئة (Bootstrap)"

if [[ -f "${BOOTSTRAP_SCRIPT}" ]]; then
    chmod +x "${BOOTSTRAP_SCRIPT}"
    print_info "تشغيل السكربت التحضيري: ${BOOTSTRAP_SCRIPT}"
    # تشغيل السكربت التحضيري في نفس الجلسة (لا نستخدم subprocess منفصل)
    source "${BOOTSTRAP_SCRIPT}" 2>/dev/null || bash "${BOOTSTRAP_SCRIPT}" || {
        print_error "فشل تشغيل السكربت التحضيري. يرجى مراجعة الأخطاء أعلاه."
        exit 1
    }
    print_success "اكتمل إعداد البيئة بنجاح"
else
    print_warning "السكربت التحضيري غير موجود: ${BOOTSTRAP_SCRIPT}"
    print_info "سيتم المتابعة مع افتراض أن البيئة مُعدة مسبقاً"
fi

# ==============================================================================
# الخطوة 2: التأكد من وجود ملفات المشروع
# ==============================================================================
print_header "الخطوة 2: التحقق من ملفات المشروع"

if [[ ! -d "${PROJECT_DIR}" ]]; then
    print_error "مجلد المشروع غير موجود: ${PROJECT_DIR}"
    print_info "الرجاء نسخ ملفات المشروع إلى هذا المسار أو تشغيل السكربت التحضيري أولاً"
    exit 1
fi

print_success "مجلد المشروع موجود: ${PROJECT_DIR}"

# التأكد من وجود ملفات التثبيت الأساسية وجعلها قابلة للتنفيذ
for file in "${INSTALL_ODOO17}" "${INSTALL_ODOO19}" "${HEALTH_CHECK}"; do
    if [[ -f "${file}" ]]; then
        chmod +x "${file}"
        print_info "تم جعل السكربت قابل للتنفيذ: $(basename "${file}")"
    else
        print_error "ملف ناقص: ${file}"
        exit 1
    fi
done

# ==============================================================================
# الخطوة 3: التأكد من تشغيل خدمة Docker
# ==============================================================================
print_header "الخطوة 3: التحقق من خدمة Docker"

if ! systemctl is-active --quiet docker 2>/dev/null; then
    print_info "تشغيل خدمة Docker..."
    systemctl start docker 2>/dev/null || {
        print_error "فشل تشغيل خدمة Docker. يرجى تشغيلها يدوياً: systemctl start docker"
        exit 1
    }
fi

if ! systemctl is-enabled --quiet docker 2>/dev/null; then
    systemctl enable docker 2>/dev/null || true
fi

print_success "خدمة Docker تعمل بنجاح: $(docker --version)"

# ==============================================================================
# الخطوة 4: التأكد من وجود شبكة Docker proxy
# ==============================================================================
print_header "الخطوة 4: التحقق من شبكة Docker proxy"

DOCKER_NETWORK="proxy"
DOCKER_SUBNET="172.28.0.0/16"

if docker network inspect "${DOCKER_NETWORK}" >/dev/null 2>&1; then
    print_success "شبكة Docker ${DOCKER_NETWORK} موجودة"
else
    print_info "إنشاء شبكة Docker ${DOCKER_NETWORK}..."
    docker network create \
        --driver bridge \
        --subnet "${DOCKER_SUBNET}" \
        "${DOCKER_NETWORK}" >/dev/null 2>&1 || {
        print_warning "فشل إنشاء الشبكة مع subnet محدد، محاولة subnet افتراضي..."
        docker network create --driver bridge "${DOCKER_NETWORK}" >/dev/null 2>&1 || {
            print_error "فشل إنشاء شبكة Docker proxy. يرجى إنشائها يدوياً."
            exit 1
        }
    }
    print_success "تم إنشاء شبكة Docker ${DOCKER_NETWORK}"
fi

# ==============================================================================
# الخطوة 5: تثبيت Odoo 17
# ==============================================================================
print_header "الخطوة 5: تثبيت Odoo 17 (نسختان مستقلتان)"

print_info "تشغيل سكريبت تثبيت Odoo 17..."
chmod +x "${INSTALL_ODOO17}"
bash "${INSTALL_ODOO17}" || {
    print_error "فشل تثبيت Odoo 17. يرجى مراجعة السجلات أعلاه."
    exit 1
}
print_success "تم تثبيت Odoo 17 بنجاح"

# ==============================================================================
# الخطوة 6: تثبيت Odoo 19
# ==============================================================================
print_header "الخطوة 6: تثبيت Odoo 19 (نسختان مستقلتان)"

print_info "تشغيل سكريبت تثبيت Odoo 19..."
chmod +x "${INSTALL_ODOO19}"
bash "${INSTALL_ODOO19}" || {
    print_error "فشل تثبيت Odoo 19. يرجى مراجعة السجلات أعلاه."
    exit 1
}
print_success "تم تثبيت Odoo 19 بنجاح"

# ==============================================================================
# الخطوة 7: فحص صحة جميع الخدمات
# ==============================================================================
print_header "الخطوة 7: فحص صحة جميع الخدمات"

ALL_HEALTHY=true

for version in odoo17 odoo19; do
    for instance in instance1 instance2; do
        print_info "فحص صحة ${version} - ${instance}..."
        if bash "${HEALTH_CHECK}" "${instance}" 8069 8072 2>/dev/null; then
            print_success "${version} - ${instance}: يعمل بشكل طبيعي"
        else
            print_warning "${version} - ${instance}: قد يحتاج إلى وقت إضافي للبدء"
            ALL_HEALTHY=false
        fi
    done
done

# ==============================================================================
# الخطوة 8: عرض التقرير النهائي
# ==============================================================================
print_header "تقرير التشغيل النهائي"

echo -e "${GREEN}✓${NC} تم تشغيل المشروع بنجاح!"
echo ""
echo -e "${BLUE}الخدمات المُنشأة:${NC}"
echo "  ┌─ Odoo 17 - Instance 1: https://odoo1.devops-odoo.com"
echo "  ├─ Odoo 17 - Instance 2: https://odoo2.devops-odoo.com"
echo "  ├─ Odoo 19 - Instance 1: https://odoo19-1.devops-odoo.com"
echo "  └─ Odoo 19 - Instance 2: https://odoo19-2.devops-odoo.com"
echo ""
echo -e "${BLUE}الحاويات النشطة:${NC}"
docker ps --filter "name=odoo17" --filter "name=odoo19" \
    --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" 2>/dev/null || true
echo ""
echo -e "${BLUE}مسارات البيانات:${NC}"
echo "  Odoo 17: /data/odoo17/instance1, /data/odoo17/instance2"
echo "  Odoo 19: /data/odoo19/instance1, /data/odoo19/instance2"
echo ""
echo -e "${BLUE}مسارات الإعدادات:${NC}"
echo "  Odoo 17: /opt/odoo17/instance1, /opt/odoo17/instance2"
echo "  Odoo 19: /opt/odoo19/instance1, /opt/odoo19/instance2"
echo ""
echo -e "${BLUE}نسخ احتياطية:${NC}"
echo "  /data/backups/odoo17, /data/backups/odoo19"
echo ""

if [[ "${ALL_HEALTHY}" == "true" ]]; then
    print_success "جميع الخدمات تعمل بشكل طبيعي!"
else
    print_warning "بعض الخدمات قد تحتاج إلى وقت إضافي للبدء completamente."
    print_info "يمكنك فحص الحالة لاحقاً باستخدام: ${HEALTH_CHECK} <instance> 8069 8072"
fi

echo ""
echo -e "${BLUE}الأوامر المفيدة:${NC}"
echo "  فحص الصحة:     sudo ${HEALTH_CHECK} instance1 8069 8072"
echo "  النسخ الاحتياطي: sudo ${SCRIPT_DIR}/backup.sh instance1 odoo17 /data/backups/odoo17"
echo "  الاستعادة:       sudo ${SCRIPT_DIR}/restore.sh <backup_id> odoo17 instance1 existing"
echo "  التحقق:          sudo ${SCRIPT_DIR}/verify-backups.sh /data/backups"
echo "  عرض النسخ:       sudo ${SCRIPT_DIR}/list-backups.sh /data/backups"
echo ""
echo -e "${GREEN}✓${NC} اكتمل تشغيل المشروع بجميع الصلاحيات!"
echo ""

exit 0