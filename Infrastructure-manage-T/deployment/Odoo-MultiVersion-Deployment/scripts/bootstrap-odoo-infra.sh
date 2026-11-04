#!/usr/bin/env bash
# ==============================================================================
# Odoo Multi-Version Deployment - Bootstrap Infrastructure
# Installs all dependencies and prepares the environment for the project
# ==============================================================================
set -euo pipefail

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

# Determine paths dynamically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BOOTSTRAP_LOG="/var/log/odoo-bootstrap.log"

print_header "Odoo Multi-Version Deployment - Bootstrap"
print_info "Installing dependencies and preparing environment..."
print_info "Project directory: ${PROJECT_DIR}"
print_info "Log file: ${BOOTSTRAP_LOG}"

# Redirect output to log file and screen
exec > >(tee -a "${BOOTSTRAP_LOG}") 2>&1

# ==============================================================================
# Step 1: Update system and install basic packages
# ==============================================================================
print_header "Step 1: Update system and install basic packages"

print_info "Updating package index..."
if apt-get update -y >/dev/null 2>&1; then
    print_success "Package index updated"
else
    print_warning "Failed to update package index (no internet connection?)"
fi

print_info "Installing basic packages..."
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    curl wget gnupg software-properties-common apt-transport-https \
    ca-certificates python3 python3-pip python3-venv git vim sudo ufw jq tar gzip zstd \
    >/dev/null 2>&1 || {
    print_error "Failed to install basic packages"
    exit 1
}
print_success "Basic packages installed successfully"

# ==============================================================================
# Step 2: Install Docker Engine
# ==============================================================================
print_header "Step 2: Install Docker Engine"

if command -v docker >/dev/null 2>&1; then
    print_success "Docker already installed: $(docker --version)"
else
    print_info "Installing Docker Engine from official repository..."
    install -m 0755 -d /etc/apt/keyrings 2>/dev/null || true
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null || true
    chmod a+r /etc/apt/keyrings/docker.gpg 2>/dev/null || true

    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        | tee /etc/apt/sources.list.d/docker.list >/dev/null

    apt-get update -y >/dev/null 2>&1 || true
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin \
        >/dev/null 2>&1 || {
        print_error "Failed to install Docker Engine"
        exit 1
    }

    systemctl enable docker >/dev/null 2>&1 || true
    systemctl start docker >/dev/null 2>&1 || true
    print_success "Docker Engine installed successfully"
fi

print_info "Docker version: $(docker --version)"
print_info "Docker Compose version: $(docker compose version 2>/dev/null || echo 'not available')"

# Add current user to docker group
if [[ -n "${SUDO_USER:-}" ]]; then
    usermod -aG docker "${SUDO_USER}" 2>/dev/null || true
    print_info "Added user ${SUDO_USER} to docker group"
fi

usermod -aG docker odoo 2>/dev/null || true

# ==============================================================================
# Step 3: Install Ansible
# ==============================================================================
print_header "Step 3: Install Ansible and collections"

if command -v ansible-playbook >/dev/null 2>&1; then
    print_success "Ansible already installed: $(ansible-playbook --version | head -1)"
else
    print_info "Installing Ansible via pip3..."
    python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
    python3 -m pip install ansible >/dev/null 2>&1 || {
        print_error "Failed to install Ansible via pip3"
        exit 1
    }
    print_success "Ansible installed successfully"
fi

print_info "Ansible version: $(ansible-playbook --version | head -1)"

# ==============================================================================
# Step 4: Install required Ansible collections
# ==============================================================================
print_header "Step 4: Install required Ansible collections"

REQUIREMENTS_FILE="${PROJECT_DIR}/requirements.yml"
if [[ -f "${REQUIREMENTS_FILE}" ]]; then
    print_info "Installing collections from requirements.yml..."
    ansible-galaxy collection install -r "${REQUIREMENTS_FILE}" 2>&1 | tail -10
    print_success "Ansible collections installed successfully"
else
    print_warning "requirements.yml not found. Installing collections manually..."
    ansible-galaxy collection install community.docker:3.8.0 2>&1 | tail -3 || true
    ansible-galaxy collection install community.general:7.4.0 2>&1 | tail -3 || true
    ansible-galaxy collection install ansible.posix:1.5.4 2>&1 | tail -3 || true
fi

print_info "Installed collections:"
ansible-galaxy collection list 2>/dev/null | grep -E "community.docker|community.general|ansible.posix" || true

# ==============================================================================
# Step 5: Create directories and basic structure
# ==============================================================================
print_header "Step 5: Create directories and basic structure"

DIRS=(
    "/opt"
    "/data"
    "/data/backups"
    "/opt/odoo17" "/opt/odoo19"
    "/data/odoo17" "/data/odoo19"
    "/data/backups/odoo17" "/data/backups/odoo19"
    "/data/backups/infrastructure" "/data/backups/jenkins" "/data/backups/reports"
)

