#!/usr/bin/env bash
# ==============================================================================
# Odoo Infrastructure Manager - Traefik v3.7 Setup & Launcher
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TRAEFIK_DIR="${PROJECT_ROOT}/deployment/traefik"

log_info() { echo -e "\033[0;34m[INFO]\033[0m $*"; }
log_ok()   { echo -e "\033[0;32m[OK]\033[0m $*"; }
log_warn() { echo -e "\033[0;33m[WARN]\033[0m $*"; }
log_err()  { echo -e "\033[0;31m[ERROR]\033[0m $*" >&2; }

trap 'log_err "Traefik setup failed at line ${LINENO}"' ERR

ENV_FILE="${1:-${PROJECT_ROOT}/.env}"

if [[ -f "${ENV_FILE}" ]]; then
  log_info "Loading environment variables from: ${ENV_FILE}"
  # Export non-comment lines
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
else
  log_warn "No environment file found at ${ENV_FILE}. Using default parameters."
fi

DATA_ROOT="${ODOO_DATA_ROOT:-/opt/odoo-infrastructure}"
ACME_FILE="${DATA_ROOT}/traefik/acme/acme.json"

mkdir -p "${DATA_ROOT}/traefik/acme"
mkdir -p "${DATA_ROOT}/traefik/logs"

if [[ ! -f "${ACME_FILE}" ]]; then
  touch "${ACME_FILE}"
fi
chmod 600 "${ACME_FILE}"

PROXY_NET="${DOCKER_PROXY_NETWORK:-proxy}"
if ! docker network inspect "${PROXY_NET}" >/dev/null 2>&1; then
  log_info "Creating Docker proxy network: ${PROXY_NET}"
  docker network create --driver bridge "${PROXY_NET}"
fi

log_info "Checking port 80 and 443 availability..."
for port in 80 443; do
  if ss -tuln 2>/dev/null | grep -q ":${port} "; then
    log_warn "Port ${port} is currently bound. Ensure no other web server (nginx/apache) is running."
  fi
done

log_info "Validating Traefik compose configuration..."
docker compose --env-file "${ENV_FILE}" -f "${TRAEFIK_DIR}/docker-compose.yml" config >/dev/null

log_info "Launching Traefik v3.7 container..."
docker compose --env-file "${ENV_FILE}" -f "${TRAEFIK_DIR}/docker-compose.yml" up -d

log_info "Waiting for Traefik to become healthy..."
sleep 3
if docker inspect --format='{{.State.Status}}' traefik 2>/dev/null | grep -q "running"; then
  log_ok "Traefik v3.7 is up and running successfully!"
else
  log_err "Traefik container failed to start properly. Check logs with: docker logs traefik"
  exit 1
fi
