# Odoo Infrastructure Architecture Guide

## Overview

`odoo-infrastructure-manager` orchestrates a multi-version, enterprise-ready Odoo infrastructure on Ubuntu Server.

```
                    Internet (HTTP: 80 / HTTPS: 443)
                                  │
                                  ▼
               ┌─────────────────────────────────────┐
               │         Traefik v3.7 Proxy          │
               │      (Automatic Let's Encrypt)      │
               │   Secure dashboard router + Auth    │
               └──────────────────┬──────────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         │ Docker Bridge Network: 'proxy' (172.28.0.0/16)  │
         └───┬──────────────┬──────────────┬───────────────┘
             │              │              │
 Host: odoo17 │  Host: odoo18 │  Host: odoo19 │  Host: pgadmin
             │              │              │
             ▼              ▼              ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ Odoo 17 (Web)│ │ Odoo 18 (Web)│ │ Odoo 19 (Web)│ │  pgAdmin 4   │
    └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────────────┘
           │                │                │
  odoo17_internal   odoo18_internal   odoo19_internal
           │                │                │
           ▼                ▼                ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ PostgreSQL 16│ │ PostgreSQL 17│ │ PostgreSQL 18│
    │ (5432 - int) │ │ (5432 - int) │ │ (5432 - int) │
    └──────────────┘ └──────────────┘ └──────────────┘
```

## Key Components

1. **Host Operating System**: Ubuntu Server 22.04 LTS or 24.04 LTS (default hostname: `devops-odoo`).
2. **Reverse Proxy (Traefik v3.7)**:
   - Terminates TLS via Let's Encrypt ACME HTTP-01 or TLS-ALPN-01 challenge.
   - Enforces automatic HTTP to HTTPS permanent redirection (301).
   - Injects security headers (HSTS, X-Frame-Options, Content-Type-Nosniff, XSS protection).
   - Routes WebSocket / livechat traffic to port 8072.
   - Routes standard web traffic to port 8069.
   - Protected Web Dashboard with Basic Auth middleware (exposed only via secure router; `api.insecure=false`, no published management port).
   - Local API on `127.0.0.1:8787` serves the React dashboard; Vite proxies `/api`.
3. **External Network (`proxy`)**:
   - Subnet `172.28.0.0/16`.
   - Shared between Traefik and frontend Odoo containers.
   - Database containers are strictly isolated and NOT connected to `proxy`.
4. **Odoo 17 Stack**:
   - Image: `odoo:17.0` (configurable).
   - Database: `postgres:16-alpine`.
   - Network: `odoo17_internal` (bridge, internal-only).
   - Persistent Volumes: `odoo17/db_data`, `odoo17/data`, `odoo17/addons`.
   - Host ports: `10017` (HTTP) and `20017` (chat) in standalone mode.
5. **Odoo 18 Stack**:
   - Image: `odoo:18.0` (configurable).
   - Database: `postgres:17-alpine`.
   - Network: `odoo18_internal` (bridge, internal-only).
   - Persistent Volumes: `odoo18/db_data`, `odoo18/data`, `odoo18/addons`.
   - Host ports: `10018` (HTTP) and `20018` (chat) in standalone mode.
6. **Odoo 19 Stack**:
   - Image: `odoo:19.0` (configurable next-gen).
   - Database: `postgres:18-alpine`.
   - Network: `odoo19_internal` (bridge, internal-only).
   - Persistent Volumes: `odoo19/db_data`, `odoo19/data`, `odoo19/addons`.
   - Host ports: `10019` (HTTP) and `20019` (chat) in standalone mode.
   - PostgreSQL 18 changed its `PGDATA` layout, so the volume mounts at `/var/lib/postgresql/18/docker`.
7. **pgAdmin 4**:
   - Image: `dpage/pgadmin4`.
   - Attached to the external `proxy` network only; no bundled PostgreSQL.
   - Credentials from `.env`; published on `${PGADMIN_HTTP_PORT:-5050}`.
8. **Unified installer** (`automation/scripts/install-odoo.sh`):
   - Accepts `17`, `18`, or `19` and creates a self-contained instance directory with `docker-compose.yml`, `postgresql/`, `addons/`, `etc/odoo.conf`, `entrypoint.sh`, and a per-version `.env` (`0600`).