for dir in "${DIRS[@]}"; do
    if [[ ! -d "${dir}" ]]; then
        mkdir -p "${dir}"
        print_info "Created directory: ${dir}"
    fi
done

# Create instance directories for each version
for version in odoo17 odoo19; do
    for instance in instance1 instance2; do
        mkdir -p "/data/${version}/${instance}/postgresql"
        mkdir -p "/opt/${version}/${instance}/etc"
        mkdir -p "/opt/${version}/${instance}/addons"
    done
done
print_success "All basic directories created"

# ==============================================================================
# Step 6: Set permissions
# ==============================================================================
print_header "Step 6: Set permissions and files"

chmod 755 /opt/odoo17 /data/odoo17 /data/backups/odoo17 2>/dev/null || true
chmod 755 /opt/odoo19 /data/odoo19 /data/backups/odoo19 2>/dev/null || true
chmod 700 /data/odoo17/instance1/postgresql /data/odoo17/instance2/postgresql 2>/dev/null || true
chmod 700 /data/odoo19/instance1/postgresql /data/odoo19/instance2/postgresql 2>/dev/null || true

if ! id "odoo" >/dev/null 2>&1; then
    useradd -r -s /usr/sbin/nologin -d /var/lib/odoo odoo 2>/dev/null || true
    print_info "Created system user odoo"
fi
usermod -aG docker odoo 2>/dev/null || true

print_success "Permissions set successfully"

# ==============================================================================
# Step 7: Create Docker proxy network
# ==============================================================================
print_header "Step 7: Create Docker proxy network"

DOCKER_NETWORK="proxy"
DOCKER_SUBNET="172.28.0.0/16"

if docker network inspect "${DOCKER_NETWORK}" >/dev/null 2>&1; then
    print_success "Docker network ${DOCKER_NETWORK} already exists"
else
    print_info "Creating Docker network ${DOCKER_NETWORK}..."
    docker network create \
        --driver bridge \
        --subnet "${DOCKER_SUBNET}" \
        "${DOCKER_NETWORK}" >/dev/null 2>&1 || {
        print_warning "Failed to create network with subnet, trying default subnet..."
        docker network create --driver bridge "${DOCKER_NETWORK}" >/dev/null 2>&1 || {
            print_error "Failed to create Docker proxy network"
            exit 1
        }
    }
    print_success "Docker network ${DOCKER_NETWORK} created"
fi

# ==============================================================================
# Step 8: Make project scripts executable
# ==============================================================================
print_header "Step 8: Make project scripts executable"

if [[ -d "${PROJECT_DIR}/scripts" ]]; then
    chmod +x "${PROJECT_DIR}/scripts"/*.sh 2>/dev/null || true
    print_success "Project scripts made executable"
else
    print_warning "Project scripts directory not found: ${PROJECT_DIR}/scripts"
fi

# ==============================================================================
# Step 9: Final environment verification
# ==============================================================================
print_header "Step 9: Final environment verification"

ALL_OK=true

command -v docker >/dev/null 2>&1 && print_success "Docker: $(docker --version)" || { print_error "Docker not installed"; ALL_OK=false; }
docker compose version >/dev/null 2>&1 && print_success "Docker Compose: $(docker compose version)" || { print_error "Docker Compose not available"; ALL_OK=false; }
command -v ansible-playbook >/dev/null 2>&1 && print_success "Ansible: $(ansible-playbook --version | head -1)" || { print_error "Ansible not installed"; ALL_OK=false; }
command -v python3 >/dev/null 2>&1 && print_success "Python3: $(python3 --version)" || { print_error "Python3 not installed"; ALL_OK=false; }
command -v git >/dev/null 2>&1 && print_success "Git: $(git --version)" || { print_error "Git not installed"; ALL_OK=false; }
docker network inspect "${DOCKER_NETWORK}" >/dev/null 2>&1 && print_success "Docker network ${DOCKER_NETWORK}: exists" || { print_error "Docker network ${DOCKER_NETWORK}: not found"; ALL_OK=false; }

if [[ -d "${PROJECT_DIR}" ]]; then
    print_success "Project directory: ${PROJECT_DIR} (exists)"
else
    print_warning "Project directory: ${PROJECT_DIR} (not found)"
fi

# ==============================================================================
# Completion
# ==============================================================================
print_header "Environment setup complete"

if [[ "${ALL_OK}" == "true" ]]; then
    print_success "All dependencies installed and environment is ready!"
    echo ""
    print_info "Next steps:"
    echo "  1. cd ${PROJECT_DIR}"
    echo "  2. sudo bash scripts/launch-odoo-infra.sh"
    echo ""
    print_info "Or install directly:"
    echo "  sudo bash scripts/install-odoo17.sh"
    echo "  sudo bash scripts/install-odoo19.sh"
else
    print_error "Some components were not installed successfully. Please review errors above."
    exit 1
fi

echo ""
exit 0