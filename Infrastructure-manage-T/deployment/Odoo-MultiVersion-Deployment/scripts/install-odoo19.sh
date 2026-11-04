#!/usr/bin/env bash
# ==============================================================================
# Odoo 19 Multi-Instance Unified Installation Script
# Uses same Ansible Playbook as Jenkins Pipeline to ensure identical results
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ANSIBLE_PLAYBOOK="${PROJECT_ROOT}/ansible/playbooks/install-odoo19.yml"
ANSIBLE_INVENTORY="${PROJECT_ROOT}/ansible/inventory/hosts.ini"
INSTANCES_CONFIG="${PROJECT_ROOT}/versions/odoo19.yml"
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
    print_header "Step 1: Check basic requirements (Odoo 19)"
    local missing=0
    command -v docker >/dev/null 2>&1 && print_success "Docker Engine: $(docker --version)" || { print_error "Docker Engine not installed"; missing=1; }
    docker compose version >/dev/null 2>&1 && print_success "Docker Compose: $(docker compose version)" || { print_error "Docker Compose not installed"; missing=1; }
    command -v ansible-playbook >/dev/null 2>&1 && print_success "Ansible: $(ansible-playbook --version | head -1)" || { print_error "Ansible not installed"; missing=1; }
    df -h /opt /data 2>/dev/null || df -h /
    free -h 2>/dev/null || echo "Cannot read memory"
    [ $missing -eq 1 ] && { print_error "Requirements incomplete"; exit 1; }
    print_success "All requirements available"
}

install_requirements() {
    print_header "Step 2: Install missing requirements"
    apt-get update -qq 2>/dev/null || true
    command -v pipx >/dev/null 2>&1 || { apt-get install -y -qq pipx >/dev/null 2>&1 || true; pipx ensurepath >/dev/null 2>&1 || true; }
    [ -f "${REQUIREMENTS_FILE}" ] && ansible-galaxy collection install -r "${REQUIREMENTS_FILE}" 2>&1 | tail -5
    print_success "Requirements installed"
}

create_infrastructure() {
    print_header "Step 3: Create directories and networks (Odoo 19)"
    local dirs=(
        "/opt/odoo19" "/data/odoo19" "/data/backups/odoo19"
        "/data/odoo19/instance1" "/data/odoo19/instance2"
        "/data/odoo19/instance1/postgresql" "/data/odoo19/instance2/postgresql"
        "/opt/odoo19/instance1" "/opt/odoo19/instance2"
        "/opt/odoo19/instance1/etc" "/opt/odoo19/instance1/addons"
        "/opt/odoo19/instance2/etc" "/opt/odoo19/instance2/addons"
    )
    for dir in "${dirs[@]}"; do [ -d "${dir}" ] || mkdir -p "${dir}" && print_info "Created: ${dir}"; done
    chmod 755 /opt/odoo19 /data/odoo19 /data/backups/odoo19
    chmod 700 /data/odoo19/instance1/postgresql /data/odoo19/instance2/postgresql
    docker network inspect proxy >/dev/null 2>&1 || { docker network create --driver bridge --subnet 172.28.0.0/16 proxy 2>/dev/null || docker network create --driver bridge proxy 2>/dev/null || true; print_success "Created proxy network"; } || print_success "proxy network exists"
    print_success "Directories and networks created"
}

run_ansible() {
    print_header "Step 4: Run Ansible Playbook (Odoo 19)"
    [ -f "${ANSIBLE_PLAYBOOK}" ] || { print_error "Playbook file not found"; exit 1; }
    [ -f "${ANSIBLE_INVENTORY}" ] || { print_error "Inventory file not found"; exit 1; }
    local extra_vars=""
    [ -n "${ODOO_ADMIN_PASSWORD}" ] && extra_vars="${extra_vars} -e vault_odoo_admin_password=${ODOO_ADMIN_PASSWORD}"
    [ -n "${POSTGRES_PASSWORD}" ] && extra_vars="${extra_vars} -e vault_postgres_password=${POSTGRES_PASSWORD}"
    print_info "Running: ${ANSIBLE_PLAYBOOK}"
    if [ -n "${ANSIBLE_VAULT_PASSWORD}" ]; then
        echo "${ANSIBLE_VAULT_PASSWORD}" > /tmp/.ansible_vault_pass; chmod 600 /tmp/.ansible_vault_pass
        ansible-playbook -i "${ANSIBLE_INVENTORY}" -e @"${INSTANCES_CONFIG}" ${extra_vars} --vault-password-file /tmp/.ansible_vault_pass "${ANSIBLE_PLAYBOOK}"
        rm -f /tmp/.ansible_vault_pass
    else
        ansible-playbook -i "${ANSIBLE_INVENTORY}" -e @"${INSTANCES_CONFIG}" ${extra_vars} "${ANSIBLE_PLAYBOOK}"
    fi
    print_success "Ansible Playbook completed successfully"
}

run_health_checks() {
    print_header "Step 5: Check service health (Odoo 19)"
    local all_healthy=true
    for instance in instance1 instance2; do
        print_info "Checking: ${instance}"
        local odoo_c="odoo19-${instance}" db_c="odoo19-${instance}-db"
        docker ps --format '{{.Names}}' | grep -q "^${odoo_c}$" || { print_error "Container not found: ${odoo_c}"; all_healthy=false; continue; }
        docker ps --format '{{.Names}}' | grep -q "^${db_c}$" || { print_error "DB container not found: ${db_c}"; all_healthy=false; continue; }
        [ "$(docker inspect --format='{{.State.Status}}' "${odoo_c}" 2>/dev/null || echo unknown)" = "running" ] && print_success "Odoo running: ${odoo_c}" || { print_error "Odoo not running: ${odoo_c}"; all_healthy=false; }
        [ "$(docker inspect --format='{{.State.Status}}' "${db_c}" 2>/dev/null || echo unknown)" = "running" ] && print_success "DB running: ${db_c}" || { print_error "DB not running: ${db_c}"; all_healthy=false; }
        docker exec "${db_c}" pg_isready -U odoo -h localhost >/dev/null 2>&1 && print_success "PostgreSQL 18 responds" || { print_error "PostgreSQL 18 not responding"; all_healthy=false; }
    done
    [ "${all_healthy}" = true ] && { print_success "All services healthy"; return 0; } || { print_error "Some services not healthy"; return 1; }
}

show_report() {
    print_header "Final report - Odoo 19 Multi-Instance"
    echo "Instance 1: odoo19-1.devops-odoo.com | odoo19-instance1 | odoo19_db1 (PostgreSQL 18)"
    echo "Instance 2: odoo19-2.devops-odoo.com | odoo19-instance2 | odoo19_db2 (PostgreSQL 18)"
    echo ""
    docker ps --filter "name=odoo19" --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || true
    echo ""
    echo -e "${GREEN}✓ Odoo 19 two instances installed successfully${NC}"
    echo "https://odoo19-1.devops-odoo.com"
    echo "https://odoo19-2.devops-odoo.com"
}

main() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Odoo 19 Multi-Instance Unified Installer  ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    print_info "Path: ${PROJECT_ROOT}"
    check_requirements
    install_requirements
    create_infrastructure
    run_ansible
    run_health_checks && show_report || { print_error "Health checks failed"; exit 1; }
}
main "$@"