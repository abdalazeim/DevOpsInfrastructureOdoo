#!/usr/bin/env bash
# ==============================================================================
# Odoo Infrastructure Manager - Health & Status Diagnostic Script
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

log_info() { echo -e "\033[0;34m[INFO]\033[0m $*"; }
log_ok()   { echo -e "\033[0;32m[OK]\033[0m $*"; }
log_warn() { echo -e "\033[0;33m[WARN]\033[0m $*"; }
log_err()  { echo -e "\033[0;31m[FAIL]\033[0m $*" >&2; }

echo "=========================================================="
echo "    ODOO INFRASTRUCTURE MANAGER - HEALTH CHECK REPORT     "
echo "    Date: $(date -u +"%Y-%m-%d %H:%M:%S UTC")             "
echo "=========================================================="

# 1. Check Docker Daemon
echo ""
log_info "1. Docker Daemon Engine Status:"
if docker info >/dev/null 2>&1; then
  DOCKER_VER=$(docker version --format '{{.Server.Version}}')
  log_ok "Docker daemon is active and responsive (v${DOCKER_VER})."
else
  log_err "Docker daemon is unreachable or stopped."
  exit 1
fi

# 2. Check Shared Network
echo ""
log_info "2. Shared Network 'proxy':"
if docker network inspect proxy >/dev/null 2>&1; then
  SUBNET=$(docker network inspect proxy --format '{{(index .IPAM.Config 0).Subnet}}' 2>/dev/null || echo "dynamic")
  log_ok "Network 'proxy' is active (Subnet: ${SUBNET})"
else
  log_warn "Network 'proxy' is not created yet."
fi

# 3. Check Containers
echo ""
log_info "3. Service Containers Health Status:"
SERVICES=("traefik" "odoo17" "odoo17-db" "odoo19" "odoo19-db")

for svc in "${SERVICES[@]}"; do
  if docker ps -a --format '{{.Names}}' | grep -Eq "^${svc}$"; then
    STATUS=$(docker inspect --format '{{.State.Status}}' "${svc}")
    HEALTH=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${svc}")
    UPTIME=$(docker inspect --format '{{.State.StartedAt}}' "${svc}")
    
    if [[ "${STATUS}" == "running" ]]; then
      log_ok "Container ${svc}: RUNNING (Health: ${HEALTH})"
    else
      log_err "Container ${svc}: ${STATUS^^}"
    fi
  else
    log_warn "Container ${svc}: NOT FOUND / NOT DEPLOYED"
  fi
done

# 4. Check PostgreSQL Internal Connectivity
echo ""
log_info "4. Database Engine Status:"
for version in 17 19; do
  db_svc="odoo${version}-db"
  if docker ps --format '{{.Names}}' | grep -Eq "^${db_svc}$"; then
    if docker exec "${db_svc}" pg_isready >/dev/null 2>&1; then
      log_ok "${db_svc}: PostgreSQL accepting connections"
    else
      log_err "${db_svc}: PostgreSQL ping rejected"
    fi
  fi
done

# 5. Check Disk & Memory Utilization
echo ""
log_info "5. Host Resource Metrics:"
df -h / | awk 'NR==2 {print "Disk Root Usage: " $3 " / " $2 " (" $5 " used)"}'
free -h | awk 'NR==2 {print "Memory Usage:    " $3 " / " $2 " (" $7 " available)"}'

echo ""
echo "=========================================================="
log_ok "Health check sweep completed."
