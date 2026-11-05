#!/usr/bin/env bash
# ==============================================================================
# Odoo Multi-Version Deployment - Ubuntu System Configuration Restore
# Restore Ubuntu system configuration after reinstallation
# Staged and safe - does not restore sensitive settings blindly
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BACKUP_ROOT="/data/backups/system-config"
TIMESTAMP="${1:-}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_error() { echo -e "${RED}[✗]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_info() { echo -e "${BLUE}[i]${NC} $1"; }

# Verify parameters
if [[ -z "$TIMESTAMP" ]]; then
    print_error "Backup timestamp must be specified for restore."
    echo "Usage: $0 <TIMESTAMP>"
    echo "Example: $0 2026-11-04_020000"
    echo ""
    print_info "Available backups:"
    if [[ -d "$BACKUP_ROOT" ]]; then
        ls -1 "$BACKUP_ROOT" 2>/dev/null || true
    fi
    exit 1
fi

# Check root privileges
if [[ $EUID -ne 0 ]]; then
    print_error "This script must be run with root privileges (sudo)."
    exit 1
fi

BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"

if [[ ! -d "$BACKUP_DIR" ]]; then
    print_error "Backup not found: $BACKUP_DIR"
    exit 1
fi

echo -e "${BLUE}======================================${NC}"
echo " Ubuntu System Configuration Restore"
echo "======================================"
echo "Backup: $TIMESTAMP"
echo "Directory: $BACKUP_DIR"
echo -e "${BLUE}======================================${NC}"
echo ""

# Verify backup integrity
print_info "Verifying backup integrity..."
if [[ -f "$BACKUP_DIR/checksums.sha256" ]]; then
    cd "$BACKUP_DIR"
    if sha256sum -c checksums.sha256 >/dev/null 2>&1; then
        print_success "File integrity verification succeeded"
    else
        print_error "File integrity verification failed"
        exit 1
    fi
else
    print_warning "checksums.sha256 not found, skipping integrity verification"
fi

# Read backup info
if [[ -f "$BACKUP_DIR/manifest.json" ]]; then
    print_info "Backup info:"
    python3 -c "import json; m=json.load(open('$BACKUP_DIR/manifest.json')); print(f'  type: {m.get(\"backup_type\")}'); print(f'  date: {m.get(\"created_at\")}'); print(f'  hostname: {m.get(\"hostname\")}'); print(f'  OS: {m.get(\"operating_system\")}')" 2>/dev/null || true
fi

echo ""
print_warning "Important security warning:"
print_warning "1. Do not restore Netplan, SSH, or fstab settings blindly."
print_warning "2. Network cards, disk UUIDs, or IP addresses may change after OS reinstallation."
print_warning "3. Blind restoration may cause loss of server access."
print_warning "4. Restore is staged - you can choose what to restore."
echo ""

# Phase 1: Disk info and partitions
echo -e "${BLUE}Phase 1: Disk info and partitions${NC}"
print_info "Displaying disk info from backup..."
cat "$BACKUP_DIR/system-info/lsblk.txt" 2>/dev/null || true
cat "$BACKUP_DIR/system-info/findmnt.txt" 2>/dev/null || true
echo ""
read -p "Continue to next phase? (yes/no): " CONFIRM_PHASE1
if [[ "$CONFIRM_PHASE1" != "yes" ]]; then
    print_warning "Restore cancelled by user."
    exit 0
fi

# Phase 2: /etc/fstab after UUID matching
echo -e "${BLUE}Phase 2: /etc/fstab${NC}"
print_warning "Verify disk UUIDs match before restoring fstab."
print_info "fstab content from backup:"
cat "$BACKUP_DIR/etc/fstab" 2>/dev/null || true
echo ""
read -p "Restore /etc/fstab? (yes/no): " CONFIRM_FSTAB
if [[ "$CONFIRM_FSTAB" == "yes" ]]; then
    cp -a "$BACKUP_DIR/etc/fstab" /etc/fstab
    print_success "/etc/fstab restored"
else
    print_warning "/etc/fstab skipped"
