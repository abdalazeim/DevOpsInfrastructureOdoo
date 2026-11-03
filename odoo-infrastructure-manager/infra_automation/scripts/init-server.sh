#!/usr/bin/env bash
# ==============================================================================
# Odoo Infrastructure Manager - Server Initialization Script
# Prepares baseline directories, network, and security permissions on Ubuntu
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

log_info() { echo -e "\033[0;34m[INFO]\033[0m $*"; }
log_ok()   { echo -e "\033[0;32m[OK]\033[0m $*"; }
log_warn() { echo -e "\033[0;33m[WARN]\033[0m $*"; }
log_err()  { echo -e "\033[0;31m[ERROR]\033[0m $*" >&2; }

trap 'log_err "Script terminated prematurely at line ${LINENO}"' ERR

log_info "Starting Odoo Infrastructure Server Baseline Initialization..."

# 1. Detect Ubuntu OS & Edition (Server / Desktop)
if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  source /etc/os-release
  log_info "Detected OS: ${PRETTY_NAME:-Ubuntu} (Supports Ubuntu Server & Desktop 22.04+)"
fi

if [[ $EUID -ne 0 ]]; then
  log_warn "Running without direct root privileges; sudo may be required for Docker and system tasks."
fi

# 2. Check Docker and Docker Compose
if command -v docker >/dev/null 2>&1; then
  log_ok "Docker is installed: $(docker --version)"
else
  log_err "Docker is not installed. Please run Ansible baseline or install docker-ce first."
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  log_ok "Docker Compose plugin is available: $(docker compose version)"
else
  log_err "Docker Compose v2 plugin is missing."
  exit 1
fi

# 3. Create Required Persistent Infrastructure Directories
DATA_ROOT="${ODOO_DATA_ROOT:-/opt/odoo-infrastructure}"
log_info "Ensuring persistent directories exist at: ${DATA_ROOT}"

mkdir -p "${DATA_ROOT}/traefik/acme"
mkdir -p "${DATA_ROOT}/traefik/logs"
mkdir -p "${DATA_ROOT}/odoo17/data"
mkdir -p "${DATA_ROOT}/odoo17/db_data"
mkdir -p "${DATA_ROOT}/odoo17/addons"
mkdir -p "${DATA_ROOT}/odoo19/data"
mkdir -p "${DATA_ROOT}/odoo19/db_data"
mkdir -p "${DATA_ROOT}/odoo19/addons"
mkdir -p "${DATA_ROOT}/backups"

# 4. Strict Permissions on sensitive acme certificates
touch "${DATA_ROOT}/traefik/acme/acme.json"
chmod 600 "${DATA_ROOT}/traefik/acme/acme.json"
log_ok "Created and secured acme.json with permissions 0600"

# 5. Create Shared Docker Network 'proxy' if not exists
PROXY_NET="${DOCKER_PROXY_NETWORK:-proxy}"
if ! docker network inspect "${PROXY_NET}" >/dev/null 2>&1; then
  log_info "Creating external bridge network '${PROXY_NET}'..."
  docker network create \
    --driver bridge \
    --subnet 172.28.0.0/16 \
    "${PROXY_NET}"
  log_ok "Network '${PROXY_NET}' successfully created."
else
  log_ok "Network '${PROXY_NET}' already exists."
fi

log_ok "Server initialization complete! Ready for Traefik and Odoo deployment."
