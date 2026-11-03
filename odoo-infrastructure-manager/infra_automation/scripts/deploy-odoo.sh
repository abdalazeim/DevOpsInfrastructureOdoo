#!/usr/bin/env bash
# ==============================================================================
# Odoo Infrastructure Manager - Odoo Deployment & Lifecycle Script
#
# Operates on the dedicated instance folder created by install-odoo.sh:
#   /opt/odoo-infrastructure/odoo{17,18,19}/docker-compose.yml
#
# Usage: ./deploy-odoo.sh <17|18|19> <start|stop|restart|logs|check|config>
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

VERSION="${1:-}"
ACTION="${2:-}"
DB_CONTAINER="odoo${VERSION}-db"
WEB_CONTAINER="odoo${VERSION}"
DATA_ROOT="${ODOO_DATA_ROOT:-/opt/odoo-infrastructure}"
INSTANCE_DIR_VAR="ODOO${VERSION}_DIR"
INSTANCE_DIR="${!INSTANCE_DIR_VAR:-${DATA_ROOT}/odoo${VERSION}}"
COMPOSE_FILE="${INSTANCE_DIR}/docker-compose.yml"
ENV_FILE="${INSTANCE_DIR}/.env"

log_info() { echo -e "\033[0;34m[INFO]\033[0m $*"; }
log_ok()   { echo -e "\033[0;32m[OK]\033[0m $*"; }
log_err()  { echo -e "\033[0;31m[ERROR]\033[0m $*" >&2; }

if [[ "${VERSION}" != "17" && "${VERSION}" != "18" && "${VERSION}" != "19" ]]; then
  log_err "Usage: $0 <17|18|19> <start|stop|restart|logs|check|config>"
  exit 1
fi

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  log_err "Odoo ${VERSION} is not installed yet: ${COMPOSE_FILE}"
  log_err "Run: bash automation/scripts/install-odoo.sh ${VERSION}"
  exit 1
fi

compose() {
  local env_args=()
  [[ -f "${ENV_FILE}" ]] && env_args=(--env-file "${ENV_FILE}")
  docker compose "${env_args[@]}" -f "${COMPOSE_FILE}" "$@"
}

case "${ACTION}" in
  start)
    log_info "Launching Odoo ${VERSION} stack..."
    compose up -d
    ;;
  stop)
    log_info "Stopping Odoo ${VERSION} stack..."
    compose stop
    ;;
  restart)
    log_info "Restarting Odoo ${VERSION} stack..."
    compose restart
    ;;
  logs)
    compose logs --tail 100 -f
    ;;
  config)
    compose config
    ;;
  check)
    if docker inspect "${WEB_CONTAINER}" >/dev/null 2>&1; then
      status=$(docker inspect --format='{{.State.Status}}' "${WEB_CONTAINER}")
      log_ok "Odoo ${VERSION} is ${status}"
    else
      log_err "Odoo ${VERSION} container not found."
      exit 1
    fi
    ;;
  *)
    log_err "Unknown action: ${ACTION}"
    exit 1
    ;;
esac
