#!/usr/bin/env bash
# ==============================================================================
# Odoo Infrastructure Manager - Odoo 17 / 18 / 19 One-Command Installer
#
# Follows the layout used by minhng92/odoo-{17,18,19}-docker-compose:
#   DESTINATION/
#     docker-compose.yml
#     entrypoint.sh
#     etc/odoo.conf
#     addons/
#     postgresql/
#     .env
#
# Differences (intentional):
#   - Passwords come from the project .env instead of hardcoded values.
#   - An isolated Docker network is created per instance.
#   - --with-traefik removes published ports and adds Traefik labels.
#
# Usage:
#   ./install-odoo.sh 17
#   ./install-odoo.sh 18 --destination /opt/odoo-infrastructure/odoo18
#   ./install-odoo.sh 19 --port 10019 --chat 20019 --with-traefik
#   ./install-odoo.sh 17 --no-start
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

log_info() { echo -e "\033[0;34m[INFO]\033[0m $*"; }
log_ok()   { echo -e "\033[0;32m[OK]\033[0m $*"; }
log_warn() { echo -e "\033[0;33m[WARN]\033[0m $*"; }
log_err()  { echo -e "\033[0;31m[ERROR]\033[0m $*" >&2; }

trap 'log_err "Odoo installation failed at line ${LINENO}."' ERR

VERSION="${1:-}"
if [[ "${VERSION}" != "17" && "${VERSION}" != "18" && "${VERSION}" != "19" ]]; then
  log_err "Usage: $0 <17|18|19> [--destination DIR] [--port PORT] [--chat PORT]"
  log_err "          [--password MASTER] [--db-password DB] [--with-traefik] [--no-start]"
  exit 1
fi
shift

DATA_ROOT="${ODOO_DATA_ROOT:-/opt/odoo-infrastructure}"
DESTINATION="${DATA_ROOT}/odoo${VERSION}"
HTTP_PORT="100${VERSION}"
CHAT_PORT="200${VERSION}"
MASTER_PASSWORD=""
DB_PASSWORD=""
WITH_TRAEFIK=0
START=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --destination)  DESTINATION="$2"; shift 2 ;;
    --port)         HTTP_PORT="$2"; shift 2 ;;
    --chat)         CHAT_PORT="$2"; shift 2 ;;
    --password)     MASTER_PASSWORD="$2"; shift 2 ;;
    --db-password)  DB_PASSWORD="$2"; shift 2 ;;
    --with-traefik) WITH_TRAEFIK=1; shift ;;
    --no-start)     START=0; shift ;;
    -h|--help)      sed -n '2,30p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) log_err "Unknown option: $1"; exit 2 ;;
  esac
done

# ------------------------------------------------------------------------------
# 1. Load secrets from the repository .env (never hardcode them)
# ------------------------------------------------------------------------------
ENV_FILE="${PROJECT_ROOT}/.env"
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
else
  log_warn "No ${ENV_FILE} found. Secrets must be provided on the command line."
fi

DB_USER_VAR="ODOO${VERSION}_DB_USER"
DB_PASS_VAR="ODOO${VERSION}_DB_PASSWORD"
ADMIN_PASS_VAR="ODOO${VERSION}_ADMIN_PASSWORD"
DB_NAME_VAR="ODOO${VERSION}_DB_NAME"
DOMAIN_VAR="ODOO${VERSION}_DOMAIN"

DB_USER="${!DB_USER_VAR:-odoo}"
DB_PASSWORD="${DB_PASSWORD:-${!DB_PASS_VAR:-}}"
MASTER_PASSWORD="${MASTER_PASSWORD:-${!ADMIN_PASS_VAR:-}}"
DB_NAME="${!DB_NAME_VAR:-odoo${VERSION}_prod}"
DOMAIN="${!DOMAIN_VAR:-odoo${VERSION}.localhost}"

if [[ -z "${DB_PASSWORD}" ]]; then
  log_err "${DB_PASS_VAR} is empty. Set it in ${ENV_FILE} or pass --db-password."
  exit 1
fi
if [[ -z "${MASTER_PASSWORD}" ]]; then
  log_err "${ADMIN_PASS_VAR} is empty. Set it in ${ENV_FILE} or pass --password."
  exit 1
fi

case "${VERSION}" in
  17)
    PG_IMAGE="postgres:16"
    PG_DATA_PATH="/var/lib/postgresql/data"
    PG_VERSION="16"
    ODOO_IMAGE="${ODOO17_IMAGE:-odoo:17}"
    ;;
  18)
    PG_IMAGE="postgres:17"
    PG_DATA_PATH="/var/lib/postgresql/data"
    PG_VERSION="17"
    ODOO_IMAGE="${ODOO18_IMAGE:-odoo:18}"
    ;;
  19)
    PG_IMAGE="postgres:18"
    # PostgreSQL 18 changed PGDATA to a version-specific path.
    PG_DATA_PATH="/var/lib/postgresql/18/docker"
    PG_VERSION="18"
    ODOO_IMAGE="${ODOO19_IMAGE:-odoo:19}"
    ;;
esac

# Prefer the project virtualenv but fall back to system python3.
PYTHON_BIN="${PROJECT_ROOT}/venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi
if [[ -z "${PYTHON_BIN}" ]]; then
  log_err "python3 is required to render the Odoo configuration."
  exit 1
