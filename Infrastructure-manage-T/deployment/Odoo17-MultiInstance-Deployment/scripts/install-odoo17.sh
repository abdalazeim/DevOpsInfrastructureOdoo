#!/bin/bash
# ==============================================================================
# Odoo 17 Multi-Instance Unified Installation Script
# يمكن تشغيل هذا السكربت من Terminal مباشرة، أو عبر Jenkins Pipeline
# يستخدم نفس Ansible Playbook في الطريقتين لضمان نتائج متطابقة
# ==============================================================================
set -euo pipefail

# ألوان الإخراج
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# مسارات المشروع
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ANSIBLE_PLAYBOOK="${PROJECT_ROOT}/ansible/playbooks/install.yml"
ANSIBLE_INVENTORY="${PROJECT_ROOT}/ansible/inventory/hosts.ini"
INSTANCES_CONFIG="${PROJECT_ROOT}/instances/odoo17.yml"
REQUIREMENTS_FILE="${PROJECT_ROOT}/requirements.yml"

# متغيرات قابلة للتعديل عبر متغيرات البيئة
ODOO_ADMIN_PASSWORD="${ODOO_ADMIN_PASSWORD:-}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
ANSIBLE_VAULT_PASSWORD="${ANSIBLE_VAULT_PASSWORD:-}"
GITHUB_REPO="${GITHUB_REPO:-https://github.com/your-org/Odoo-MultiVersion-Deployment.git}"

print_header() {
    echo ""
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}==========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# دالة فحص المتطلبات
check_requirements() {
    print_header "الخطوة 1: فحص المتطلبات الأساسية"
    
    local missing=0
    
    # فحص نظام التشغيل
    if command -v lsb_release >/dev/null 2>&1; then
        local os_info=$(lsb_release -ds 2>/dev/null || echo "Unknown")
        print_info "نظام التشغيل: ${os_info}"
    else
        print_warning "لا يمكن تحديد نظام التشغيل بدقة"
    fi
    
    # فحص Docker
    if command -v docker >/dev/null 2>&1; then
        print_success "Docker Engine مثبت: $(docker --version)"
    else
        print_error "Docker Engine غير مثبت"
        missing=1
    fi
    
    # فحص Docker Compose
    if docker compose version >/dev/null 2>&1; then
        print_success "Docker Compose مثبت: $(docker compose version)"
    else
        print_error "Docker Compose غير مثبت"
        missing=1
    fi
    
    # فحص Ansible
    if command -v ansible-playbook >/dev/null 2>&1; then
        print_success "Ansible مثبت: $(ansible-playbook --version | head -1)"
    else
        print_error "Ansible غير مثبت"
        missing=1
    fi
    
    # فحص المساحة والذاكرة
    print_info "مساحة القرص المتاحة:"
    df -h /opt /data 2>/dev/null || df -h /
    
    print_info "الذاكرة المتاحة:"
    free -h 2>/dev/null || echo "لا يمكن قراءة معلومات الذاكرة"
    
    if [ $missing -eq 1 ]; then
        print_error "بعض المتطلبات الناقصة. يرجى تثبيتها قبل المتابعة."
        exit 1
    fi
    
    print_success "جميع المتطلبات الأساسية متوفرة"
}

# دالة تثبيت المتطلبات الناقصة
install_missing_requirements() {
    print_header "الخطوة 2: تثبيت المتطلبات الناقصة"
    
    # تحديث قائمة الحزم
    apt-get update -qq 2>/dev/null || true
    
    # تثبيت Python pipx إذا لم يكن موجوداً
    if ! command -v pipx >/dev/null 2>&1; then
        print_info "تثبيت pipx..."
        apt-get install -y -qq pipx >/dev/null 2>&1 || true
        pipx ensurepath >/dev/null 2>&1 || true
    fi
    
    # تثبيت مجموعات Ansible المطلوبة
    if [ -f "${REQUIREMENTS_FILE}" ]; then
        print_info "تثبيت مجموعات Ansible Galaxy..."
        ansible-galaxy collection install -r "${REQUIREMENTS_FILE}" 2>&1 | tail -5
        print_success "تم تثبيت مجموعات Ansible"
    fi
    
    print_success "تم تثبيت جميع المتطلبات"
}

