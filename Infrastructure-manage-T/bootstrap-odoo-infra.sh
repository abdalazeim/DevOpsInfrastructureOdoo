#!/usr/bin/env bash
# ==============================================================================
# Odoo Infrastructure Manager - Environment Bootstrap
#
# Installs the Python virtual environment and project dependencies, creates a
# protected .env file from templates/env.template, and (optionally) installs
# Docker Engine / Ansible.
#
# Usage:
#   ./bootstrap-odoo-infra.sh                     # Python environment + .env only
#   ./bootstrap-odoo-infra.sh --install-docker    # also install Docker Engine
#   ./bootstrap-odoo-infra.sh --install-docker --docker-version 27.5.1
#   ./bootstrap-odoo-infra.sh --install-docker --docker-mirror https://mirror.localhost
#   ./bootstrap-odoo-infra.sh --with-ansible      # also install Ansible
#   ./bootstrap-odoo-infra.sh --skip-docker --skip-ansible
#   ./bootstrap-odoo-infra.sh --regenerate-env    # rotate all .env secrets
#   ./bootstrap-odoo-infra.sh --force-recreate    # rebuild the virtualenv
#
# Docker installation follows https://github.com/docker/docker-install:
# the official convenience script is downloaded to a temporary file first,
# then executed with the requested options (no `curl | sh` pipe).
# ==============================================================================
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${VENV_DIR:-${ROOT}/venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_DOCKER=0
WITH_ANSIBLE=0
FORCE_RECREATE=0
SKIP_DOCKER=0
SKIP_ANSIBLE=0
REGENERATE_ENV=0

log_info() { echo -e "\033[0;34m[INFO]\033[0m $*"; }
log_ok()   { echo -e "\033[0;32m[OK]\033[0m $*"; }
log_warn() { echo -e "\033[0;33m[WARN]\033[0m $*"; }
log_err()  { echo -e "\033[0;31m[ERROR]\033[0m $*" >&2; }

trap 'log_err "Bootstrap failed at line ${LINENO}. See the message above."' ERR

DOCKER_SCRIPT_URL="${DOCKER_SCRIPT_URL:-https://get.docker.com}"
DOCKER_VERSION=""
DOCKER_MIRROR=""
DOCKER_DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-docker)  INSTALL_DOCKER=1; shift ;;
    --with-ansible)    WITH_ANSIBLE=1; shift ;;
    --skip-docker)     SKIP_DOCKER=1; INSTALL_DOCKER=0; shift ;;
    --skip-ansible)    SKIP_ANSIBLE=1; WITH_ANSIBLE=0; shift ;;
    --regenerate-env)  REGENERATE_ENV=1; shift ;;
    --force-recreate)  FORCE_RECREATE=1; shift ;;
    --docker-version)  DOCKER_VERSION="$2"; shift 2 ;;
    --docker-mirror)   DOCKER_MIRROR="$2"; shift 2 ;;
    --docker-script-url) DOCKER_SCRIPT_URL="$2"; shift 2 ;;
    --docker-dry-run)  DOCKER_DRY_RUN=1; shift ;;
    -h|--help)
      sed -n '2,22p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      log_err "Unknown option: $1"
      exit 2
      ;;
  esac
done

if [[ "${EUID}" -eq 0 ]]; then
  SUDO=()
else
  if ! command -v sudo >/dev/null 2>&1; then
    log_err "sudo is required when not running as root."
    exit 1
  fi
  SUDO=(sudo)
fi

as_root() {
  "${SUDO[@]}" "$@"
}

# ------------------------------------------------------------------------------
# 1. System packages required to build the virtual environment
# ------------------------------------------------------------------------------
REQUIRED_PKGS=(python3 python3-venv python3-pip ca-certificates curl git)
MISSING_PKGS=()

for pkg in "${REQUIRED_PKGS[@]}"; do
  if ! dpkg -s "${pkg}" >/dev/null 2>&1; then
    MISSING_PKGS+=("${pkg}")
  fi
done

