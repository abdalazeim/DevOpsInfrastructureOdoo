#!/bin/bash
# ==============================================================================
# Odoo Multi-Version Deployment - Ubuntu System Configuration Restore
# استعادة إعدادات نظام Ubuntu بعد إعادة التثبيت
# مرحلية وآمنة - لا تستعيد الإعدادات الحساسة بشكل أعمى
# ==============================================================================
set -Eeuo pipefail

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

# التحقق من المعلمات
if [[ -z "$TIMESTAMP" ]]; then
    print_error "يجب تحديد تاريخ النسخة الاحتياطية للاستعادة."
    echo "الاستخدام: $0 <TIMESTAMP>"
    echo "مثال: $0 2026-11-04_020000"
    echo ""
    print_info "النسخ المتوفرة:"
    if [[ -d "$BACKUP_ROOT" ]]; then
        ls -1 "$BACKUP_ROOT" 2>/dev/null || true
    fi
    exit 1
fi

# التحقق من صلاحيات الجذر
if [[ $EUID -ne 0 ]]; then
    print_error "يجب تشغيل السكربت بصلاحيات الجذر (sudo)."
    exit 1
fi

BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"

if [[ ! -d "$BACKUP_DIR" ]]; then
    print_error "النسخة الاحتياطية غير موجودة: $BACKUP_DIR"
    exit 1
fi

echo -e "${BLUE}======================================${NC}"
echo " Ubuntu System Configuration Restore"
echo "======================================"
echo "النسخة: $TIMESTAMP"
echo "المجلد: $BACKUP_DIR"
echo -e "${BLUE}======================================${NC}"
echo ""

# التحقق من سلامة النسخة
print_info "التحقق من سلامة النسخة الاحتياطية..."
if [[ -f "$BACKUP_DIR/checksums.sha256" ]]; then
    cd "$BACKUP_DIR"
    if sha256sum -c checksums.sha256 >/dev/null 2>&1; then
        print_success "التحقق من سلامة الملفات نجح"
    else
        print_error "فشل التحقق من سلامة الملفات"
        exit 1
    fi
else
    print_warning "ملف checksums.sha256 غير موجود، تخطي التحقق من السلامة"
fi

# قراءة معلومات النسخة
if [[ -f "$BACKUP_DIR/manifest.json" ]]; then
    print_info "معلومات النسخة:"
    python3 -c "import json; m=json.load(open('$BACKUP_DIR/manifest.json')); print(f'  النوع: {m.get(\"backup_type\")}'); print(f'  التاريخ: {m.get(\"created_at\")}'); print(f'  المضيف: {m.get(\"hostname\")}'); print(f'  النظام: {m.get(\"operating_system\")}')" 2>/dev/null || true
fi

echo ""
print_warning "تنبيه أمني مهم:"
print_warning "1. لا تستعيد إعدادات Netplan أو SSH أو fstab بشكل أعمى."
print_warning "2. قد تتغير بطاقة الشبكة أو UUID الأقراص أو عناوين IP بعد إعادة التثبيت."
print_warning "3. قد يؤدي الاستعادة العمياء إلى فقدان الوصول إلى الخادم."
print_warning "4. الاستعادة مرحلية - يمكنك اختيار ما تستعيد."
echo ""

# مرحلة 1: معلومات الأقراص وتقسيماتها
echo -e "${BLUE}المرحلة 1: معلومات الأقراص وتقسيماتها${NC}"
print_info "عرض معلومات الأقراص من النسخة الاحتياطية:"
cat "$BACKUP_DIR/system-info/lsblk.txt" 2>/dev/null || true
cat "$BACKUP_DIR/system-info/findmnt.txt" 2>/dev/null || true
echo ""
read -p "هل تريد المتابعة إلى المرحلة التالية؟ (yes/no): " CONFIRM_PHASE1
if [[ "$CONFIRM_PHASE1" != "yes" ]]; then
    print_warning "تم إلغاء الاستعادة من قبل المستخدم."
    exit 0
fi

# مرحلة 2: /etc/fstab بعد مطابقة UUID
echo -e "${BLUE}المرحلة 2: /etc/fstab${NC}"
print_warning "تحقق من مطابقة UUID الأقراص قبل استعادة fstab."
print_info "محتوى fstab من النسخة الاحتياطية:"
cat "$BACKUP_DIR/etc/fstab" 2>/dev/null || true
echo ""
read -p "هل تريد استعادة /etc/fstab؟ (yes/no): " CONFIRM_FSTAB
if [[ "$CONFIRM_FSTAB" == "yes" ]]; then
    cp -a "$BACKUP_DIR/etc/fstab" /etc/fstab
    print_success "تم استعادة /etc/fstab"
