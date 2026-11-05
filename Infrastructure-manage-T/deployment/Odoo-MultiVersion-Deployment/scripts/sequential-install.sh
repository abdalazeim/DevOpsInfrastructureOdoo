#!/usr/bin/env bash
# ==============================================================================
# Sequential Component Installation & Report
#
# Installs all system components sequentially with full error tracking.
# Continues on failure and generates a comprehensive final report.
#
# Usage:
#   sudo bash scripts/sequential-install.sh          # interactive mode
#   sudo bash scripts/sequential-install.sh --dry-run # preview only
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT_DIR="$(cd "${PROJECT_DIR}/.." && pwd)"

DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run|-d) DRY_RUN=1 ;;
        --help|-h)
            echo "Usage: $0 [--dry-run] [--help]"
            exit 0
            ;;
    esac
done

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: This script requires root privileges (sudo)."
    echo "Usage: sudo $0"
    exit 1
fi

LOG_DIR="/var/log/odoo-installer"
mkdir -p "${LOG_DIR}"

# Find the Python executable
if [[ -f "${ROOT_DIR}/venv/bin/python" ]]; then
    PYTHON="${ROOT_DIR}/venv/bin/python"
else
    PYTHON="python3"
fi

cd "${ROOT_DIR}"

echo "============================================================"
echo "  SEQUENTIAL COMPONENT INSTALLATION"
echo "============================================================"
echo ""
echo "Project directory: ${ROOT_DIR}"
echo "Log directory:     ${LOG_DIR}"
echo "Dry run:           ${DRY_RUN}"
echo ""

if [[ ${DRY_RUN} -eq 1 ]]; then
    "${PYTHON}" -m app.main --action sequential-install --dry-run
else
    "${PYTHON}" -m app.main --action sequential-install
fi

EXIT_CODE=$?

echo ""
echo "============================================================"
echo "  Installation finished with exit code: ${EXIT_CODE}"
echo "============================================================"

exit "${EXIT_CODE}"