# دالة إنشاء المجلدات والشبكات
create_infrastructure() {
    print_header "الخطوة 3: إنشاء المجلدات والشبكات والصلاحيات"
    
    # إنشاء المجلدات الأساسية
    local dirs=(
        "/opt/odoo17"
        "/data/odoo17"
        "/data/backups/odoo17"
        "/data/odoo17/instance1"
        "/data/odoo17/instance2"
        "/data/odoo17/instance1/postgresql"
        "/data/odoo17/instance2/postgresql"
        "/opt/odoo17/instance1"
        "/opt/odoo17/instance2"
        "/opt/odoo17/instance1/etc"
        "/opt/odoo17/instance1/addons"
        "/opt/odoo17/instance2/etc"
        "/opt/odoo17/instance2/addons"
    )
    
    for dir in "${dirs[@]}"; do
        if [ ! -d "${dir}" ]; then
            mkdir -p "${dir}"
            print_info "تم إنشاء المجلد: ${dir}"
        fi
    done
    
    # تعيين الصلاحيات
    chmod 755 /opt/odoo17 /data/odoo17 /data/backups/odoo17
    chmod 700 /data/odoo17/instance1/postgresql /data/odoo17/instance2/postgresql
    
    # إنشاء شبكة Docker proxy إذا لم تكن موجودة
    if ! docker network inspect proxy >/dev/null 2>&1; then
        print_info "إنشاء شبكة Docker proxy..."
        docker network create --driver bridge --subnet 172.28.0.0/16 proxy 2>/dev/null || \
        docker network create --driver bridge proxy 2>/dev/null || true
        print_success "تم إنشاء شبكة proxy"
    else
        print_success "شبكة proxy موجودة بالفعل"
    fi
    
    print_success "تم إنشاء المجلدات والشبكات والصلاحيات"
}

# دالة تشغيل Ansible Playbook
run_ansible_playbook() {
    print_header "الخطوة 4: تشغيل Ansible Playbook للنشر"
    
    # التحقق من وجود ملف playbook
    if [ ! -f "${ANSIBLE_PLAYBOOK}" ]; then
        print_error "ملف Ansible Playbook غير موجود: ${ANSIBLE_PLAYBOOK}"
        exit 1
    fi
    
    # التحقق من وجود ملف المخزون
    if [ ! -f "${ANSIBLE_INVENTORY}" ]; then
        print_error "ملف مخزون المضيفين غير موجود: ${ANSIBLE_INVENTORY}"
        exit 1
    fi
    
    # تحضير متغيرات إضافية
    local extra_vars=""
    if [ -n "${ODOO_ADMIN_PASSWORD}" ]; then
        extra_vars="${extra_vars} -e vault_odoo_admin_password=${ODOO_ADMIN_PASSWORD}"
    fi
    if [ -n "${POSTGRES_PASSWORD}" ]; then
        extra_vars="${extra_vars} -e vault_postgres_password=${POSTGRES_PASSWORD}"
    fi
    
    # تشغيل Playbook
    print_info "تشغيل ansible-playbook: ${ANSIBLE_PLAYBOOK}"
    
    if [ -n "${ANSIBLE_VAULT_PASSWORD}" ]; then
        echo "${ANSIBLE_VAULT_PASSWORD}" > /tmp/.ansible_vault_pass
        chmod 600 /tmp/.ansible_vault_pass
        ansible-playbook -i "${ANSIBLE_INVENTORY}" \
            -e @${INSTANCES_CONFIG} \
            ${extra_vars} \
            --vault-password-file /tmp/.ansible_vault_pass \
            "${ANSIBLE_PLAYBOOK}"
        rm -f /tmp/.ansible_vault_pass
    else
        ansible-playbook -i "${ANSIBLE_INVENTORY}" \
            -e @${INSTANCES_CONFIG} \
            ${extra_vars} \
            "${ANSIBLE_PLAYBOOK}"
    fi
    
    print_success "تم تشغيل Ansible Playbook بنجاح"
}

