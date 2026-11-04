#!/usr/bin/env bash
# ==============================================================================
# Odoo Multi-Version Deployment - Launch Infrastructure
# Launches the project with all necessary permissions
# ==============================================================================
set -Eeuo pipefail

# Output colors
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

# Check root privileges
if [[ $EUID -ne 0 ]]; then
    print_error "This script requires root privileges (sudo)."
    echo ""
    echo "Usage: sudo $0"
    echo "or:    bash $0 (with sudo)"
    exit 1
fi

# Determine paths dynamically based on script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

BOOTSTRAP_SCRIPT="${SCRIPT_DIR}/bootstrap-odoo-infra.sh"
INSTALL_ODOO17="${SCRIPT_DIR}/install-odoo17.sh"
INSTALL_ODOO19="${SCRIPT_DIR}/install-odoo19.sh"
HEALTH_CHECK="${SCRIPT_DIR}/health-check.sh"

print_header "Odoo Multi-Version Deployment - Launcher"
print_info "Launching project with all necessary permissions..."
print_info "Scripts directory: ${SCRIPT_DIR}"
print_info "Project directory: ${PROJECT_DIR}"

# ==============================================================================
# Step 1: Run Bootstrapper to install dependencies and prepare environment
# ==============================================================================
print_header "Step 1: Install dependencies and prepare environment (Bootstrap)"

if [[ -f "${BOOTSTRAP_SCRIPT}" ]]; then
    chmod +x "${BOOTSTRAP_SCRIPT}"
    print_info "Running bootstrap script: ${BOOTSTRAP_SCRIPT}"
    source "${BOOTSTRAP_SCRIPT}" 2>/dev/null || bash "${BOOTSTRAP_SCRIPT}" || {
        print_error "Failed to run bootstrap script. Please review errors above."
        exit 1
    }
    print_success "Environment setup completed successfully"
else
    print_warning "Bootstrap script not found: ${BOOTSTRAP_SCRIPT}"
    print_info "Proceeding assuming environment is already prepared"
fi

# ==============================================================================
# Step 2: Verify project files exist
# ==============================================================================
print_header "Step 2: Verify project files"

if [[ ! -d "${PROJECT_DIR}" ]]; then
    print_error "Project directory not found: ${PROJECT_DIR}"
    print_info "Please copy project files to this path or run bootstrap script first"
    exit 1
fi

print_success "Project directory found: ${PROJECT_DIR}"

# Verify essential installation scripts exist and make them executable
for file in "${INSTALL_ODOO17}" "${INSTALL_ODOO19}" "${HEALTH_CHECK}"; do
    if [[ -f "${file}" ]]; then
        chmod +x "${file}"
        print_info "Made script executable: $(basename "${file}")"
    else
        print_error "Missing file: ${file}"
        exit 1
    fi
done

# ==============================================================================
# Step 3: Verify Docker service is running
# ==============================================================================
print_header "Step 3: Verify Docker service"

if ! systemctl is-active --quiet docker 2>/dev/null; then
    print_info "Starting Docker service..."
    systemctl start docker 2>/dev/null || {
        print_error "Failed to start Docker service. Please start it manually: systemctl start docker"
        exit 1
    }
fi

if ! systemctl is-enabled --quiet docker 2>/dev/null; then
    systemctl enable docker 2>/dev/null || true
fi

print_success "Docker service is running: $(docker --version)"

# ==============================================================================
# Step 4: Verify Docker proxy network exists
# ==============================================================================
print_header "Step 4: Verify Docker proxy network"

DOCKER_NETWORK="proxy"
DOCKER_SUBNET="172.28.0.0/16"

if docker network inspect "${DOCKER_NETWORK}" >/dev/null 2>&1; then
    print_success "Docker network ${DOCKER_NETWORK} exists"
else
    print_info "Creating Docker network ${DOCKER_NETWORK}..."
    docker network create \
        --driver bridge \
        --subnet "${DOCKER_SUBNET}" \
        "${DOCKER_NETWORK}" >/dev/null 2>&1 || {
        print_warning "Failed to create network with subnet, trying default subnet..."
        docker network create --driver bridge "${DOCKER_NETWORK}" >/dev/null 2>&1 || {
            print_error "Failed to create Docker proxy network. Please create it manually."
            exit 1
        }
    }
    print_success "Docker network ${DOCKER_NETWORK} created"
