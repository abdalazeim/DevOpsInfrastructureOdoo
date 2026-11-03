#!/usr/bin/env bash
# ==============================================================================
# Odoo Infrastructure Manager - Launcher
#
# Verifies the environment (and bootstraps it on first run), then starts the
# Python CLI/TUI with all arguments forwarded to app.main.
#
# Usage:
#   ./launch-odoo-infra.sh                          # interactive TUI
#   ./launch-odoo-infra.sh --action validate
#   ./launch-odoo-infra.sh --action preflight -p profiles/example.yaml
#   ./launch-odoo-infra.sh --action api --api-port 8787
#   ./launch-odoo-infra.sh --no-bootstrap --help
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV="${VENV_DIR:-${ROOT}/venv}"
PYTHON="${VENV}/bin/python"
NO_BOOTSTRAP=0
ARGS=()

for arg in "$@"; do
  if [[ "${arg}" == "--no-bootstrap" ]]; then
    NO_BOOTSTRAP=1
  else
    ARGS+=("${arg}")
  fi
done

log_info() { echo -e "\033[0;34m[INFO]\033[0m $*"; }
log_warn() { echo -e "\033[0;33m[WARN]\033[0m $*"; }
log_err()  { echo -e "\033[0;31m[ERROR]\033[0m $*" >&2; }

trap 'log_err "Launch failed at line ${LINENO}."' ERR

cd "${ROOT}"

# ------------------------------------------------------------------------------
# 1. Ensure the virtual environment exists
# ------------------------------------------------------------------------------
if [[ ! -x "${PYTHON}" ]]; then
  if [[ ${NO_BOOTSTRAP} -eq 1 ]]; then
    log_err "Virtual environment not found at ${VENV}."
    log_err "Run ./bootstrap-odoo-infra.sh first (or drop --no-bootstrap)."
    exit 1
  fi
  log_warn "Virtual environment not found. Running bootstrap first..."
  "${SCRIPT_DIR}/bootstrap-odoo-infra.sh"
fi

# ------------------------------------------------------------------------------
# 2. Ensure the protected .env exists
# ------------------------------------------------------------------------------
if [[ ! -f "${ROOT}/.env" ]]; then
  if [[ -f "${ROOT}/templates/env.template" && ${NO_BOOTSTRAP} -eq 0 ]]; then
    log_warn ".env is missing. Creating it from templates/env.template..."
    cp "${ROOT}/templates/env.template" "${ROOT}/.env"
    chmod 600 "${ROOT}/.env"
    log_warn "Edit ${ROOT}/.env and replace the placeholder secrets before deploying."
  else
    log_warn ".env not found. Commands that need secrets (Docker deployments) may fail."
  fi
fi

# ------------------------------------------------------------------------------
# 3. Verify the package is still importable (venv may point to a moved repo)
# ------------------------------------------------------------------------------
if ! "${PYTHON}" -c 'import yaml, app.main' >/dev/null 2>&1 && ! "${PYTHON}" -c 'import yaml; from infrastructure_core.app import main' >/dev/null 2>&1; then
  if [[ ${NO_BOOTSTRAP} -eq 1 ]]; then
    log_err "Python dependencies are missing or broken in ${VENV}."
    exit 1
  fi
  log_warn "Python environment is incomplete. Re-running bootstrap..."
  "${SCRIPT_DIR}/bootstrap-odoo-infra.sh"
fi

# ------------------------------------------------------------------------------
# 4. Start the manager (default action is the interactive TUI)
# ------------------------------------------------------------------------------
if [[ ${#ARGS[@]} -eq 0 ]]; then
  ARGS=(--action tui)
fi

log_info "Starting Odoo Infrastructure Manager..."
cd "${ROOT}" && exec "${PYTHON}" -m app.main "${ARGS[@]}" 2>/dev/null || exec "${PYTHON}" manage.py infra_run --action "${ARGS[*]}" 2>/dev/null || exec "${PYTHON}" -c "from infrastructure_core.app import main; import sys; sys.argv=['main']+${ARGS[@]}; main.main()"