fi

# ------------------------------------------------------------------------------
# 2. Prepare the instance directory (same layout as the reference repos)
# ------------------------------------------------------------------------------
log_info "Preparing Odoo ${VERSION} instance at ${DESTINATION}"
mkdir -p "${DESTINATION}/addons" "${DESTINATION}/etc" "${DESTINATION}/postgresql" "${DESTINATION}/backup"

if [[ "${WITH_TRAEFIK}" -eq 1 ]]; then
  COMPOSE_SOURCE="${PROJECT_ROOT}/deployment/odoo${VERSION}/docker-compose.traefik.yml"
  CONFIG_SOURCE="${PROJECT_ROOT}/deployment/odoo${VERSION}/config/odoo.conf"
else
  COMPOSE_SOURCE="${PROJECT_ROOT}/deployment/odoo${VERSION}/docker-compose.yml"
  CONFIG_SOURCE="${PROJECT_ROOT}/deployment/odoo${VERSION}/config/odoo.standalone.conf"
fi
if [[ ! -f "${COMPOSE_SOURCE}" ]]; then
  log_err "Compose template not found: ${COMPOSE_SOURCE}"
  exit 1
fi
cp "${COMPOSE_SOURCE}" "${DESTINATION}/docker-compose.yml"

cp "${PROJECT_ROOT}/templates/odoo-entrypoint.sh" "${DESTINATION}/entrypoint.sh"
chmod +x "${DESTINATION}/entrypoint.sh"

# Render the Odoo configuration with the real secrets (mode 0600).
"${PYTHON_BIN}" - "${CONFIG_SOURCE}" "${DESTINATION}/etc/odoo.conf" \
  "${DB_USER}" "${DB_PASSWORD}" "${MASTER_PASSWORD}" <<'PY'
import sys
from pathlib import Path

source, target, db_user, db_password, admin_password = sys.argv[1:6]
text = Path(source).read_text()
replacements = {
    "${ODOO_DB_USER}": db_user,
    "${ODOO_DB_PASSWORD}": db_password,
    "${ODOO_ADMIN_PASSWORD}": admin_password,
}
for old, new in replacements.items():
    text = text.replace(old, new)

out = Path(target)
out.write_text(text)
out.chmod(0o600)
PY

# Instance-local .env keeps the generated compose self-contained.
umask 077
cat > "${DESTINATION}/.env" <<EOF
POSTGRES_USER=${DB_USER}
POSTGRES_PASSWORD=${DB_PASSWORD}
ODOO_ADMIN_PASSWORD=${MASTER_PASSWORD}
ODOO_DB_NAME=${DB_NAME}
ODOO_HTTP_PORT=${HTTP_PORT}
ODOO_CHAT_PORT=${CHAT_PORT}
ODOO_DOMAIN=${DOMAIN}
ODOO_IMAGE=${ODOO_IMAGE}
PG_IMAGE=${PG_IMAGE}
PG_DATA_PATH=${PG_DATA_PATH}
ODOO_NETWORK=odoo${VERSION}_internal
DOCKER_PROXY_NETWORK=${DOCKER_PROXY_NETWORK:-proxy}
EOF
chmod 600 "${DESTINATION}/.env"
umask 022

log_ok "Instance files generated (secrets are mode 0600)."

# ------------------------------------------------------------------------------
# 3. Start the stack
# ------------------------------------------------------------------------------
if [[ "${START}" -eq 0 ]]; then
  log_ok "Skipping start (--no-start)."
  echo "  Run: docker compose -f ${DESTINATION}/docker-compose.yml up -d"
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  log_err "Docker is not installed. Run: ./bootstrap-odoo-infra.sh --install-docker"
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  log_err "Docker Compose v2 is required (docker compose)."
  exit 1
fi

if [[ "${WITH_TRAEFIK}" -eq 1 ]]; then
  if ! docker network inspect "${DOCKER_PROXY_NETWORK:-proxy}" >/dev/null 2>&1; then
    log_info "Creating Docker network '${DOCKER_PROXY_NETWORK:-proxy}'..."
    docker network create --driver bridge "${DOCKER_PROXY_NETWORK:-proxy}"
  fi
fi

log_info "Validating compose file..."
docker compose --env-file "${DESTINATION}/.env" -f "${DESTINATION}/docker-compose.yml" config >/dev/null

log_info "Starting Odoo ${VERSION} (PostgreSQL ${PG_VERSION})..."
docker compose --env-file "${DESTINATION}/.env" -f "${DESTINATION}/docker-compose.yml" up -d

log_ok "Odoo ${VERSION} is starting."
if [[ "${WITH_TRAEFIK}" -eq 1 ]]; then
  echo "  URL      : https://${DOMAIN}"
  echo "  Dashboard: https://${TRAEFIK_DASHBOARD_DOMAIN:-traefik.localhost}/dashboard/"
else
  echo "  URL      : http://localhost:${HTTP_PORT}"
  echo "  Livechat : http://localhost:${CHAT_PORT}"
fi
echo "  Config   : ${DESTINATION}/etc/odoo.conf"
echo "  Data     : ${DESTINATION}/postgresql"
echo "  Logs     : docker compose -f ${DESTINATION}/docker-compose.yml logs -f"
