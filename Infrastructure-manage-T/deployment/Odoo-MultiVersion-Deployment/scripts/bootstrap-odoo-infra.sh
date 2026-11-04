#!/bin/bash
# ==============================================================================
# Odoo Multi-Version Deployment - Bootstrap Infrastructure Script
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
    echo "الاستخدام: sudo $0"
    exit 1
fi

# متغيرات الإعداد
PROJECT_DIR="/opt/Odoo-MultiVersion-Deployment"
ANSIBLE_COLLECTIONS=(
    "community.docker:3.8.0"
    "community.general:7.4.0"
    "ansible.posix:1.5.4"
)
DOCKER_NETWORK="proxy"
DOCKER_SUBNET="172.28.0.0/16"
DATA_ROOT="/data"
OPT_ROOT="/opt"
BACKUP_ROOT="/data/backups"

print_header "Odoo Multi-Version Deployment - Bootstrap Infrastructure"
print_info "بدء تثبيت الملاحقات وإعداد البيئة..."
print_info "المسار المستهدف للمشروع: ${PROJECT_DIR}"

# ==============================================================================
# الخطوة 1: تحديث النظام وتثبيت الحزم الأساسية
# ==============================================================================
print_header "الخطوة 1: تحديث النظام وتثبيت الحزم الأساسية"
print_info "تحديث فهرس الحزم..."
apt-get update -y >/dev/null 2>&1 || print_warning "فشل تحديث فهرس الحزم (قد لا يوجد اتصال بالإنترنت)"

