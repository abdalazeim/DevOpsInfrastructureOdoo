# Odoo Infrastructure Architecture Guide

## Overview

`odoo-infrastructure-manager` orchestrates a dual-version, enterprise-ready Odoo infrastructure on Ubuntu Server.

```
                    Internet (HTTP: 80 / HTTPS: 443)
                                  │
                                  ▼
               ┌─────────────────────────────────────┐
               │         Traefik v3.7 Proxy          │
               │      (Automatic Let's Encrypt)      │
               └──────────────────┬──────────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         │ Docker Bridge Network: 'proxy' (172.28.0.0/16)  │
         └────────────┬─────────────────────────┬──────────┘
                      │                         │
     Host: odoo17.example.com        Host: odoo19.example.com
                      │                         │
                      ▼                         ▼
         ┌─────────────────────────┐  ┌─────────────────────────┐
         │      Odoo 17 (Web)      │  │      Odoo 19 (Web)      │
         └────────────┬────────────┘  └────────────┬────────────┘
                      │                            │
      Private: odoo17_internal     Private: odoo19_internal
                      │                            │
                      ▼                            ▼
         ┌─────────────────────────┐  ┌─────────────────────────┐
         │  PostgreSQL 16 Engine   │  │  PostgreSQL 18 Engine   │
         │  (Port 5432 - Internal) │  │  (Port 5432 - Internal) │
         └─────────────────────────┘  └─────────────────────────┘
```

## Key Components

1. **Host Operating System**: Ubuntu Server 22.04 LTS or 24.04 LTS (default hostname: `devops-odoo`).
2. **Reverse Proxy (Traefik v3.7)**:
   - Terminates TLS via Let's Encrypt ACME HTTP-01 or TLS-ALPN-01 challenge.
   - Enforces automatic HTTP to HTTPS permanent redirection (301).
   - Injects security headers (HSTS, X-Frame-Options, Content-Type-Nosniff, XSS protection).
   - Routes WebSocket / livechat traffic to port 8072.
   - Routes standard web traffic to port 8069.
   - Protected Web Dashboard with Basic Auth middleware.
3. **External Network (`proxy`)**:
   - Subnet `172.28.0.0/16`.
   - Shared between Traefik and frontend Odoo containers.
   - Database containers are strictly isolated and NOT connected to `proxy`.
4. **Odoo 17 Stack**:
   - Image: `odoo:17.0` (configurable).
   - Database: `postgres:16-alpine`.
   - Network: `odoo17_internal` (bridge, internal-only).
   - Persistent Volumes: `odoo17/db_data`, `odoo17/data`, `odoo17/addons`.
5. **Odoo 19 Stack**:
   - Image: `odoo:19.0` (configurable next-gen).
   - Database: `postgres:18-alpine`.
   - Network: `odoo19_internal` (bridge, internal-only).
   - Persistent Volumes: `odoo19/db_data`, `odoo19/data`, `odoo19/addons`.
