#!/bin/bash
# ==============================================================================
# Odoo 18 Multi-Instance Unified Installation Script
# يستخدم نفس Ansible Playbook مثل Jenkins Pipeline لضمان نتائج متطابقة
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ANSIBLE_PLAYBOOK="${PROJECT_ROOT}/ansible/playbooks/install-odoo18.yml"
ANSIBLE_INVENTORY="${PROJECT_ROOT}/ansible/inventory/hosts.ini"
INSTANCES_CONFIG="${PROJECT_ROOT}/versions/odoo18.yml"
REQUIREMENTS_FILE="${PROJECT_ROOT}/requirements.yml"

ODOO_ADMIN_PASSWORD="${ODOO_ADMIN_PASSWORD:-}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
ANSIBLE_VAULT_PASSWORD="${ANSIBLE_VAULT_PASSWORD:-}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() { echo ""; echo -e "${BLUE}==========================================${NC}"; echo -e "${BLUE} $1${NC}"; echo -e "${BLUE}==========================================${NC}"; echo ""; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }
print_info() { echo -e "${BLUE}[i]${NC} $1"; }

check_requirements() {
    print_header "الخطوة 1: فحص المتطلبات الأساسية (Odoo 18)"
    local missing=0
    command -v docker >/dev/null 2>&1 && print_success "Docker Engine: $(docker --version)" || { print_error "Docker Engine غير مثبت"; missing=1; }
    docker compose version >/dev/null 2>&1 && print_success "Docker Compose: $(docker compose version)" || { print_error "Docker Compose غير مثبت"; missing=1; }
    command -v ansible-playbook >/dev/null 2>&1 && print_success "Ansible: $(ansible-playbook --version | head -1)" || { print_error "Ansible غير مثبت"; missing=1; }
    df -h /opt /data 2>/dev/null || df -h /
    free -h 2>/dev/null || echo "لا يمكن قراءة الذاكرة"
    [ $missing -eq 1 ] && { print_error "متطلبات ناقصة"; exit 1; }
    print_success "جميع المتطلبات متوفرة"
}

install_requirements() {
    print_header "الخطوة 2: تثبيت المتطلبات الناقصة"
    apt-get update -qq 2>/dev/null || true
    command -v pipx >/dev/null 2>&1 || { apt-get install -y -qq pipx >/dev/null 2>&1 || true; pipx ensurepath >/dev/null 2>&1 || true; }
    [ -f "${REQUIREMENTS_FILE}" ] && ansible-galaxy collection install -r "${REQUIREMENTS_FILE}" 2>&1 | tail -5
    print_success "تم تثبيت المتطلبات"
}

create_infrastructure() {
    print_header "الخطوة 3: إنشاء المجلدات والشبكات (Odoo 18)"
    local dirs=(
        "/opt/odoo18" "/data/odoo18" "/data/backups/odoo18"
        "/data/odoo18/instance1" "/data/odoo18/instance2"
        "/data/odoo18/instance1/postgresql" "/data/odoo18/instance2/postgresql"
        "/opt/odoo18/instance1" "/opt/odoo18/instance2"
        "/opt/odoo18/instance1/etc" "/opt/odoo18/instance1/addons"
        "/opt/odoo18/instance2/etc" "/opt/odoo18/instance2/addons"
    )
    for dir in "${dirs[@]}"; do [ -d "${dir}" ] || mkdir -p "${dir}" && print_info "تم إنشاء: ${dir}"; done
    chmod 755 /opt/odoo18 /data/odoo18 /data/backups/odoo18
    chmod 700 /data/odoo18/instance1/postgresql /data/odoo18/instance2/postgresql
    docker network inspect proxy >/dev/null 2>&1 || { docker network create --driver bridge --subnet 172.28.0.0/16 proxy 2>/dev/null || docker network create --driver bridge proxy 2>/dev/null || true; print_success "تم إنشاء شبكة proxy"; } || print_success "شبكة proxy موجودة"
    print_success "تم إنشاء المجلدات والشبكات"
}

