#!/usr/bin/env bash
# ==============================================================================
# Odoo Multi-Version Deployment - Ubuntu System Configuration Backup
# Independent backup of Ubuntu system configuration and infrastructure
# Separate from Odoo database and file backups
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BACKUP_ROOT="/data/backups/system-config"
TIMESTAMP=$(date +"%Y-%m-%d_%H%M%S")
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"
ENCRYPT="${ENCRYPT:-false}"
ENCRYPT_PASSWORD="${ENCRYPT_PASSWORD:-}"
ARCHIVE_PATH=""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_error() { echo -e "${RED}[✗]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_info() { echo -e "${BLUE}[i]${NC} $1"; }

# Check root privileges
if [[ $EUID -ne 0 ]]; then
    print_error "This script must be run with root privileges (sudo)."
    exit 1
fi

echo -e "${BLUE}======================================${NC}"
echo " Ubuntu System Configuration Backup"
echo "======================================"
echo ""

# Create directories
mkdir -p "$BACKUP_DIR"

# Paths to backup
PATHS=(
    etc/netplan
    etc/ssh
    etc/docker
    etc/apt
    etc/systemd/system
    etc/cron.d
    etc/ufw
    opt
)

print_info "Copying required files and directories..."
for ITEM in "${PATHS[@]}"; do
    if [[ -e "/$ITEM" ]]; then
        mkdir -p "$BACKUP_DIR/$(dirname "$ITEM")"
        cp -a "/$ITEM" "$BACKUP_DIR/$ITEM"
        print_success "[OK] $ITEM"
    else
        print_warning "[SKIP] $ITEM not found"
    fi
done

# Important system files
print_info "Copying basic system files..."
mkdir -p "$BACKUP_DIR/etc"

for FILE in hostname hosts fstab; do
    if [[ -f "/etc/$FILE" ]]; then
        cp -a "/etc/$FILE" "$BACKUP_DIR/etc/"
        print_success "[OK] /etc/$FILE"
    else
        print_warning "[SKIP] /etc/$FILE not found"
    fi
done

# System and disk info
print_info "Collecting system and disk info..."
mkdir -p "$BACKUP_DIR/system-info"

hostnamectl > "$BACKUP_DIR/system-info/hostnamectl.txt" 2>/dev/null || true
lsblk -f > "$BACKUP_DIR/system-info/lsblk.txt" 2>/dev/null || true
findmnt > "$BACKUP_DIR/system-info/findmnt.txt" 2>/dev/null || true
df -hT > "$BACKUP_DIR/system-info/disk-usage.txt" 2>/dev/null || true
ip address > "$BACKUP_DIR/system-info/ip-address.txt" 2>/dev/null || true
ip route > "$BACKUP_DIR/system-info/ip-route.txt" 2>/dev/null || true
docker version > "$BACKUP_DIR/system-info/docker-version.txt" 2>&1 || true
docker compose version > "$BACKUP_DIR/system-info/compose-version.txt" 2>&1 || true

# Installed packages list
print_info "Listing installed packages..."
dpkg-query -W -f='${binary:Package}\t${Version}\n' \
    > "$BACKUP_DIR/packages.txt" 2>/dev/null || true

# Backup manifest
print_info "Creating backup manifest (manifest.json)..."
HOSTNAME_VAL=$(hostname 2>/dev/null || echo "unknown")
OS_PRETTY_NAME=$( . /etc/os-release && echo "$PRETTY_NAME" 2>/dev/null || echo "unknown")

cat > "$BACKUP_DIR/manifest.json" <<EOF
{
  "backup_type": "system_configuration",
  "created_at": "$TIMESTAMP",
  "hostname": "$HOSTNAME_VAL",
  "operating_system": "$OS_PRETTY_NAME",
  "backup_root": "$BACKUP_ROOT",
  "included_paths": [
    "/etc/netplan",
    "/etc/ssh",
    "/etc/fstab",
    "/etc/docker",
    "/opt"
  ],
  "included_files": [
    "/etc/hostname",
    "/etc/hosts",
    "/etc/fstab"
  ],
  "included_info": [
    "/etc/apt",
    "/etc/systemd/system",
    "/etc/cron.d",
    "/etc/ufw"
  ],
  "encryption": $ENCRYPT,
  "integrity_check": "sha256",
  "status": "completed"
}
EOF

# File integrity checksums (SHA256)
print_info "Creating file integrity checksums (SHA256)..."
cd "$BACKUP_DIR"
find . -type f ! -name checksums.sha256 -print0 \
    | sort -z \
    | xargs -0 sha256sum > checksums.sha256
print_success "checksums.sha256 created"

# Create compressed archive
print_info "Creating compressed archive..."
ARCHIVE_PATH="$BACKUP_ROOT/system-config-$TIMESTAMP.tar.gz"
tar --acls --xattrs -czf \
    "$ARCHIVE_PATH" \
    -C "$BACKUP_ROOT" "$TIMESTAMP"
print_success "Archive created: $ARCHIVE_PATH"

# Encrypt archive if requested
if [[ "$ENCRYPT" == "true" ]]; then
    if [[ -z "$ENCRYPT_PASSWORD" ]]; then
        print_warning "No encryption password specified, skipping encryption."
    else
        print_info "Encrypting archive..."
        echo "$ENCRYPT_PASSWORD" | gpg --batch --yes --passphrase-fd 0 -c "$ARCHIVE_PATH"
        rm -f "$ARCHIVE_PATH"
        ARCHIVE_PATH="$ARCHIVE_PATH.gpg"
        print_success "Archive encrypted: $ARCHIVE_PATH"
    fi
fi

# Cleanup temporary directory (optional)
print_info "Cleaning up temporary directory (optional)..."
# The directory can be kept for review or deleted to save space

echo ""
echo -e "${BLUE}======================================${NC}"
echo " BACKUP COMPLETED"
echo -e "${BLUE}======================================${NC}"
echo "Directory: $BACKUP_DIR"
echo "Archive: $ARCHIVE_PATH"
if [[ "$ENCRYPT" == "true" ]]; then
    echo "Status: Encrypted"
fi
echo -e "${BLUE}======================================${NC}"

print_warning "Security warning: Unencrypted archive may contain SSH keys and passwords."
print_warning "Use encryption (ENCRYPT=true) before transferring archive outside the server."

exit 0