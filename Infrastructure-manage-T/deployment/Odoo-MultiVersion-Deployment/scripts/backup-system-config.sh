#!/bin/bash
# ==============================================================================
# Odoo Multi-Version Deployment - Ubuntu System Configuration Backup
# نسخة احتياطية مستقلة لإعدادات نظام Ubuntu والبنية التحتية
# منفصلة عن نسخ قواعد بيانات Odoo وملفاتها
# ==============================================================================
set -Eeuo pipefail

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

# التحقق من صلاحيات الجذر
if [[ $EUID -ne 0 ]]; then
    print_error "يجب تشغيل السكربت بصلاحيات الجذر (sudo)."
    exit 1
fi

echo -e "${BLUE}======================================${NC}"
echo " Ubuntu System Configuration Backup"
echo "======================================"
echo ""

# إنشاء المجلدات
mkdir -p "$BACKUP_DIR"

# المسارات المطلوب حفظها
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

print_info "نسخ الملفات والمجلدات المطلوبة..."
for ITEM in "${PATHS[@]}"; do
    if [[ -e "/$ITEM" ]]; then
        mkdir -p "$BACKUP_DIR/$(dirname "$ITEM")"
        cp -a "/$ITEM" "$BACKUP_DIR/$ITEM"
        print_success "[OK] $ITEM"
    else
        print_warning "[SKIP] $ITEM غير موجود"
    fi
done

# ملفات النظام المهمة
print_info "نسخ ملفات النظام الأساسية..."
mkdir -p "$BACKUP_DIR/etc"

for FILE in hostname hosts fstab; do
    if [[ -f "/etc/$FILE" ]]; then
        cp -a "/etc/$FILE" "$BACKUP_DIR/etc/"
        print_success "[OK] /etc/$FILE"
    else
        print_warning "[SKIP] /etc/$FILE غير موجود"
    fi
done

# معلومات النظام والأقراص
print_info "جمع معلومات النظام والأقراص..."
mkdir -p "$BACKUP_DIR/system-info"

hostnamectl > "$BACKUP_DIR/system-info/hostnamectl.txt" 2>/dev/null || true
lsblk -f > "$BACKUP_DIR/system-info/lsblk.txt" 2>/dev/null || true
findmnt > "$BACKUP_DIR/system-info/findmnt.txt" 2>/dev/null || true
df -hT > "$BACKUP_DIR/system-info/disk-usage.txt" 2>/dev/null || true
ip address > "$BACKUP_DIR/system-info/ip-address.txt" 2>/dev/null || true
ip route > "$BACKUP_DIR/system-info/ip-route.txt" 2>/dev/null || true
docker version > "$BACKUP_DIR/system-info/docker-version.txt" 2>&1 || true
docker compose version > "$BACKUP_DIR/system-info/compose-version.txt" 2>&1 || true

# قائمة الحزم المثبتة
print_info "قائمة الحزم المثبتة..."
dpkg-query -W -f='${binary:Package}\t${Version}\n' \
    > "$BACKUP_DIR/packages.txt" 2>/dev/null || true

# ملف معلومات النسخة (manifest.json)
print_info "إنشاء ملف معلومات النسخة (manifest.json)..."
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

# بصمات سلامة الملفات (checksums)
print_info "إنشاء بصمات سلامة الملفات (SHA256)..."
cd "$BACKUP_DIR"
find . -type f ! -name checksums.sha256 -print0 \
    | sort -z \
    | xargs -0 sha256sum > checksums.sha256
print_success "تم إنشاء checksums.sha256"

# إنشاء أرشيف مضغوط
print_info "إنشاء أرشيف مضغوط..."
ARCHIVE_PATH="$BACKUP_ROOT/system-config-$TIMESTAMP.tar.gz"
tar --acls --xattrs -czf \
    "$ARCHIVE_PATH" \
    -C "$BACKUP_ROOT" "$TIMESTAMP"
print_success "تم إنشاء الأرشيف: $ARCHIVE_PATH"

# تشفير الأرشيف إذا كان مطلوبًا
if [[ "$ENCRYPT" == "true" ]]; then
    if [[ -z "$ENCRYPT_PASSWORD" ]]; then
        print_warning "لم يتم تحديد كلمة مرور للتشفير، يتم تخطي التشفير."
    else
        print_info "تشفير الأرشيف..."
        echo "$ENCRYPT_PASSWORD" | gpg --batch --yes --passphrase-fd 0 -c "$ARCHIVE_PATH"
        rm -f "$ARCHIVE_PATH"
        ARCHIVE_PATH="$ARCHIVE_PATH.gpg"
        print_success "تم تشفير الأرشيف: $ARCHIVE_PATH"
    fi
fi

# تنظيف المجلد المؤقت (اختياري، يمكن الاحتفاظ به للمراجعة)
print_info "تنظيف المجلد المؤقت (اختياري)..."
# يمكن ترك المجلد للمراجعة أو حذفه لتوفير المساحة

echo ""
echo -e "${BLUE}======================================${NC}"
echo " BACKUP COMPLETED"
echo -e "${BLUE}======================================${NC}"
echo "المجلد: $BACKUP_DIR"
echo "الأرشيف: $ARCHIVE_PATH"
if [[ "$ENCRYPT" == "true" ]]; then
    echo "الحالة: مشفر"
fi
echo -e "${BLUE}======================================${NC}"

print_warning "تنبيه أمني: archiv غير مشفر قد يحتوي على مفاتيح SSH وكلمات مرور."
print_warning "يُستخدم التشفير (ENCRYPT=true) قبل نقل الأرشيف خارج الخادم."

exit 0