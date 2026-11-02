#!/usr/bin/env bash
# ==============================================================================
# Odoo Infrastructure Manager - Traefik Docker Management Script
# Provides idempotent discovery, deployment, proxy networking, backup, and health testing.
# Adheres strictly to: set -Eeuo pipefail
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

TRAEFIK_CONFIG_DIR="${TRAEFIK_CONFIG_DIR:-/opt/traefik}"
TRAEFIK_IMAGE="${TRAEFIK_IMAGE:-traefik:v3.7}"
CONTAINER_NAME="traefik"
PROXY_NETWORK="${DOCKER_PROXY_NETWORK:-proxy}"
HTTP_PORT="${TRAEFIK_HTTP_PORT:-80}"
DASHBOARD_INTERNAL_PORT="8080"
DASHBOARD_EXTERNAL_PORT="${TRAEFIK_DASHBOARD_PORT:-10090}"
ODOO19_PORT="${ODOO19_PORT:-10019}"
JENKINS_PORT="${JENKINS_PORT:-8081}"

log_info() { echo -e "\033[0;34m[INFO]\033[0m $*"; }
log_ok()   { echo -e "\033[0;32m[OK]\033[0m $*"; }
log_warn() { echo -e "\033[0;33m[WARN]\033[0m $*"; }
log_err()  { echo -e "\033[0;31m[ERROR]\033[0m $*" >&2; }

trap 'log_err "Traefik operation failed at line ${LINENO}"' ERR

check_requirements() {
  if ! command -v docker >/dev/null 2>&1; then
    log_err "Docker Engine is not installed! Aborting."
    exit 1
  fi
  if ! docker compose version >/dev/null 2>&1; then
    log_err "Docker Compose v2 is required! Aborting."
    exit 1
  fi
}

cmd_discover() {
  log_info "=== TRAEFIK DISCOVERY & AUDIT ==="
  check_requirements
  log_ok "Docker: $(docker --version)"
  log_ok "Compose: $(docker compose version)"

  # Container status
  if docker inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
    local status
    status=$(docker inspect --format='{{.State.Status}}' "${CONTAINER_NAME}")
    local img
    img=$(docker inspect --format='{{.Config.Image}}' "${CONTAINER_NAME}")
    log_ok "Container '${CONTAINER_NAME}' exists: status=${status}, image=${img}"
  else
    log_warn "Container '${CONTAINER_NAME}' does not exist."
  fi

  # Proxy network
  if docker network inspect "${PROXY_NETWORK}" >/dev/null 2>&1; then
    log_ok "Docker network '${PROXY_NETWORK}' exists."
    log_info "Connected containers:"
    docker network inspect "${PROXY_NETWORK}" --format='{{range $k, $v := .Containers}} - {{$v.Name}} ({{$v.IPv4Address}}){{println}}{{end}}'
  else
    log_warn "Docker network '${PROXY_NETWORK}' does not exist."
  fi

  # Port inspections
  log_info "Port conflict check (80, 10090, 8080, 10019, 8081):"
  for p in 80 10090 8080 10019 8081; do
    if ss -tuln 2>/dev/null | grep -q ":${p} "; then
      log_warn "Port :${p} is CURRENTLY BOUND on host."
    else
      log_ok "Port :${p} is free."
    fi
  done
}

ensure_proxy_network() {
  if ! docker network inspect "${PROXY_NETWORK}" >/dev/null 2>&1; then
    log_info "Creating external bridge network '${PROXY_NETWORK}'..."
    docker network create --driver bridge --subnet "172.28.0.0/16" "${PROXY_NETWORK}"
    log_ok "Network '${PROXY_NETWORK}' created."
  fi
}

ensure_directories() {
  mkdir -p "${TRAEFIK_CONFIG_DIR}/acme"
  mkdir -p "${TRAEFIK_CONFIG_DIR}/logs"
  mkdir -p "${TRAEFIK_CONFIG_DIR}/backups"

  local acme_file="${TRAEFIK_CONFIG_DIR}/acme/acme.json"
  if [[ ! -f "${acme_file}" ]]; then
    echo "{}" > "${acme_file}"
  fi
  chmod 600 "${acme_file}"
}

