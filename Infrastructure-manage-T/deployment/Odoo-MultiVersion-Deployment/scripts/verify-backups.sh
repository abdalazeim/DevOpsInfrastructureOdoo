#!/usr/bin/env bash
# ==============================================================================
# Odoo Multi-Version Deployment - Verify Backups Script
# Verifies integrity of all backups and manifest files
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BACKUP_ROOT="${1:-/data/backups}"
ODOO_VERSION="${2:-all}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_error() { echo -e "${RED}[✗]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_info() { echo -e "${BLUE}[i]${NC} $1"; }

ERRORS=0
TOTAL=0

echo -e "${BLUE}========================================${NC}"
echo "Verifying backups - Odoo Multi-Version"
echo "Backup root: ${BACKUP_ROOT}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Find all manifest.json files
MANIFESTS=$(find "${BACKUP_ROOT}" -name "manifest.json" -type f 2>/dev/null || true)

if [ -z "${MANIFESTS}" ]; then
    print_warning "No backups found in: ${BACKUP_ROOT}"
    exit 0
fi

for manifest in ${MANIFESTS}; do
    BACKUP_DIR=$(dirname "${manifest}")
    TOTAL=$((TOTAL + 1))

    echo ""
    print_info "Checking backup: ${BACKUP_DIR}"

    # Check essential files exist
    for file in database.dump filestore.tar.zst manifest.json checksums.sha256; do
        if [ -f "${BACKUP_DIR}/${file}" ]; then
            print_success "  Found: ${file}"
        else
            print_warning "  Missing: ${file}"
            ERRORS=$((ERRORS + 1))
        fi
    done

    # Verify checksums
    if [ -f "${BACKUP_DIR}/checksums.sha256" ]; then
        print_info "  Verifying checksums..."
        cd "${BACKUP_DIR}"
        if sha256sum -c checksums.sha256 >/dev/null 2>&1; then
            print_success "  Checksums valid"
        else
            print_error "  Checksums invalid"
            ERRORS=$((ERRORS + 1))
        fi
    fi

    # Verify manifest.json is valid JSON
    if [ -f "${BACKUP_DIR}/manifest.json" ]; then
        if python3 -m json.tool "${BACKUP_DIR}/manifest.json" >/dev/null 2>&1; then
            print_success "  manifest.json valid"
        else
            print_error "  manifest.json invalid"
            ERRORS=$((ERRORS + 1))
        fi
    fi
done

echo ""
echo -e "${BLUE}========================================${NC}"
echo "Verification results:"
echo "Total backups checked: ${TOTAL}"
if [ ${ERRORS} -eq 0 ]; then
    print_success "All backups are healthy (0 errors)"
else
    print_error "${ERRORS} errors found in backups"
fi
echo -e "${BLUE}========================================${NC}"

exit ${ERRORS}