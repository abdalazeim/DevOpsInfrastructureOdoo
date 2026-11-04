#!/usr/bin/env bash
# ==============================================================================
# Odoo Multi-Version Deployment - List Backups Script
# Lists all available backups with details
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BACKUP_ROOT="${1:-/data/backups}"
ODOO_VERSION="${2:-all}"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[i]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }

echo -e "${BLUE}================================================================================${NC}"
echo "Available backups - Odoo Multi-Version Deployment"
echo "Backup root: ${BACKUP_ROOT}"
echo -e "${BLUE}================================================================================${NC}"
echo ""

if [ ! -d "${BACKUP_ROOT}" ]; then
    print_info "Backup directory not found: ${BACKUP_ROOT}"
    exit 0
fi

# List backups for each version
for version in odoo17 odoo18 odoo19; do
    if [ "${ODOO_VERSION}" != "all" ] && [ "${ODOO_VERSION}" != "${version}" ]; then
        continue
    fi

    VERSION_DIR="${BACKUP_ROOT}/${version}"
    if [ ! -d "${VERSION_DIR}" ]; then
        continue
    fi

    echo -e "${GREEN}📦 Version: ${version}${NC}"
    echo "--------------------------------------------------------------------------------"

    for instance_dir in "${VERSION_DIR}"/*/; do
        if [ ! -d "${instance_dir}" ]; then
            continue
        fi

        instance_name=$(basename "${instance_dir}")

        for backup_dir in "${instance_dir}"/*/; do
            if [ ! -d "${backup_dir}" ]; then
                continue
            fi

            backup_name=$(basename "${backup_dir}")

            # Read info from manifest.json if available
            if [ -f "${backup_dir}/manifest.json" ]; then
                backup_type=$(python3 -c "import json; print(json.load(open('${backup_dir}/manifest.json')).get('backup_type', 'unknown'))" 2>/dev/null || echo "unknown")
                created_at=$(python3 -c "import json; print(json.load(open('${backup_dir}/manifest.json')).get('created_at', 'unknown'))" 2>/dev/null || echo "unknown")
                database=$(python3 -c "import json; print(json.load(open('${backup_dir}/manifest.json')).get('database', 'unknown'))" 2>/dev/null || echo "unknown")
                status=$(python3 -c "import json; print(json.load(open('${backup_dir}/manifest.json')).get('status', 'unknown'))" 2>/dev/null || echo "unknown")
            else
                backup_type="unknown"
                created_at="unknown"
                database="unknown"
                status="unknown"
            fi

            # Calculate backup size
            backup_size=$(du -sh "${backup_dir}" 2>/dev/null | cut -f1 || echo "unknown")

            echo ""
            echo "  📁 Backup: ${backup_name}"
            echo "     Instance: ${instance_name}"
            echo "     Backup type: ${backup_type}"
            echo "     Date: ${created_at}"
            echo "     Database: ${database}"
            echo "     Status: ${status}"
            echo "     Size: ${backup_size}"
            echo "     Path: ${backup_dir}"
        done
    done
    echo ""
done

echo -e "${BLUE}================================================================================${NC}"
print_success "All available backups listed"
exit 0