cmd_backup() {
  ensure_directories
  local ts
  ts=$(date +%Y%m%d_%H%M%S)
  local backup_file="${TRAEFIK_CONFIG_DIR}/backups/traefik_backup_${ts}.tar.gz"

  log_info "Creating Traefik backup snapshot: ${backup_file}"
  tar -czf "${backup_file}" -C "${TRAEFIK_CONFIG_DIR}" acme logs $([[ -f "${TRAEFIK_CONFIG_DIR}/docker-compose.yml" ]] && echo "docker-compose.yml" || true) $([[ -f "${TRAEFIK_CONFIG_DIR}/traefik.yml" ]] && echo "traefik.yml" || true)
  chmod 600 "${backup_file}"
  local sha
  sha=$(sha256sum "${backup_file}" | awk '{print $1}')
  log_ok "Backup created successfully! SHA256: ${sha}"
  echo "${backup_file}"
}

cmd_deploy() {
  check_requirements
  ensure_directories
  ensure_proxy_network

  local compose_target="${TRAEFIK_CONFIG_DIR}/docker-compose.yml"
  local project_compose="${PROJECT_ROOT}/deployment/traefik/docker-compose.yml"

  # Pre-change safety backup if compose exists
  if [[ -f "${compose_target}" ]]; then
    log_info "Existing Traefik configuration detected. Creating pre-change backup..."
    cmd_backup >/dev/null
  fi

  # Synchronize or generate compose file
  if [[ -f "${project_compose}" ]]; then
    log_info "Deploying Compose file from project templates to ${compose_target}..."
    cp "${project_compose}" "${compose_target}"
  fi

  log_info "Validating compose syntax..."
  docker compose -f "${compose_target}" config >/dev/null

  log_info "Launching Traefik container (${TRAEFIK_IMAGE})..."
  docker compose -f "${compose_target}" up -d

  sleep 2
  cmd_verify
}

cmd_verify() {
  log_info "=== TRAEFIK POST-EXECUTION VERIFICATION ==="
  if docker inspect --format='{{.State.Status}}' "${CONTAINER_NAME}" 2>/dev/null | grep -q "running"; then
    log_ok "Traefik container is RUNNING."
  else
    log_err "Traefik container is NOT running!"
    exit 1
  fi

  # Check Port 80
  if ss -tuln 2>/dev/null | grep -q ":80 "; then
    log_ok "Port 80 (HTTP Web Entrypoint) is active."
  fi

  # Check Port 10090 (Dashboard)
  if ss -tuln 2>/dev/null | grep -q ":${DASHBOARD_EXTERNAL_PORT} "; then
    log_ok "Port ${DASHBOARD_EXTERNAL_PORT} (Dashboard) is active."
    log_ok "Dashboard URL: http://localhost:${DASHBOARD_EXTERNAL_PORT}/dashboard/"
  fi
}

cmd_restart() {
  check_requirements
  local compose_target="${TRAEFIK_CONFIG_DIR}/docker-compose.yml"
  if [[ -f "${compose_target}" ]]; then
    docker compose -f "${compose_target}" restart
  else
    docker restart "${CONTAINER_NAME}"
  fi
  log_ok "Traefik container restarted."
  cmd_verify
}

cmd_stop() {
  check_requirements
  local compose_target="${TRAEFIK_CONFIG_DIR}/docker-compose.yml"
  if [[ -f "${compose_target}" ]]; then
    docker compose -f "${compose_target}" stop
  else
    docker stop "${CONTAINER_NAME}"
  fi
  log_ok "Traefik container stopped safely (volumes and proxy network preserved)."
}

# Main Command Dispatcher
ACTION="${1:-discover}"
case "${ACTION}" in
  discover) cmd_discover ;;
  deploy)   cmd_deploy ;;
  verify)   cmd_verify ;;
  restart)  cmd_restart ;;
  stop)     cmd_stop ;;
  backup)   cmd_backup ;;
  *)
    echo "Usage: $0 {discover|deploy|verify|restart|stop|backup}"
    exit 1
    ;;
esac