run_ansible() {
    print_header "الخطوة 4: تشغيل Ansible Playbook (Odoo 18)"
    [ -f "${ANSIBLE_PLAYBOOK}" ] || { print_error "ملف playbook غير موجود"; exit 1; }
    [ -f "${ANSIBLE_INVENTORY}" ] || { print_error "ملف المخزون غير موجود"; exit 1; }
    local extra_vars=""
    [ -n "${ODOO_ADMIN_PASSWORD}" ] && extra_vars="${extra_vars} -e vault_odoo_admin_password=${ODOO_ADMIN_PASSWORD}"
    [ -n "${POSTGRES_PASSWORD}" ] && extra_vars="${extra_vars} -e vault_postgres_password=${POSTGRES_PASSWORD}"
    print_info "تشغيل: ${ANSIBLE_PLAYBOOK}"
    if [ -n "${ANSIBLE_VAULT_PASSWORD}" ]; then
        echo "${ANSIBLE_VAULT_PASSWORD}" > /tmp/.ansible_vault_pass; chmod 600 /tmp/.ansible_vault_pass
        ansible-playbook -i "${ANSIBLE_INVENTORY}" -e @"${INSTANCES_CONFIG}" ${extra_vars} --vault-password-file /tmp/.ansible_vault_pass "${ANSIBLE_PLAYBOOK}"
        rm -f /tmp/.ansible_vault_pass
    else
        ansible-playbook -i "${ANSIBLE_INVENTORY}" -e @"${INSTANCES_CONFIG}" ${extra_vars} "${ANSIBLE_PLAYBOOK}"
    fi
    print_success "تم تشغيل Ansible Playbook بنجاح"
}

run_health_checks() {
    print_header "الخطوة 5: فحص صحة الخدمات (Odoo 18)"
    local all_healthy=true
    for instance in instance1 instance2; do
        print_info "فحص: ${instance}"
        local odoo_c="odoo18-${instance}" db_c="odoo18-${instance}-db"
        docker ps --format '{{.Names}}' | grep -q "^${odoo_c}$" || { print_error "حاوية غير موجودة: ${odoo_c}"; all_healthy=false; continue; }
        docker ps --format '{{.Names}}' | grep -q "^${db_c}$" || { print_error "حاوية DB غير موجودة: ${db_c}"; all_healthy=false; continue; }
        [ "$(docker inspect --format='{{.State.Status}}' "${odoo_c}" 2>/dev/null || echo unknown)" = "running" ] && print_success "Odoo يعمل: ${odoo_c}" || { print_error "Odoo غير عاملة: ${odoo_c}"; all_healthy=false; }
        [ "$(docker inspect --format='{{.State.Status}}' "${db_c}" 2>/dev/null || echo unknown)" = "running" ] && print_success "DB تعمل: ${db_c}" || { print_error "DB غير عاملة: ${db_c}"; all_healthy=false; }
        docker exec "${db_c}" pg_isready -U odoo -h localhost >/dev/null 2>&1 && print_success "PostgreSQL 17 يستجيب" || { print_error "PostgreSQL 17 لا يستجيب"; all_healthy=false; }
    done
    [ "${all_healthy}" = true ] && { print_success "جميع الخدمات سالمة"; return 0; } || { print_error "بعض الخدمات غير سالمة"; return 1; }
}

show_report() {
    print_header "التقرير النهائي - Odoo 18 Multi-Instance"
    echo "النسخة 1: odoo18-1.devops-odoo.com | odoo18-instance1 | odoo18_db1 (PostgreSQL 17)"
    echo "النسخة 2: odoo18-2.devops-odoo.com | odoo18-instance2 | odoo18_db2 (PostgreSQL 17)"
    echo ""
    docker ps --filter "name=odoo18" --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || true
    echo ""
    echo -e "${GREEN}✓ تم تثبيت نسختي Odoo 18 بنجاح${NC}"
    echo "https://odoo18-1.devops-odoo.com"
    echo "https://odoo18-2.devops-odoo.com"
}

main() {
    echo -e "${BLUE}╔═════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Odoo 18 Multi-Instance Unified Installer  ║${NC}"
    echo -e "${BLUE}╚═════════════════════════════════════╝${NC}"
    print_info "المسار: ${PROJECT_ROOT}"
    check_requirements
    install_requirements
    create_infrastructure
    run_ansible
    run_health_checks && show_report || { print_error "فشلت الفحوصات"; exit 1; }
}
main "$@"