fi

# Phase 3: Netplan settings
echo -e "${BLUE}Phase 3: Netplan settings${NC}"
print_warning "Verify network cards and IP addresses before restoring Netplan."
print_info "Netplan files from backup:"
ls -la "$BACKUP_DIR/etc/netplan/" 2>/dev/null || true
echo ""
read -p "Restore Netplan settings? (yes/no): " CONFIRM_NETPLAN
if [[ "$CONFIRM_NETPLAN" == "yes" ]]; then
    mkdir -p /etc/netplan
    cp -a "$BACKUP_DIR/etc/netplan/." /etc/netplan/
    print_success "Netplan settings restored"
else
    print_warning "Netplan settings skipped"
fi

# Phase 4: SSH settings
echo -e "${BLUE}Phase 4: SSH settings${NC}"
print_warning "Verify host keys before restoring SSH settings."
print_info "SSH directory from backup:"
ls -la "$BACKUP_DIR/etc/ssh/" 2>/dev/null || true
echo ""
read -p "Restore SSH settings? (yes/no): " CONFIRM_SSH
if [[ "$CONFIRM_SSH" == "yes" ]]; then
    mkdir -p /etc/ssh
    cp -a "$BACKUP_DIR/etc/ssh/." /etc/ssh/
    chmod 600 /etc/ssh/ssh_host_*_key 2>/dev/null || true
    print_success "SSH settings restored"
else
    print_warning "SSH settings skipped"
fi

# Phase 5: Docker Daemon
echo -e "${BLUE}Phase 5: Docker Daemon${NC}"
print_info "Docker settings from backup:"
ls -la "$BACKUP_DIR/etc/docker/" 2>/dev/null || true
echo ""
read -p "Restore Docker Daemon settings? (yes/no): " CONFIRM_DOCKER
if [[ "$CONFIRM_DOCKER" == "yes" ]]; then
    mkdir -p /etc/docker
    cp -a "$BACKUP_DIR/etc/docker/." /etc/docker/
    print_success "Docker Daemon settings restored"
else
    print_warning "Docker Daemon settings skipped"
fi

# Phase 6: /opt projects
echo -e "${BLUE}Phase 6: /opt projects${NC}"
print_info "/opt directories from backup:"
ls -la "$BACKUP_DIR/opt/" 2>/dev/null || true
echo ""
read -p "Restore /opt directory? (yes/no): " CONFIRM_OPT
if [[ "$CONFIRM_OPT" == "yes" ]]; then
    mkdir -p /opt
    cp -a "$BACKUP_DIR/opt/." /opt/
    print_success "/opt directory restored"
else
    print_warning "/opt directory skipped"
fi

# Phase 7: systemd services and cron jobs
echo -e "${BLUE}Phase 7: systemd services and cron jobs${NC}"
print_info "Services and cron from backup:"
ls -la "$BACKUP_DIR/etc/systemd/system/" 2>/dev/null || true
ls -la "$BACKUP_DIR/etc/cron.d/" 2>/dev/null || true
echo ""
read -p "Restore services and cron jobs? (yes/no): " CONFIRM_SERVICES
if [[ "$CONFIRM_SERVICES" == "yes" ]]; then
    mkdir -p /etc/systemd/system /etc/cron.d
    cp -a "$BACKUP_DIR/etc/systemd/system/." /etc/systemd/system/ 2>/dev/null || true
    cp -a "$BACKUP_DIR/etc/cron.d/." /etc/cron.d/ 2>/dev/null || true
    systemctl daemon-reload 2>/dev/null || true
    print_success "Services and cron jobs restored"
else
    print_warning "Services and cron jobs skipped"
fi

# Phase 8: System status check
echo -e "${BLUE}Phase 8: System status check${NC}"
print_info "Checking system status after restore..."
hostnamectl 2>/dev/null || true
ip address 2>/dev/null || true
docker version 2>/dev/null || true
docker compose version 2>/dev/null || true
echo ""
print_success "Restore completed for selected phases."
print_info "Reboot recommended after restoring network and SSH settings."

exit 0