else
    print_warning "تم تخطي /etc/fstab"
fi

# مرحلة 3: إعدادات Netplan
echo -e "${BLUE}المرحلة 3: إعدادات Netplan${NC}"
print_warning "تحقق من بطاقات الشبكة وعناوين IP قبل استعادة Netplan."
print_info "ملفات Netplan من النسخة الاحتياطية:"
ls -la "$BACKUP_DIR/etc/netplan/" 2>/dev/null || true
echo ""
read -p "هل تريد استعادة إعدادات Netplan؟ (yes/no): " CONFIRM_NETPLAN
if [[ "$CONFIRM_NETPLAN" == "yes" ]]; then
    cp -a "$BACKUP_DIR/etc/netplan/" /etc/netplan/
    print_success "تم استعادة إعدادات Netplan"
else
    print_warning "تم تخطي إعدادات Netplan"
fi

# مرحلة 4: إعدادات SSH
echo -e "${BLUE}المرحلة 4: إعدادات SSH${NC}"
print_warning "تحقق من مفاتيح المضيف قبل استعادة إعدادات SSH."
print_info "مجلد SSH من النسخة الاحتياطية:"
ls -la "$BACKUP_DIR/etc/ssh/" 2>/dev/null || true
echo ""
read -p "هل تريد استعادة إعدادات SSH؟ (yes/no): " CONFIRM_SSH
if [[ "$CONFIRM_SSH" == "yes" ]]; then
    cp -a "$BACKUP_DIR/etc/ssh/" /etc/ssh/
    chmod 600 /etc/ssh/ssh_host_*_key 2>/dev/null || true
    print_success "تم استعادة إعدادات SSH"
else
    print_warning "تم تخطي إعدادات SSH"
fi

# مرحلة 5: Docker Daemon
echo -e "${BLUE}المرحلة 5: Docker Daemon${NC}"
print_info "إعدادات Docker من النسخة الاحتياطية:"
ls -la "$BACKUP_DIR/etc/docker/" 2>/dev/null || true
echo ""
read -p "هل تريد استعادة إعدادات Docker Daemon؟ (yes/no): " CONFIRM_DOCKER
if [[ "$CONFIRM_DOCKER" == "yes" ]]; then
    cp -a "$BACKUP_DIR/etc/docker/" /etc/docker/
    print_success "تم استعادة إعدادات Docker Daemon"
else
    print_warning "تم تخطي إعدادات Docker Daemon"
fi

# مرحلة 6: مشاريع /opt
echo -e "${BLUE}المرحلة 6: مشاريع /opt${NC}"
print_info "مجلدات /opt من النسخة الاحتياطية:"
ls -la "$BACKUP_DIR/opt/" 2>/dev/null || true
echo ""
read -p "هل تريد استعادة مجلد /opt؟ (yes/no): " CONFIRM_OPT
if [[ "$CONFIRM_OPT" == "yes" ]]; then
    cp -a "$BACKUP_DIR/opt/" /opt/
    print_success "تم استعادة مجلد /opt"
else
    print_warning "تم تخطي مجلد /opt"
fi

# مرحلة 7: الخدمات والجداول المجدولة
echo -e "${BLUE}المرحلة 7: الخدمات والجداول المجدولة${NC}"
print_info "الخدمات والجداول من النسخة الاحتياطية:"
ls -la "$BACKUP_DIR/etc/systemd/system/" 2>/dev/null || true
ls -la "$BACKUP_DIR/etc/cron.d/" 2>/dev/null || true
echo ""
read -p "هل تريد استعادة الخدمات والجداول المجدولة؟ (yes/no): " CONFIRM_SERVICES
if [[ "$CONFIRM_SERVICES" == "yes" ]]; then
    cp -a "$BACKUP_DIR/etc/systemd/system/" /etc/systemd/system/ 2>/dev/null || true
    cp -a "$BACKUP_DIR/etc/cron.d/" /etc/cron.d/ 2>/dev/null || true
    systemctl daemon-reload 2>/dev/null || true
    print_success "تم استعادة الخدمات والجداول المجدولة"
else
    print_warning "تم تخطي الخدمات والجداول المجدولة"
fi

# مرحلة 8: فحص التشغيل والشبكة والحاويات
echo -e "${BLUE}المرحلة 8: فحص التشغيل والشبكة والحاويات${NC}"
print_info "فحص حالة النظام بعد الاستعادة..."
hostnamectl 2>/dev/null || true
ip address 2>/dev/null || true
docker version 2>/dev/null || true
docker compose version 2>/dev/null || true
echo ""
print_success "اكتملت عملية الاستعادة للمراحل المحددة."
print_info "يُوصى بإعادة تشغيل النظام بعد استعادة إعدادات الشبكة وSSH."

exit 0