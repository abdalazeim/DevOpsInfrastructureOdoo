import React, { useState } from 'react';
import { X, FileCode, Copy, Check, Terminal, FileText } from 'lucide-react';
import { Language } from '../types';

interface ArchitectureFilesModalProps {
  lang: Language;
  onClose: () => void;
}

export const ArchitectureFilesModal: React.FC<ArchitectureFilesModalProps> = ({
  lang,
  onClose,
}) => {
  const isAr = lang === 'ar';
  const [selectedFile, setSelectedFile] = useState<string>('traefik_compose');
  const [copied, setCopied] = useState<boolean>(false);

  const filesMap: Record<string, { title: string; path: string; lang: string; content: string }> = {
    traefik_compose: {
      title: 'Traefik v3.7 Docker Compose',
      path: 'deployment/traefik/docker-compose.yml',
      lang: 'yaml',
      content: `version: '3.8'

services:
  traefik:
    image: traefik:v3.7
    container_name: traefik
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    networks:
      - proxy
    ports:
      - "80:80"
      - "443:443"
    environment:
      - ACME_EMAIL=\${ACME_EMAIL}
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./config/traefik.yml:/etc/traefik/traefik.yml:ro
      - /opt/odoo-infrastructure/traefik/acme/acme.json:/etc/traefik/acme/acme.json
      - /opt/odoo-infrastructure/traefik/logs:/var/log/traefik
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.traefik-dashboard.rule=Host(\`\${TRAEFIK_DASHBOARD_DOMAIN}\`)"
      - "traefik.http.routers.traefik-dashboard.entrypoints=websecure"
      - "traefik.http.routers.traefik-dashboard.service=api@internal"
      - "traefik.http.routers.traefik-dashboard.tls.certresolver=letsencrypt"
      - "traefik.http.routers.traefik-dashboard.middlewares=auth-admin"

networks:
  proxy:
    external: true`,
    },
    odoo17_compose: {
      title: 'Odoo 17 & PostgreSQL 16 Compose',
      path: 'deployment/odoo17/docker-compose.yml',
      lang: 'yaml',
      content: `version: '3.8'

services:
  odoo17-db:
    image: postgres:16-alpine
    container_name: odoo17-db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_USER=\${ODOO17_DB_USER}
      - POSTGRES_PASSWORD=\${ODOO17_DB_PASSWORD}
      - PGDATA=/var/lib/postgresql/data/pgdata
    volumes:
      - /opt/odoo-infrastructure/odoo17/db_data:/var/lib/postgresql/data/pgdata
    networks:
      - odoo17_internal
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U \${ODOO17_DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  odoo17:
    image: odoo:17.0
    container_name: odoo17
    restart: unless-stopped
    depends_on:
      odoo17-db:
        condition: service_healthy
    environment:
      - HOST=odoo17-db
      - USER=\${ODOO17_DB_USER}
      - PASSWORD=\${ODOO17_DB_PASSWORD}
    volumes:
      - ./config/odoo.conf:/etc/odoo/odoo.conf:ro
      - /opt/odoo-infrastructure/odoo17/data:/var/lib/odoo
      - /opt/odoo-infrastructure/odoo17/addons:/mnt/extra-addons
    networks:
      - odoo17_internal
      - proxy
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.odoo17-web.rule=Host(\`\${ODOO17_DOMAIN}\`)"
      - "traefik.http.routers.odoo17-web.entrypoints=websecure"
      - "traefik.http.routers.odoo17-web.tls.certresolver=letsencrypt"
      - "traefik.http.routers.odoo17-web.service=odoo17-svc"
      - "traefik.http.services.odoo17-svc.loadbalancer.server.port=8069"

networks:
  odoo17_internal:
    driver: bridge
    internal: true
  proxy:
    external: true`,
    },
    odoo18_compose: {
      title: 'Odoo 18 & PostgreSQL 17 Compose',
      path: 'deployment/odoo18/docker-compose.yml',
      lang: 'yaml',
      content: `version: '3.8'

services:
  odoo18-db:
    image: postgres:17-alpine
    container_name: odoo18-db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_USER=\${ODOO18_DB_USER}
      - POSTGRES_PASSWORD=\${ODOO18_DB_PASSWORD}
      - PGDATA=/var/lib/postgresql/data/pgdata
    volumes:
      - /opt/odoo-infrastructure/odoo18/db_data:/var/lib/postgresql/data/pgdata
    networks:
      - odoo18_internal
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U \${ODOO18_DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  odoo18:
    image: odoo:18.0
    container_name: odoo18
    restart: unless-stopped
    depends_on:
      odoo18-db:
        condition: service_healthy
    environment:
      - HOST=odoo18-db
      - USER=\${ODOO18_DB_USER}
      - PASSWORD=\${ODOO18_DB_PASSWORD}
    volumes:
      - ./config/odoo.conf:/etc/odoo/odoo.conf:ro
      - /opt/odoo-infrastructure/odoo18/data:/var/lib/odoo
      - /opt/odoo-infrastructure/odoo18/addons:/mnt/extra-addons
    networks:
      - odoo18_internal
      - proxy
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.odoo18-web.rule=Host(\`\${ODOO18_DOMAIN}\`)"
      - "traefik.http.routers.odoo18-web.entrypoints=websecure"
      - "traefik.http.routers.odoo18-web.tls.certresolver=letsencrypt"
      - "traefik.http.routers.odoo18-web.service=odoo18-svc"
      - "traefik.http.services.odoo18-svc.loadbalancer.server.port=8069"

networks:
  odoo18_internal:
    driver: bridge
    internal: true
  proxy:
    external: true`,
    },
    odoo19_compose: {
      title: 'Odoo 19 & PostgreSQL 18 Compose',
      path: 'deployment/odoo19/docker-compose.yml',
      lang: 'yaml',
      content: `version: '3.8'

services:
  odoo19-db:
    image: postgres:18-alpine
    container_name: odoo19-db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_USER=\${ODOO19_DB_USER}
      - POSTGRES_PASSWORD=\${ODOO19_DB_PASSWORD}
      - PGDATA=/var/lib/postgresql/data/pgdata
    volumes:
      - /opt/odoo-infrastructure/odoo19/db_data:/var/lib/postgresql/data/pgdata
    networks:
      - odoo19_internal
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U \${ODOO19_DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  odoo19:
    image: odoo:19.0
    container_name: odoo19
    restart: unless-stopped
    depends_on:
      odoo19-db:
        condition: service_healthy
    environment:
      - HOST=odoo19-db
      - USER=\${ODOO19_DB_USER}
      - PASSWORD=\${ODOO19_DB_PASSWORD}
    volumes:
      - ./config/odoo.conf:/etc/odoo/odoo.conf:ro
      - /opt/odoo-infrastructure/odoo19/data:/var/lib/odoo
      - /opt/odoo-infrastructure/odoo19/addons:/mnt/extra-addons
    networks:
      - odoo19_internal
      - proxy
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.odoo19-web.rule=Host(\`\${ODOO19_DOMAIN}\`)"
      - "traefik.http.routers.odoo19-web.entrypoints=websecure"
      - "traefik.http.routers.odoo19-web.tls.certresolver=letsencrypt"
      - "traefik.http.routers.odoo19-web.service=odoo19-svc"
      - "traefik.http.services.odoo19-svc.loadbalancer.server.port=8069"

networks:
  odoo19_internal:
    driver: bridge
    internal: true
  proxy:
    external: true`,
    },
    ansible_playbook: {
      title: 'Ansible Ubuntu Baseline Playbook',
      path: 'automation/ansible/playbook.yml',
      lang: 'yaml',
      content: `---
- name: Configure Ubuntu Server Baseline for Odoo Infrastructure
  hosts: odoo_servers
  become: true
  roles:
    - role: baseline
      tags: [baseline, system]
    - role: docker
      tags: [docker, containers]

  post_tasks:
    - name: Ensure shared external proxy network exists
      community.docker.docker_network:
        name: "{{ docker_proxy_network | default('proxy') }}"
        driver: bridge
        state: present
        ipam_config:
          - subnet: "172.28.0.0/16"
            gateway: "172.28.0.1"`,
    },
    backup_script: {
      title: 'PostgreSQL & Filestore Backup Engine',
      path: 'automation/scripts/backup-db.sh',
      lang: 'bash',
      content: `#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="\${1}"
DB_NAME="\${2}"
RETENTION="\${3:-7}"
BACKUP_DIR="/opt/odoo-infrastructure/backups/odoo\${VERSION}"

mkdir -p "\${BACKUP_DIR}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DUMP_FILE="\${BACKUP_DIR}/dump_\${DB_NAME}_\${TIMESTAMP}.sql.gz"

echo "[INFO] Dumping PostgreSQL database '\${DB_NAME}'..."
docker exec "odoo\${VERSION}-db" pg_dump -U odoo -d "\${DB_NAME}" --clean | gzip > "\${DUMP_FILE}"

CHECKSUM=$(sha256sum "\${DUMP_FILE}" | awk '{print $1}')
echo "[OK] Backup created: $(basename "\${DUMP_FILE}") (SHA256: \${CHECKSUM:0:16}...)"`,
    },
  };

  const current = filesMap[selectedFile];

  const handleCopy = () => {
    navigator.clipboard.writeText(current.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        
        {/* Header */}
        <div className="bg-slate-950 px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center">
              <FileCode className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">
                {isAr ? 'مستعرض ملفات التكوين والسكربتات' : 'Generated Infrastructure & Automation Files'}
              </h2>
              <p className="text-xs text-slate-400 font-mono">
                Docker Compose • Traefik • Ansible Roles • Bash Automation
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-mono text-cyan-300 border border-slate-700 transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? (isAr ? 'تم النسخ!' : 'Copied!') : (isAr ? 'نسخ الملف' : 'Copy File')}</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
          
          {/* File Selector Sidebar */}
          <div className="w-full md:w-64 bg-slate-950/60 border-b md:border-b-0 md:border-r border-slate-800 p-3 space-y-1">
            <div className="text-[11px] font-mono text-slate-500 px-2 py-1 uppercase tracking-wider">
              {isAr ? 'الملفات المتاحة' : 'Architecture Files'}
            </div>
            {Object.entries(filesMap).map(([key, item]) => (
              <button
                key={key}
                onClick={() => setSelectedFile(key)}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs font-mono transition-colors flex items-center justify-between ${
                  selectedFile === key
                    ? 'bg-cyan-950 border border-cyan-800 text-cyan-300 font-bold'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                }`}
              >
                <div className="truncate pr-2">{item.title}</div>
                <span className="text-[10px] text-slate-500 uppercase">{item.lang}</span>
              </button>
            ))}
          </div>

          {/* File Viewer Main Panel */}
          <div className="flex-1 flex flex-col bg-slate-950 overflow-hidden">
            <div className="bg-slate-900/60 px-4 py-2 border-b border-slate-800 flex items-center justify-between text-xs font-mono text-slate-400">
              <span>Path: <code className="text-cyan-400">{current.path}</code></span>
              <span className="text-slate-500">Read-Only View</span>
            </div>
            <div className="flex-1 p-4 overflow-auto">
              <pre className="font-mono text-xs text-slate-300 leading-relaxed whitespace-pre selection:bg-cyan-900 selection:text-cyan-100">
                {current.content}
              </pre>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
};
