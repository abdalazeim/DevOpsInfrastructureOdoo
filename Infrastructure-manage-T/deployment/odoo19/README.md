# Installing Odoo 19.0 with one command (Supports multiple Odoo instances on one server).

## Quick Installation

Install [docker](https://docs.docker.com/get-docker/) and [docker-compose](https://docs.docker.com/compose/install/) yourself, then run the following to set up first Odoo instance:

```bash
cd /opt/Odoo-MultiVersion-Deployment/odoo19
sudo ./scripts/install-odoo19.sh
```

The script installs two independent Odoo 19 instances:
- **Instance 1**: `https://odoo19-1.devops-odoo.com` — `odoo19-db1` (PostgreSQL 18)
- **Instance 2**: `https://odoo19-2.devops-odoo.com` — `odoo19-db2` (PostgreSQL 18)

No ports are published publicly; Traefik handles access via HTTPS.

### Installation via Jenkins

Use the Jenkins Pipeline `Install Odoo 19 – Two Instances` which runs all installation stages automatically.

### Installation via Terminal

```bash
cd /opt/Odoo-MultiVersion-Deployment/odoo19
sudo ./scripts/install-odoo19.sh
```

## Usage

Start the container:
```sh
cd /opt/odoo19/instance1
docker-compose up -d
```

Then open `https://odoo19-1.devops-odoo.com` to access Odoo 19 via Traefik HTTPS.

For the second instance:
```bash
cd /opt/odoo19/instance2
docker-compose up -d
```

Open `https://odoo19-2.devops-odoo.com` to access the second Odoo 19 instance.

- **If you get any permission issues**, change the folder permission to make sure that the container is able to access the directory:

```sh
$ sudo chmod -R 700 /data/odoo19/instance1/postgresql
$ sudo chmod -R 700 /data/odoo19/instance2/postgresql
```

- If you want to start the server with a different port, change **8069** to another value in **docker-compose.yml** inside the parent dir:

```
ports:
  - "8069:8069"
```

- To run Odoo container in detached mode:

```
docker-compose up -d
```

- To Use a restart policy:

```
restart: always             # run as a service
```

- To increase maximum number of files watching from 8192 (default) to **524288**:

```
$ if grep -qF "fs.inotify.max_user_watches" /etc/sysctl.conf; then echo $(grep -F "fs.inotify.max_user_watches" /etc/sysctl.conf); else echo "fs.inotify.max_user_watches = 524288" | sudo tee -a /etc/sysctl.conf; fi
$ sudo sysctl -p    # apply new config immediately
```

## Custom addons

The **addons/** folder contains custom addons. Just put your custom addons if you have any.

## Odoo configuration & log

* To change Odoo configuration, edit file: **etc/odoo.conf**.
* Log file: **etc/odoo-server.log**
* Default database password (**admin_passwd**) is set via `vault_odoo_admin_password` in Ansible vault, update it in [etc/odoo.conf](/etc/odoo.conf) or via Jenkins credentials.

## 🔑 كلمات مرور المشرف الافتراضية (before production)

| الإصدار | Odoo Admin Password | PostgreSQL Password | container_name |
|---------|---------------------|---------------------|----------------|
| **Odoo 19** | `odoo19` | `odoo19` | `odoo19` |

> ⚠️ **تنبيه أمني مهم**: هذه كلمات مرور افتراضية للتجربة فقط. **يجب استبدالها قبل النشر في بيئة إنتاج حقيقية** عبر Jenkins Credentials أو ملف `.env` أو Ansible Vault.

## Odoo container management

**Run Odoo**:

```bash
docker-compose up -d
```

**Restart Odoo**:

```bash
docker-compose restart
```

**Stop Odoo**:

```bash
docker-compose down
```

## Live chat

Live chat runs on port **8072** internally and is routed through Traefik via WebSocket path `/websocket`.

Configuring **nginx** to activate live chat feature (in production):

```conf
#...
server {
    #...
    location /websocket/ {
        proxy_pass http://0.0.0.0:8072/websocket/;
    }
    #...
}
#...
```

## docker-compose.yml

* odoo:19
* postgres:18
* PGDATA: /var/lib/postgresql/18/docker

## Odoo 19.0 Multi-Instance Deployment Summary

| المكون | القيمة |
|--------|--------|
| صورة Odoo Docker | `odoo:19` |
| PostgreSQL | 18 |
| PGDATA المسار | `/var/lib/postgresql/18/docker` |
| المنفذ الداخلي Odoo | 8069 |
| المنفذ الداخلي Live Chat | 8072 |
| عدد النسخ | 2 |
| النطاقات | `odoo19-1.devops-odoo.com` / `odoo19-2.devops-odoo.com` |
| مجلدات البيانات | `/data/odoo19/instance1` / `/data/odoo19/instance2` |
| Traefik | مشترك (HTTPS) |