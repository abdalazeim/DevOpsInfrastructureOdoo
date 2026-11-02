#!/usr/bin/env bash
# ==============================================================================
# Odoo Infrastructure Manager - Odoo Deployment & Lifecycle Script
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

VERSION=$1
ACTION=$2
DB_CONTAINER="odoo${VERSION}-db"
WEB_CONTAINER="odoo${VERSION}"
# Based on project directory structure in summary
COMP_DIR="${PROJECT_ROOT}/deployment/odoo${VERSION}"

log_info() { echo -e "\033[0;34m[INFO]\033[0m $*"; }
log_ok()   { echo -e "\033[0;32m[OK]\033[0m $*"; }
log_err()  { echo -e "\033[0;31m[ERROR]\033[0m $*" >&2; }

if [[ ! -d "${COMP_DIR}" ]]; then
  log_err "Configuration directory for Odoo ${VERSION} not found: ${COMP_DIR}"
  exit 1
fi

case "${ACTION}" in
  start)
    log_info "Launching Odoo ${VERSION} stack..."
    docker compose -f "${COMP_DIR}/docker-compose.yml" up -d
    ;;
  stop)
    log_info "Stopping Odoo ${VERSION} stack..."
    docker compose -f "${COMP_DIR}/docker-compose.yml" stop
    ;;
  restart)
    log_info "Restarting Odoo ${VERSION} stack..."
    docker compose -f "${COMP_DIR}/docker-compose.yml" restart
    ;;
  logs)
    docker compose -f "${COMP_DIR}/docker-compose.yml" logs --tail 100 -f
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
