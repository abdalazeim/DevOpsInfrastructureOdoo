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

## 💾 النسخ الاحتياطي والاستعاشة من الكوارث (Backup & Disaster Recovery)

### نظرة عامة

يدعم النظام نسخًا احتياطية شاملة لكل مكون من مكونات النشر، مع نظام مدير النسخ الاحتياطي المركزي (Backup & Recovery Manager) يدعم أربع عمليات رئيسية: **Backup، Restore، Verify، Schedule**.

### ما الذي نحفظه لكل نسخة Odoo

| العنصر | ما الذي نحفظه | الأداة المستخدمة |
|--------|--------------|----------------|
| **PostgreSQL** | قواعد البيانات والمستخدمون والصلاحيات | `pg_dump` / `backup-db.sh` |
| **Filestore** | المرفقات والصور والملفات المرفوعة | `tar.zst` / `backup.sh` |
| **Custom Addons** | الإضافات والتعديلات البرمجية المخصصة | Git / `tar.zst` |
| **Odoo Configuration** | ملفات `odoo.conf` وإعدادات الحاوية | `cp` / Ansible |
| **Docker Compose** | ملفات تشغيل الحاويات (`docker-compose.yml`) | Git |
| **Environment** | متغيرات التشغيل والأسرار المشفرة (`.env`) | `chmod 600` + GPG |
| **Traefik** | إعدادات التوجيه والشهادات (SSL/TLS) | `cp` + GPG |
| **Ansible** | Playbooks و Roles و Inventory | Git |
| **Jenkins** | إعدادات خطوط الأنابيب والملفات المهمة | Jenkins Backup Plugin |
| **Git** | رقم Commit والإصدار المستخدم في النشر | Git (tag / commit hash) |

### أنواع النسخ الاحتياطي المدعومة

| النوع | الوظيفة |
|-------|----------|
| **Full Backup** | نسخ شامل لجميع بيانات النسخة وإعداداتها |
| **Database Backup** | نسخ قواعد البيانات فقط |
| **Filestore Backup** | نسخ المرفقات والملفات |
| **Configuration Backup** | نسخ الإعدادات وملفات التشغيل |
| **Complete Infrastructure Backup** | نسخ جميع نسخ Odoo وملفات البنية التحتية |
| **Pre-Update Backup** | نسخ تلقائي قبل تحديث Odoo أو الإضافات |

### خيارا الاستخدام اليومي

- **Backup All**: نسخ شامل لكل نسخ Odoo 19.
- **Backup Selected**: اختيار نسخة معينة (مثل Odoo 19 Instance 1).

### عملية النسخ الصحيحة

1. التحقق من مساحة التخزين المتاحة.
2. التأكد من أن PostgreSQL يعمل.
3. إيقاف خدمة Odoo مؤقتًا (محمية بـ `try/finally`).
4. تصدير قاعدة البيانات باستخدام `pg_dump` بصيغة Custom.
5. حفظ صلاحيات ومستخدمي PostgreSQL.
6. نسخ Filestore.
7. نسخ Custom Addons وملفات الإعداد.
8. إنشاء ملف Manifest.
9. إنشاء Checksums (SHA256).
10. إعادة تشغيل Odoo.
11. تسجيل نتيجة العملية.

### تنظيم مجلدات النسخ الاحتياطية

```
/data/backups/
├── odoo19/
│   ├── instance1/
│   │   └── 2026-11-04_020000/
│   │       ├── database.dump
│   │       ├── filestore.tar.zst
│   │       ├── addons.tar.zst
│   │       ├── config.tar.zst
│   │       ├── manifest.json
│   │       └── checksums.sha256
│   │
│   └── instance2/
│
└── infrastructure/
    ├── ansible/
    ├── traefik/
    └── docker/
```

### أخذ نسخة احتياطية

```bash
cd /opt/Odoo-MultiVersion-Deployment/odoo19
sudo ./scripts/backup.sh instance1 /data/backups/odoo19
sudo ./scripts/backup.sh instance2 /data/backups/odoo19

# أوامر مستقلة عبر Terminal
sudo ./scripts/backup.sh --all              # نسخ شامل لجميع نسخ Odoo
sudo ./scripts/backup.sh --version 19       # نسخ Odoo 19 فقط
sudo ./scripts/backup.sh --instance odoo19-instance1  # نسخة محددة
sudo ./scripts/verify-backups.sh            # فحص النسخ الاحتياطية
sudo ./scripts/list-backups.sh              # عرض النسخ المتوفرة
sudo ./scripts/restore.sh --backup-id BACKUP_ID  # استعادة نسخة احتياطية
```

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