fi

# ==============================================================================
# Step 5: Install Odoo 17
# ==============================================================================
print_header "Step 5: Install Odoo 17 (two independent instances)"

print_info "Running Odoo 17 installation script..."
chmod +x "${INSTALL_ODOO17}"
bash "${INSTALL_ODOO17}" || {
    print_error "Failed to install Odoo 17. Please review logs above."
    exit 1
}
print_success "Odoo 17 installed successfully"

# ==============================================================================
# Step 6: Install Odoo 19
# ==============================================================================
print_header "Step 6: Install Odoo 19 (two independent instances)"

print_info "Running Odoo 19 installation script..."
chmod +x "${INSTALL_ODOO19}"
bash "${INSTALL_ODOO19}" || {
    print_error "Failed to install Odoo 19. Please review logs above."
    exit 1
}
print_success "Odoo 19 installed successfully"

# ==============================================================================
# Step 7: Health check all services
# ==============================================================================
print_header "Step 7: Health check all services"

ALL_HEALTHY=true

for version in odoo17 odoo19; do
    for instance in instance1 instance2; do
        print_info "Health check ${version} - ${instance}..."
        if bash "${HEALTH_CHECK}" "${instance}" 8069 8072 2>/dev/null; then
            print_success "${version} - ${instance}: running normally"
        else
            print_warning "${version} - ${instance}: may need more time to start"
            ALL_HEALTHY=false
        fi
    done
done

# ==============================================================================
# Step 8: Display final report
# ==============================================================================
print_header "Final launch report"

echo -e "${GREEN}✓${NC} Project launched successfully!"
echo ""
echo -e "${BLUE}Services created:${NC}"
echo "  ┌─ Odoo 17 - Instance 1: https://odoo1.devops-odoo.com"
echo "  ├─ Odoo 17 - Instance 2: https://odoo2.devops-odoo.com"
echo "  ├─ Odoo 19 - Instance 1: https://odoo19-1.devops-odoo.com"
echo "  └─ Odoo 19 - Instance 2: https://odoo19-2.devops-odoo.com"
echo ""
echo -e "${BLUE}Active containers:${NC}"
docker ps --filter "name=odoo17" --filter "name=odoo19" \
    --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" 2>/dev/null || true
echo ""
echo -e "${BLUE}Data paths:${NC}"
echo "  Odoo 17: /data/odoo17/instance1, /data/odoo17/instance2"
echo "  Odoo 19: /data/odoo19/instance1, /data/odoo19/instance2"
echo ""
echo -e "${BLUE}Config paths:${NC}"
echo "  Odoo 17: /opt/odoo17/instance1, /opt/odoo17/instance2"
echo "  Odoo 19: /opt/odoo19/instance1, /opt/odoo19/instance2"
echo ""
echo -e "${BLUE}Backups:${NC}"
echo "  /data/backups/odoo17, /data/backups/odoo19"
echo ""

if [[ "${ALL_HEALTHY}" == "true" ]]; then
    print_success "All services are running normally!"
else
    print_warning "Some services may need more time to start completely."
    print_info "You can check status later using: ${HEALTH_CHECK} <instance> 8069 8072"
fi

echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "  Health check:     sudo ${HEALTH_CHECK} instance1 8069 8072"
echo "  Backup:           sudo ${SCRIPT_DIR}/backup.sh instance1 odoo17 /data/backups/odoo17"
echo "  Restore:          sudo ${SCRIPT_DIR}/restore.sh <backup_id> odoo17 instance1 existing"
echo "  Verify:           sudo ${SCRIPT_DIR}/verify-backups.sh /data/backups"
echo "  List backups:     sudo ${SCRIPT_DIR}/list-backups.sh /data/backups"
echo ""
echo -e "${GREEN}✓${NC} Project launched with all permissions!"
echo ""

exit 0