#!/bin/bash
# ==============================================================================
# Odoo 17 Private Repository - Installation Script
#
# يستمد الأفكار من odoo-17-docker-compose-master/run.sh
# مع تحسينات لنظام مدير البنية التحتية.
#
# الاستخدام:
#   ./scripts/install-odoo17.sh <instance_name> <http_port> <chat_port> [--with-traefik]
# ==============================================================================
set -euo pipefail

INSTANCE_NAME="${1:? instance name is required}"
HTTP_PORT="${2:? HTTP port is required}"
CHAT_PORT="${3:? chat port is required}"
WITH_TRAEFIK="${4:-}"

DESTINATION="/opt/odoo-infrastructure/${INSTANCE_NAME}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

SOURCE_DIR="${PROJECT_ROOT}/deployment/odoo17/odoo-17-private-repo"

echo "============================================="
echo " Installing Odoo 17 Private Repository"
echo "============================================="
echo " Instance: ${INSTANCE_NAME}"
echo " Destination: ${DESTINATION}"
echo " HTTP Port: ${HTTP_PORT}"
echo " Chat Port: ${CHAT_PORT}"
echo " Traefik: ${WITH_TRAEFIK:-no}"
echo ""

# التحقق من وجود دوكرب
if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker is not installed."
    exit 1
fi

# إنشاء مجلد المثيل
mkdir -p "${DESTINATION}/{addons,etc,postgresql}"

# نسخ ملفات القالب
cp "${SOURCE_DIR}/docker-compose.yml" "${DESTINATION}/"
cp "${SOURCE_DIR}/entrypoint.sh" "${DESTINATION}/"
cp "${SOURCE_DIR}/etc/odoo.conf" "${DESTINATION}/etc/"
cp "${SOURCE_DIR}/etc/requirements.txt" "${DESTINATION}/etc/"
cp "${SOURCE_DIR}/.gitignore" "${DESTINATION}/"
cp -r "${SOURCE_DIR}/addons/." "${DESTINATION}/addons/" 2>/dev/null || true

if [ "${WITH_TRAEFIK}" = "--with-traefik" ]; then
    cp "${SOURCE_DIR}/docker-compose.traefik.yml" "${DESTINATION}/docker-compose.traefik.yml"
    echo "Traefik mode enabled."
fi

# إعداد الصلاحيات
chmod +x "${DESTINATION}/entrypoint.sh"
find "${DESTINATION}" -type f -exec chmod 644 {} \;
find "${DESTINATION}" -type d -exec chmod 755 {} \;
chmod 700 "${DESTINATION}/postgresql"

# إنشاء ملف .env للقالب
cat > "${DESTINATION}/.env" <<EOF
# Odoo 17 Private Repository - Environment Variables
ODOO_IMAGE=odoo:17
PG_IMAGE=postgres:16
ODOO_HTTP_PORT=${HTTP_PORT}
ODOO_CHAT_PORT=${CHAT_PORT}
ODOO_NETWORK=odoo17_internal
ODOO_DOMAIN=odoo17.localhost
DOCKER_PROXY_NETWORK=proxy
CERTSRESOLVER=letsencrypt
POSTGRES_USER=odoo
POSTGRES_PASSWORD=CHANGE_ME
ODOO_DB_USER=odoo
ODOO_DB_PASSWORD=CHANGE_ME
ODOO_ADMIN_PASSWORD=CHANGE_ME
ODOO_DB_NAME=odoo17_prod
EOF
chmod 600 "${DESTINATION}/.env"

echo ""
echo "============================================="
echo " Odoo 17 Private Repository installed"
echo "============================================="
echo " Next steps:"
echo "  1. Edit ${DESTINATION}/.env and set secure passwords"
echo "  2. Run: docker compose -f ${DESTINATION}/docker-compose.yml up -d"
echo "  3. Access: http://localhost:${HTTP_PORT}"
echo ""

if [ "${WITH_TRAEFIK}" = "--with-traefik" ]; then
    echo " Traefik mode: Access via https://${ODOO_DOMAIN}"
fi