print_info "تثبيت الحزم الأساسية..."
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    curl \
    wget \
    gnupg \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    python3 \
    python3-pip \
    python3-venv \
    git \
    vim \
    sudo \
    ufw \
    jq \
    tar \
    gzip \
    zstd \
    >/dev/null 2>&1 || {
    print_error "فشل تثبيت بعض الحزم الأساسية. يرجى التحقق من اتصال الإنترنت ومحاولة مجدداً."
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
    # إضافة مفتاح GPG الرسمي لـ Docker
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null || true
    chmod a+r /etc/apt/keyrenders/docker.gpg 2>/dev/null || true

    # إضافة مستودع Docker
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        | tee /etc/apt/sources.list.d/docker.list >/dev/null

    apt-get update -y >/dev/null 2>&1 || true
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        docker-ce \
        docker-ce-cli \
        containerd.io \
        docker-buildx-plugin \
        docker-compose-plugin \
        >/dev/null 2>&1 || {
        print_error "فشل تثبيت Docker Engine. يرجى التثبيت يدوياً ومتابعة السكربت."
        exit 1
    }

    # تشغيل وتمكين خدمة Docker
    systemctl enable docker >/dev/null 2>&1 || true
    systemctl start docker >/dev/null 2>&1 || true
    print_success "تم تثبيت Docker Engine بنجاح"
fi

print_info "إصدار Docker: $(docker --version)"
print_info "إصدار Docker Compose: $(docker compose version 2>/dev/null || echo 'غير متاح')"

# إضافة المستخدم الحالي لمجموعة Docker (إذا كان السكربت يُ_run بواسطة مستخدم غير root)
if [[ -n "${SUDO_USER:-}" ]]; then
    usermod -aG docker "${SUDO_USER}" 2>/dev/null || true
    print_info "تم إضافة المستخدم ${SUDO_USER} لمجموعة docker"
fi

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
        print_error "فشل تثبيت Ansible عبر pip3. يرجى التثبيت يدوياً."
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
    print_warning "ملف requirements.yml غير موجود في ${PROJECT_DIR}. سيتم تثبيت المجموعات يدوياً..."
    for collection in "${ANSIBLE_COLLECTIONS[@]}"; do
        name="${collection%%:*}"
        version="${collection##*:}"
        print_info "تثبيت ${name}:${version}..."
        ansible-galaxy collection install "${name}:${version}" 2>&1 | tail -3 || true
    done
fi

# التحقق من تثبيت المجموعات
print_info "المجموعات المثبتة:"
ansible-galaxy collection list 2>/dev/null | grep -E "community.docker|community.general|ansible.posix" || true

# ==============================================================================
# الخطوة 5: إنشاء المجلدات والبنية الأساسية
# ==============================================================================
print_header "الخطوة 5: إنشاء المجلدات والبنية الأساسية"

DIRS=(
    "${OPT_ROOT}"
    "${DATA_ROOT}"
    "${BACKUP_ROOT}"
    "${OPT_ROOT}/odoo17"
    "${OPT_ROOT}/odoo19"
    "${DATA_ROOT}/odoo17"
    "${DATA_ROOT}/odoo19"
    "${BACKUP_ROOT}/odoo17"
    "${BACKUP_ROOT}/odoo19"
    "${BACKUP_ROOT}/infrastructure"
    "${BACKUP_ROOT}/jenkins"
    "${BACKUP_ROOT}/reports"
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
        mkdir -p "${DATA_ROOT}/${version}/${instance}/postgresql"
        mkdir -p "${OPT_ROOT}/${version}/${instance}/etc"
        mkdir -p "${OPT_ROOT}/${version}/${instance}/addons"
    done
done
print_success "تم إنشاء جميع المجلدات الأساسية"

# ==============================================================================
# الخطوة 6: إعداد الصلاحيات
# ==============================================================================
print_header "الخطوة 6: إعداد الصلاحيات والملفات"

chmod 755 "${OPT_ROOT}/odoo17" "${DATA_ROOT}/odoo17" "${BACKUP_ROOT}/odoo17"
chmod 755 "${OPT_ROOT}/odoo19" "${DATA_ROOT}/odoo19" "${BACKUP_ROOT}/odoo19"
chmod 700 "${DATA_ROOT}/odoo17/instance1/postgresql" "${DATA_ROOT}/odoo17/instance2/postgresql"
chmod 700 "${DATA_ROOT}/odoo19/instance1/postgresql" "${DATA_ROOT}/odoo19/instance2/postgresql"

# إنشاء مستخدم odoo if not exists
if ! id "odoo" >/dev/null 2>&1; then
    useradd -r -s /usr/sbin/nologin -d /var/lib/odoo odoo 2>/dev/null || true
    print_info "تم إنشاء مستخدم النظام odoo"
fi

# إضافة odoo لمجموعة docker
usermod -aG docker odoo 2>/dev/null || true

print_success "تم ضبط الصلاحيات بنجاح"

# ==============================================================================
# الخطوة 7: إنشاء شبكة Docker proxy
# ==============================================================================
print_header "الخطوة 7: إنشاء شبكة Docker proxy"

if docker network inspect "${DOCKER_NETWORK}" >/dev/null 2>&1; then
    print_success "شبكة Docker ${DOCKER_NETWORK} موجودة بالفعل"
else
    print_info "إنشاء شبكة Docker ${DOCKER_NETWORK}..."
    docker network create \
        --driver bridge \
        --subnet "${DOCKER_SUBNET}" \
        "${DOCKER_NETWORK}" >/dev/null 2>&1 || {
        print_warning "فشل إنشاء شبكة Docker مع subnet محدد، محاولة إنشاء subnet افتراضي..."
        docker network create --driver bridge "${DOCKER_NETWORK}" >/dev/null 2>&1 || {
            print_error "فشل إنشاء شبكة Docker proxy. يرجى إنشائها يدوياً."
            exit 1
        }
    }
    print_success "تم إنشاء شبكة Docker ${DOCKER_NETWORK}"
fi

# ==============================================================================
# الخطوة 8: نسخ ملفات المشروع إلى المسار المستهدف
# ==============================================================================
print_header "الخطوة 8: إعداد ملفات المشروع"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# إذا كان السكربت يُ_run من داخل مجلد المشروع، لا نحتاج نسخ
if [[ "${SCRIPT_DIR}" != "${PROJECT_DIR}" ]]; then
    if [[ -d "${PROJECT_DIR}" ]]; then
        print_warning "المجلد ${PROJECT_DIR} موجود بالفعل. سيتم تخطي النسخ."
    else
        print_info "نسخ ملفات المشروع إلى ${PROJECT_DIR}..."
        cp -r "${SCRIPT_DIR}/.." "${PROJECT_DIR}" 2>/dev/null || {
            print_warning "فشل النسخ التلقائي. يرجى نسخ ملفات المشروع يدوياً إلى ${PROJECT_DIR}"
        }
    fi
else
    print_info "السكربت يعمل من داخل مجلد المشروع: ${PROJECT_DIR}"
fi

# جعل السكربتات قابلة للتنفيذ
if [[ -d "${PROJECT_DIR}/scripts" ]]; then
    chmod +x "${PROJECT_DIR}/scripts"/*.sh 2>/dev/null || true
    print_success "تم جعل سكريبتات المشروع قابلة للتنفيذ"
fi

# ==============================================================================
# الخطوة 9: التحقق من البيئة النهائية
# ==============================================================================
print_header "الخطوة 9: التحقق من البيئة النهائية"

ALL_OK=true

# التحقق من Docker
if command -v docker >/dev/null 2>&1; then
    print_success "Docker: $(docker --version)"
else
    print_error "Docker غير مثبت"
    ALL_OK=false
fi

# التحقق من Docker Compose
if docker compose version >/dev/null 2>&1; then
    print_success "Docker Compose: $(docker compose version)"
else
    print_error "Docker Compose غير متاح"
    ALL_OK=false
fi

# التحقق من Ansible
if command -v ansible-playbook >/dev/null 2>&1; then
    print_success "Ansible: $(ansible-playbook --version | head -1)"
else
    print_error "Ansible غير مثبت"
    ALL_OK=false
fi

# التحقق من Python3
if command -v python3 >/dev/null 2>&1; then
    print_success "Python3: $(python3 --version)"
else
    print_error "Python3 غير مثبت"
    ALL_OK=false
fi

# التحقق من Git
if command -v git >/dev/null 2>&1; then
    print_success "Git: $(git --version)"
else
    print_error "Git غير مثبت"
    ALL_OK=false
fi

# التحقق من شبكة Docker
if docker network inspect "${DOCKER_NETWORK}" >/dev/null 2>&1; then
    print_success "شبكة Docker ${DOCKER_NETWORK}: موجودة"
else
    print_error "شبكة Docker ${DOCKER_NETWORK}: غير موجودة"
    ALL_OK=false
fi

# التحقق من وجود مجلد المشروع
if [[ -d "${PROJECT_DIR}" ]]; then
    print_success "مجلد المشروع: ${PROJECT_DIR} (موجود)"
else
    print_warning "مجلد المشروع: ${PROJECT_DIR} (غير موجود - يرجى نسخ ملفات المشروع إليه)"
fi

# ==============================================================================
# line النهاية
# ==============================================================================
print_header "اكتمل إعداد البيئة"

if [[ "${ALL_OK}" == "true" ]]; then
    print_success "جميع الملاحقات مثبتة والبيئة جاهزة!"
    echo ""
    print_info "الخطوات التالية:"
    echo "  1. انسخ ملفات المشروع إلى: ${PROJECT_DIR}"
    echo "  2. أدخل إلى مجلد المشروع: cd ${PROJECT_DIR}"
    echo "  3. ثبت مجموعات Ansible: ansible-galaxy collection install -r requirements.yml"
    echo "  4. ثبّت Odoo 17: sudo ./scripts/install-odoo17.sh"
    echo "  5. ثبّت Odoo 19: sudo ./scripts/install-odoo19.sh"
    echo ""
    print_info "أو عبر Jenkins: شغّل Pipeline install-odoo17.Jenkinsfile أو install-odoo19.Jenkinsfile"
else
    print_error "بعض المكونات لم يتم تثبيتها بنجاح. يرجى مراجعة الأخطاء أعلاه وإعادة المحاولة."
    exit 1
fi

echo ""
exit 0