# دالة فحص صحة الخدمات
run_health_checks() {
    print_header "الخطوة 5: فحص صحة الخدمات"
    
    local all_healthy=true
    
    for instance in instance1 instance2; do
        print_info "فحص صحة النسخة: ${instance}"
        
        # فحص حاوية Odoo
        local odoo_container="odoo17-${instance}"
        local db_container="odoo17-${instance}-db"
        
        if docker ps --format '{{.Names}}' | grep -q "^${odoo_container}$"; then
            local status=$(docker inspect --format='{{.State.Status}}' "${odoo_container}" 2>/dev/null || echo "unknown")
            if [ "${status}" = "running" ]; then
                print_success "حاوية Odoo تعمل: ${odoo_container}"
            else
                print_error "حاوية Odoo غير عاملة: ${odoo_container} (${status})"
                all_healthy=false
            fi
        else
            print_error "حاوية Odoo غير موجودة: ${odoo_container}"
            all_healthy=false
        fi
        
        # فحص حاوية قاعدة البيانات
        if docker ps --format '{{.Names}}' | grep -q "^${db_container}$"; then
            local db_status=$(docker inspect --format='{{.State.Status}}' "${db_container}" 2>/dev/null || echo "unknown")
            if [ "${db_status}" = "running" ]; then
                print_success "حاوية قاعدة البيانات تعمل: ${db_container}"
            else
                print_error "حاوية قاعدة البيانات غير عاملة: ${db_container} (${db_status})"
                all_healthy=false
            fi
        else
            print_error "حاوية قاعدة البيانات غير موجودة: ${db_container}"
            all_healthy=false
        fi
        
        # فحص PostgreSQL
        if docker exec "${db_container}" pg_isready -U odoo -h localhost >/dev/null 2>&1; then
            print_success "قاعدة بيانات PostgreSQL تستجيب: ${db_container}"
        else
            print_error "قاعدة بيانات PostgreSQL لا تستجيب: ${db_container}"
            all_healthy=false
        fi
    done
    
    if [ "${all_healthy}" = true ]; then
        print_success "جميع الخدمات سالمة وبحالة جيدة"
        return 0
    else
        print_error "بعض الخدمات غير سالمة. يرجى مراجعة السجلات أعلاه."
        return 1
    fi
}

# دالة عرض التقرير النهائي
show_final_report() {
    print_header "التقرير النهائي لعملية التثبيت"
    
    echo -e "${BLUE}النسخة الأولى:${NC}"
    echo "  النطاق: odoo1.devops-odoo.com"
    echo "  الحاوية: odoo17-instance1"
    echo "  قاعدة البيانات: odoo17_db1 (PostgreSQL 16 مستقل)"
    echo "  البيانات: /data/odoo17/instance1"
    echo ""
    
    echo -e "${BLUE}النسخة الثانية:${NC}"
    echo "  النطاق: odoo2.devops-odoo.com"
    echo "  الحاوية: odoo17-instance2"
    echo "  قاعدة البيانات: odoo17_db2 (PostgreSQL 16 مستقل)"
    echo "  البيانات: /data/odoo17/instance2"
    echo ""
    
    echo -e "${BLUE}الحاويات العاملة:${NC}"
    docker ps --filter "name=odoo17" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || true
    
    echo ""
    echo -e "${BLUE}الشبكات:${NC}"
    docker network ls --filter "name=odoo17\|proxy" --format "table {{.Name}}\t{{.Driver}}" 2>/dev/null || true
    
    echo ""
    echo -e "${GREEN}✓ تم تثبيت نسختي Odoo 17 بنجاح${NC}"
    echo ""
    echo "للوصول عبر Tr
afik (HTTPS):"
    echo "  https://odoo1.devops-odoo.com"
    echo "  https://odoo2.devops-odoo.com"
    echo ""
    echo "للوصول المباشر (HTTP - إذا لم يكن Tr
afik مضمناً):"
    echo "  http://localhost:8069 (النسخة الأولى)"
    echo "  http://localhost:8069 (النسخة الثانية - عبر ترافيك)"
}

# الدالة الرئيسية
main() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════╗"
    echo "║    Odoo 17 Multi-Instance Unified Installer    ║"
    echo "║    يدعم التشغيل من Terminal و Jenkins           ║"
    echo "╚═════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    print_info "مسار المشروع: ${PROJECT_ROOT}"
    print_info "ملف Ansible Playbook: ${ANSIBLE_PLAYBOOK}"
    echo ""
    
    check_requirements
    install_missing_requirements
    create_infrastructure
    run_ansible_playbook
    
    if run_health_checks; then
        show_final_report
        exit 0
    else
        print_error "فشلت اختبارات الصحة. يرجى مراجعة السجلات أعلاه."
        exit 1
    fi
}

# تشغيل الدالة الرئيسية
main "$@"