if [[ ${#MISSING_PKGS[@]} -gt 0 ]]; then
  log_info "Installing missing system packages: ${MISSING_PKGS[*]}"
  as_root apt-get update
  DEBIAN_FRONTEND=noninteractive as_root apt-get install -y "${MISSING_PKGS[@]}"
else
  log_ok "Required system packages are already installed."
fi

# ------------------------------------------------------------------------------
# 2. Python version check (>= 3.10, per pyproject.toml)
# ------------------------------------------------------------------------------
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  log_err "Python executable '${PYTHON_BIN}' was not found."
  exit 1
fi

PY_VERSION="$("${PYTHON_BIN}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if ! "${PYTHON_BIN}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
  log_err "Python >= 3.10 is required (detected ${PY_VERSION})."
  exit 1
fi
log_ok "Python ${PY_VERSION} detected."

# ------------------------------------------------------------------------------
# 3. Virtual environment
# ------------------------------------------------------------------------------
if [[ ${FORCE_RECREATE} -eq 1 && -d "${VENV}" ]]; then
  log_warn "Removing existing virtual environment at ${VENV}"
  rm -rf "${VENV}"
fi

if [[ ! -x "${VENV}/bin/python" ]]; then
  log_info "Creating virtual environment at ${VENV}"
  "${PYTHON_BIN}" -m venv "${VENV}"
else
  log_ok "Virtual environment already exists at ${VENV}"
fi

# ------------------------------------------------------------------------------
# 4. Python dependencies (single source of truth: pyproject.toml)
# ------------------------------------------------------------------------------
log_info "Upgrading pip, setuptools, and wheel..."
"${VENV}/bin/python" -m pip install --upgrade pip setuptools wheel

log_info "Installing project in editable mode (this can take a minute)..."
"${VENV}/bin/python" -m pip install -e "${ROOT}"

log_ok "Python dependencies installed."

# ------------------------------------------------------------------------------
# 5. Protected .env file with generated secrets
# ------------------------------------------------------------------------------
ENV_FILE="${ROOT}/.env"

generate_env() {
  log_info "Creating ${ENV_FILE} from templates/env.template"
  cp "${ROOT}/templates/env.template" "${ENV_FILE}"

  if command -v openssl >/dev/null 2>&1; then
    local odoo17_db_pass odoo17_admin_pass
    local odoo18_db_pass odoo18_admin_pass
    local odoo19_db_pass odoo19_admin_pass
    local pgadmin_pass traefik_user_pass traefik_hash

    odoo17_db_pass="$(openssl rand -hex 24)"
    odoo17_admin_pass="$(openssl rand -hex 24)"
    odoo18_db_pass="$(openssl rand -hex 24)"
    odoo18_admin_pass="$(openssl rand -hex 24)"
    odoo19_db_pass="$(openssl rand -hex 24)"
    odoo19_admin_pass="$(openssl rand -hex 24)"
    pgadmin_pass="$(openssl rand -hex 18)"
    traefik_user_pass="$(openssl rand -hex 18)"
    traefik_hash="$(openssl passwd -apr1 "${traefik_user_pass}" 2>/dev/null || true)"

    "${VENV}/bin/python" - "${ENV_FILE}" \
      "${odoo17_db_pass}" "${odoo17_admin_pass}" \
      "${odoo18_db_pass}" "${odoo18_admin_pass}" \
      "${odoo19_db_pass}" "${odoo19_admin_pass}" \
      "${pgadmin_pass}" \
      "${traefik_user_pass}" "${traefik_hash}" <<'PY'
import re
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
(
    o17_db, o17_admin,
    o18_db, o18_admin,
    o19_db, o19_admin,
    pgadmin_pass,
    tr_user_pass, tr_hash,
) = sys.argv[2:11]
text = env_path.read_text()
replacements = {
    "change_me_to_a_secure_postgres16_password": o17_db,
    "change_me_to_a_secure_odoo17_master_password": o17_admin,
    "change_me_to_a_secure_postgres17_password": o18_db,
    "change_me_to_a_secure_odoo18_master_password": o18_admin,
    "change_me_to_a_secure_postgres18_password": o19_db,
    "change_me_to_a_secure_odoo19_master_password": o19_admin,
    "change_me_to_a_secure_pgadmin_password": pgadmin_pass,
}
for old, new in replacements.items():
    text = text.replace(old, new)

if tr_hash:
    text = re.sub(
        r"^TRAEFIK_BASIC_AUTH=.*$",
        f"TRAEFIK_BASIC_AUTH='admin:{tr_hash}'",
        text,
        flags=re.MULTILINE,
    )

env_path.write_text(text)

if tr_hash:
    creds_path = env_path.parent / ".traefik_credentials"
    creds_path.write_text(f"username: admin\npassword: {tr_user_pass}\n")
    creds_path.chmod(0o600)
PY
  else
    log_warn "openssl is missing: the placeholder secrets in .env were NOT replaced."
    log_warn "Install openssl and re-run with --regenerate-env."
  fi

  chmod 600 "${ENV_FILE}"
  log_ok "Created ${ENV_FILE} with mode 0600."
  log_warn "Review ACME_EMAIL and the *_DOMAIN values in .env before deploying."
}

if [[ ${REGENERATE_ENV} -eq 1 ]]; then
  if [[ -f "${ENV_FILE}" ]]; then
    backup_env="${ENV_FILE}.bak.$(date +%Y%m%d_%H%M%S)"
    cp -p "${ENV_FILE}" "${backup_env}"
    chmod 600 "${backup_env}"
    log_warn "Existing .env backed up to ${backup_env}"
    rm -f "${ENV_FILE}"
  fi
  generate_env
elif [[ ! -f "${ENV_FILE}" ]]; then
  generate_env
else
  chmod 600 "${ENV_FILE}" 2>/dev/null || true
  log_ok "Existing ${ENV_FILE} preserved."
fi

# ------------------------------------------------------------------------------
# 6. Optional: Docker Engine
# ------------------------------------------------------------------------------
if [[ ${SKIP_DOCKER} -eq 1 ]]; then
  log_warn "Docker installation skipped (--skip-docker)."
elif [[ ${INSTALL_DOCKER} -eq 1 ]]; then
  if command -v docker >/dev/null 2>&1; then
    log_ok "Docker is already installed: $(docker --version)"
  else
    log_warn "Installing Docker Engine via the official docker/docker-install script..."
    log_warn "Review https://docs.docker.com/engine/install/ before using this on production hosts."

    DOCKER_TMP="$(mktemp -d)"
    trap 'rm -rf "${DOCKER_TMP}"' EXIT
    log_info "Downloading ${DOCKER_SCRIPT_URL}"
    curl -fsSL "${DOCKER_SCRIPT_URL}" -o "${DOCKER_TMP}/install-docker.sh"
    chmod +x "${DOCKER_TMP}/install-docker.sh"

    DOCKER_ARGS=()
    [[ -n "${DOCKER_VERSION}" ]] && DOCKER_ARGS+=(--version "${DOCKER_VERSION}")
    [[ -n "${DOCKER_MIRROR}" ]] && DOCKER_ARGS+=(--mirror "${DOCKER_MIRROR}")
    [[ ${DOCKER_DRY_RUN} -eq 1 ]] && DOCKER_ARGS+=(--dry-run)

    as_root sh "${DOCKER_TMP}/install-docker.sh" "${DOCKER_ARGS[@]}"

    if ! "${SUDO[@]}" systemctl enable --now docker; then
      log_warn "systemctl enable failed; start the Docker daemon manually if needed."
    fi
    if [[ "${EUID}" -ne 0 ]]; then
      as_root usermod -aG docker "${USER}"
      log_warn "Log out and back in (or run 'newgrp docker') so ${USER} can use Docker without sudo."
    fi

    if command -v docker >/dev/null 2>&1; then
      log_ok "Docker installed: $(docker --version)"
      if docker compose version >/dev/null 2>&1; then
        log_ok "Docker Compose plugin: $(docker compose version --short 2>/dev/null || docker compose version)"
      else
        log_warn "Docker Compose v2 plugin was not detected."
      fi
    fi
  fi
else
  if ! command -v docker >/dev/null 2>&1; then
    log_warn "Docker is not installed. Re-run with --install-docker or install it manually."
  else
    log_ok "Docker is available: $(docker --version)"
  fi
fi

# ------------------------------------------------------------------------------
# 7. Optional: Ansible
# ------------------------------------------------------------------------------
if [[ ${SKIP_ANSIBLE} -eq 1 ]]; then
  log_warn "Ansible installation skipped (--skip-ansible)."
elif [[ ${WITH_ANSIBLE} -eq 1 ]]; then
  if command -v ansible-playbook >/dev/null 2>&1; then
    log_ok "Ansible is already installed: $(ansible-playbook --version | head -n1)"
  else
    log_info "Installing Ansible..."
    as_root apt-get install -y ansible
  fi
fi

# ------------------------------------------------------------------------------
# 8. Make helper scripts executable and verify the import path
# ------------------------------------------------------------------------------
chmod +x "${ROOT}"/*.sh "${ROOT}"/automation/scripts/*.sh 2>/dev/null || true
"${VENV}/bin/python" -c 'import yaml, app.main' >/dev/null
log_ok "Python package imports successfully."

echo ""
echo "=============================================================================="
echo " Bootstrap complete"
echo "-----------------------------------------------------------------------------"
echo " Virtualenv : ${VENV}"
echo " Environment: ${ENV_FILE}"
echo ""
echo " Next steps:"
echo "   ./launch-odoo-infra.sh --action validate -p profiles/example.yaml"
echo "   ./launch-odoo-infra.sh --action preflight"
echo "   ./launch-odoo-infra.sh                     # interactive TUI"
echo "=============================================================================="
