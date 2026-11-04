#!/usr/bin/env bash
# ==============================================================================
# Odoo Multi-Version Deployment - Bootstrap Infrastructure
# يثبت جميع الملاحقات ويهيئ البيئة قبل تشغيل المشروع
# Installs all dependencies and prepares the environment for the project
# ==============================================================================
set -Eeuo pipefail

# ألوان الإخراج
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}================================================================${NC}"
    echo ""
}

print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_error()   { echo -e "${RED}[✗]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_info()    { echo -e "${BLUE}[i]${NC} $1"; }

# التحقق من صلاحيات الجذر
if [[ $EUID -ne 0 ]]; then
    print_error "هذا السكربت يتطلب صلاحيات الجذر (root/sudo)."
    echo ""
    echo "الاستخدام: sudo $0"
    echo "أو:         bash $0 (مع sudo)"
    exit 1
fi

# تحديد المسارات ديناميكياً
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BOOTSTRAP_LOG="/var/log/odoo-bootstrap.log"

print_header "Odoo Multi-Version Deployment - Bootstrap"
print_info "بدء تثبيت الملاحقات وإعداد البيئة..."
print_info "مجلد المشروع: ${PROJECT_DIR}"
print_info "ملف السجل: ${BOOTSTRAP_LOG}"

# إعادة توجيه المخرجات إلى ملف السجل والشاشة معًا
exec > >(tee -a "${BOOTSTRAP_LOG}") 2>&1

# ==============================================================================
# الخطوة 1: تحديث النظام وتثبيت الحزم الأساسية
# ==============================================================================
print_header "الخطوة 1: تحديث النظام وتثبيت الحزم الأساسية"

print_info "تحديث فهرس الحزم..."
if apt-get update -y >/dev/null 2>&1; then
    print_success "تم تحديث فهرس الحزم"
else
    print_warning "فشل تحديث فهرس الحزم (قد لا يوجد اتصال بالإنترنت)"
fi

print_info "تثبيت الحزم الأساسية..."
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    curl wget gnupg software-properties-common apt-transport-https \
    ca-certificates python3 python3-pip python3-venv git vim sudo ufw jq tar gzip zstd \
    >/dev/null 2>&1 || {
    print_error "فشل تثبيت بعض الحزم الأساسية"
    exit 1
}
print_success "تم تثبيت الحزم الأساسية بنجاح"

# ==============================================================================
# الخطوة 2: تثبيت Docker Engine
# ==============================================================================
print_header "الخطوة 2: تثبيت Docker Engine"

if command -v docker >/dev/null 2>&1; then
    print_success "Docker مثبت بالفعل: $(docker --version)"
else
    print_info "تثبيت Docker Engine من المستودع الرسمي..."
    install -m 0755 -d /etc/apt/keyrings 2>/dev/null || true
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null || true
    chmod a+r /etc/apt/keyrings/docker.gpg 2>/dev/null || true

    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        | tee /etc/apt/sources.list.d/docker.list >/dev/null

    apt-get update -y >/dev/null 2>&1 || true
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin \
        >/dev/null 2>&1 || {
        print_error "فشل تثبيت Docker Engine"
        exit 1
    }

    systemctl enable docker >/dev/null 2>&1 || true
    systemctl start docker >/dev/null 2>&1 || true
    print_success "تم تثبيت Docker Engine بنجاح"
fi

print_info "إصدار Docker: $(docker --version)"
print_info "إصدار Docker Compose: $(docker compose version 2>/dev/null || echo 'غير متاح')"

# إضافة المستخدم الحالي لمجموعة Docker
if [[ -n "${SUDO_USER:-}" ]]; then
    usermod -aG docker "${SUDO_USER}" 2>/dev/null || true
    print_info "تم إضافة المستخدم ${SUDO_USER} لمجموعة docker"
fi

usermod -aG docker odoo 2>/dev/null || true

# ==============================================================================
# الخطوة 3: تثبيت Ansible
# ==============================================================================
print_header "الخطوة 3: تثبيت Ansible ومجموعاتansible"

if command -v ansible-playbook >/dev/null 2>&1; then
    print_success "Ansible مثبت بالفعل: $(ansible-playbook --version | head -1)"
else
    print_info "تثبيت Ansible عبر pip3..."
    python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
    python3 -m pip install ansible >/dev/null 2>&1 || {
        print_error "فشل تثبيت Ansible عبر pip3"
        exit 1
    }
    print_success "تم تثبيت Ansible بنجاح"
fi

print_info "إصدار Ansible: $(ansible-playbook --version | head -1)"

# ==============================================================================
# الخطوة 4: تثبيت مجموعات Ansible المطلوبة
# ==============================================================================
print_header "الخطوة 4: تثبيت مجموعات Ansible المطلوبة"

REQUIREMENTS_FILE="${PROJECT_DIR}/requirements.yml"
if [[ -f "${REQUIREMENTS_FILE}" ]]; then
    print_info "تثبيت المجموعات من ملف requirements.yml..."
    ansible-galaxy collection install -r "${REQUIREMENTS_FILE}" 2>&1 | tail -10
    print_success "تم تثبيت مجموعات Ansible بنجاح"
else
    print_warning "ملف requirements.yml غير موجود. تثبيت المجموعات يدوياً..."
    ansible-galaxy collection install community.docker:3.8.0 2>&1 | tail -3 || true
    ansible-galaxy collection install community.general:7.4.0 2>&1 | tail -3 || true
    ansible-galaxy collection install ansible.posix:1.5.4 2>&1 | tail -3 || true
fi

print_info "المجموعات المثبتة:"
ansible-galaxy collection list 2>/dev/null | grep -E "community.docker|community.general|ansible.posix" || true

# ==============================================================================
# الخطوة 5: إنشاء المجلدات والبنية الأساسية
# ==============================================================================
print_header "الخطوة 5: إنشاء المجلدات والبنية الأساسية"

DIRS=(
    "/opt"
    "/data"
    "/data/backups"
    "/opt/odoo17" "/opt/odoo19"
    "/data/odoo17" "/data/odoo19"
    "/data/backups/odoo17" "/data/backups/odoo19"
    "/data/backups/infrastructure" "/data/backups/jenkins" "/data/backups/reports"
)

for dir in "${DIRS[@]}"; do
    if [[ ! -d "${dir}" ]]; then
        mkdir -p "${dir}"
        print_info "تم إنشاء المجلد: ${dir}"
    fi
done

# إنشاء مجلداتinstancestين لكل إصدار
for version in odoo17 odoo19; do
    for instance in instance1 instance2; do
        mkdir -p "/data/${version}/${instance}/postgresql"
        mkdir -p "/opt/${version}/${instance}/etc"
        mkdir -p "/opt/${version}/${instance}/addons"
    done
done
print_success "تم إنشاء جميع المجلدات الأساسية"

# ==============================================================================
# الخطوة 6: إعداد الصلاحيات
# ==============================================================================
print_header "الخطوة 6: إعداد الصلاحيات والملفات"

chmod 755 /opt/odoo17 /data/odoo17 /data/backups/odoo17 2>/dev/null || true
chmod 755 /opt/odoo19 /data/odoo19 /data/backups/odoo19 2>/dev/null || true
chmod 700 /data/odoo17/instance1/postgresql /data/odoo17/instance2/postgresql 2>/dev/null || true
chmod 700 /data/odoo19/instance1/postgresql /data/odoo19/instance2/postgresql 2>/dev/null || true

if ! id "odoo" >/dev/null 2>&1; then
    useradd -r -s /usr/sbin/nologin -d /var/lib/odoo odoo 2>/dev/null || true
    print_info "تم إنشاء مستخدم النظام odoo"
fi
usermod -aG docker odoo 2>/dev/null || true

print_success "تم ضبط الصلاحيات بنجاح"

# ==============================================================================
# الخطوة 7: إنشاء شبكة Docker proxy
# ==============================================================================
print_header "الخطوة 7: إنشاء شبكة Docker proxy"

DOCKER_NETWORK="proxy"
DOCKER_SUBNET="172.28.0.0/16"

if docker network inspect "${DOCKER_NETWORK}" >/dev/null 2>&1; then
    print_success "شبكة Docker ${DOCKER_NETWORK} موجودة بالفعل"
else
    print_info "إنشاء شبكة Docker ${DOCKER_NETWORK}..."
    docker network create \
        --driver bridge \
        --subnet "${DOCKER_SUBNET}" \
        "${DOCKER_NETWORK}" >/dev/null 2>&1 || {
        print_warning "فشل إنشاء الشبكة مع subnet محدد، محاولة subnet افتراضي..."
        docker network create --driver bridge "${DOCKER_NETWORK}" >/dev/null 2>&1 || {
            print_error "فشل إنشاء شبكة Docker proxy"
            exit 1
        }
    }
    print_success "تم إنشاء شبكة Docker ${DOCKER_NETWORK}"
fi

# ==============================================================================
# الخطوة 8: جعل سكريبتات المشروع قابلة للتنفيذ
# ==============================================================================
print_header "الخطوة 8: جعل سكريبتات المشروع قابلة للتنفيذ"

if [[ -d "${PROJECT_DIR}/scripts" ]]; then
    chmod +x "${PROJECT_DIR}/scripts"/*.sh 2>/dev/null || true
    print_success "تم جعل سكريبتات المشروع قابلة للتنفيذ"
else
    print_warning "مجلد سكريبتات المشروع غير موجود: ${PROJECT_DIR}/scripts"
fi

# ==============================================================================
# الخطوة 9: التحقق من البيئة النهائية
# ==============================================================================
print_header "الخطوة 9: التحقق من البيئة النهائية"

ALL_OK=true

command -v docker >/dev/null 2>&1 && print_success "Docker: $(docker --version)" || { print_error "Docker غير مثبت"; ALL_OK=false; }
docker compose version >/dev/null 2>&1 && print_success "Docker Compose: $(docker compose version)" || { print_error "Docker Compose غير متاح"; ALL_OK=false; }
command -v ansible-playbook >/dev/null 2>&1 && print_success "Ansible: $(ansible-playbook --version | head -1)" || { print_error "Ansible غير مثبت"; ALL_OK=false; }
command -v python3 >/dev/null 2>&1 && print_success "Python3: $(python3 --version)" || { print_error "Python3 غير مثبت"; ALL_OK=false; }
command -v git >/dev/null 2>&1 && print_success "Git: $(git --version)" || { print_error "Git غير مثبت"; ALL_OK=false; }
docker network inspect "${DOCKER_NETWORK}" >/dev/null 2>&1 && print_success "شبكة Docker ${DOCKER_NETWORK}: موجودة" || { print_error "شبكة Docker ${DOCKER_NETWORK}: غير موجودة"; ALL_OK=false; }

if [[ -d "${PROJECT_DIR}" ]]; then
    print_success "مجلد المشروع: ${PROJECT_DIR} (موجود)"
else
    print_warning "مجلد المشروع: ${PROJECT_DIR} (غير موجود)"
fi

# ==============================================================================
# النهاية
# ==============================================================================
print_header "اكتمل إعداد البيئة"

if [[ "${ALL_OK}" == "true" ]]; then
    print_success "جميع الملاحقات مثبتة والبيئة جاهزة!"
    echo ""
    print_info "الخطوات التالية:"
    echo "  1. cd ${PROJECT_DIR}"
    echo "  2. sudo ./scripts/launch-odoo-infra.sh"
    echo ""
    print_info "أو تشغيل التثبيت مباشرة:"
    echo "  sudo ./scripts/install-odoo17.sh"
    echo "  sudo ./scripts/install-odoo19.sh"
else
    print_error "بعض المكونات لم يتم تثبيتها بنجاح. يرجى مراجعة الأخطاء أعلاه."
    exit 1
fi

echo ""
exit 0