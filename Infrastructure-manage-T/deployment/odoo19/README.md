# 🐋 تثبيت Odoo 19 بأمر واحد (يدعم نسخ متعددة من Odoo على خادم واحد) — Installing Odoo 19.0

> **النظام المدعوم:** Ubuntu Server 22.04 LTS / 24.04 LTS  
> **الأداة:** Odoo 19 + PostgreSQL 18  
> **حالات الاستخدام:** نشر نسخ متعددة من Odoo 19 على خادم واحد عبر Traefik HTTPS  
> **المستوى:** مشرف نظام / مسؤول بنية تحتية  
> **التاريخ:** نوفمبر 2026

---

## 📋 جدول المحتويات

1. [التثبيت السريع](#-التثبيت-السريع)
2. [الاستخدام](#-الاستخدام)
3. [الإضافات المخصصة](#-الإضافات-المخصصة-Custom-addons)
4. [تكوين Odoo والسجل](#-تكوين-Odoo-والسجل)
5. [كلمات مرور المشرف الافتراضية (قبل الإنتاج)](#-كلمات-مرور-المشرف-الافتراضية-قبل-الإنتاج)
6. [النسخ الاحتياطي والاستعاشة من الكوارث (Backup & Disaster Recovery)](#-النسخ-الاحتياطي والاستعاشة-من-الكوارث-Backup-Disaster-Recovery)
7. [إدارة حاوية Odoo](#-إدارة-حاوية-Odoo-Odoo-container-management)
8. [الدردشة الحية](#-الدردشة الحية-Live-chat)
9. [ملف docker-compose.yml](#-ملف-docker-compose-yml)
10. [ملخص نشر نسخ متعددة من Odoo 19.0](#-ملخص-نشر-نسخ-متعددة-من-Odoo-19-0-Odoo-19-Multi-Instance-Deployment-Summary)

---

## 1. ⚡ التثبيت السريع

ثبت [Docker](https://docs.docker.com/get-docker/) و [Docker Compose](https://docs.docker.com/compose/install/) بنفسك، ثم شغل الأمر التالي لإعداد أول نسخة من Odoo:

```bash
cd /opt/Odoo-MultiVersion-Deployment/odoo19
sudo ./scripts/install-odoo19.sh
```

يثبت السكربت نسختين مستقلتين من Odoo 19:

- **النسخة 1**: `https://${ODOO19_INSTANCE1_DOMAIN}` — `odoo19-db1` (PostgreSQL 18)
- **النسخة 2**: `https://${ODOO19_INSTANCE2_DOMAIN}` — `odoo19-db2` (PostgreSQL 18)

لا يتم نشر أي منافذ علناً؛ يتعامل Traefik مع الوصول عبر HTTPS.

### التثبيت عبر Jenkins

استخدم خط أنابيب Jenkins `Install Odoo 19 – Two Instances` الذي ينفذ جميع مراحل التثبيت تلقائياً.

### التثبيت عبر Terminal

```bash
cd /opt/Odoo-MultiVersion-Deployment/odoo19
sudo ./scripts/install-odoo19.sh
```

---

## 2. 📖 الاستخدام

ابدأ الحاوية:

```sh
cd /opt/odoo19/instance1
docker-compose up -d
```

ثم افتح `https://${ODOO19_INSTANCE1_DOMAIN}` للوصول إلى Odoo 19 عبر Traefik HTTPS.

بالنسبة للنسخة الثانية:

```bash
cd /opt/odoo19/instance2
docker-compose up -d
```

افتح `https://${ODOO19_INSTANCE2_DOMAIN}` للوصول إلى النسخة الثانية من Odoo 19.

- إذا واجهت أي مشاكل في الصلاحيات، غيّر صلاحية المجلد لضمان قدرة الحاوية على الوصول إلى الدليل:

```sh
$ sudo chmod -R 700 /data/odoo19/instance1/postgresql
$ sudo chmod -R 700 /data/odoo19/instance2/postgresql
```

- إذا كنت تريد تشغيل الخادم على منفذ مختلف، غيّر القيمة **8069** إلى قيمة أخرى في ملف **docker-compose.yml** داخل الدليل الأب:

```
ports:
  - "8069:8069"
```

- لتشغيل حاوية Odoo في وضع الانفصال (detached mode):

```
docker-compose up -d
```

- لاستخدام سياسة إعادة التشغيل:

```
restart: always             #運ة كخدمة
```

- لزيادة أقصى عدد لمراقبة الملفات من 8192 (الافتراضي) إلى **524288**:

```
$ if grep -qF "fs.inotify.max_user_watches" /etc/sysctl.conf; then echo $(grep -F "fs.inotify.max_user_watches" /etc/sysctl.conf); else echo "fs.inotify.max_user_watches = 524288" | sudo tee -a /etc/sysctl.conf; fi
$ sudo sysctl -p    # تطبيق الإعداد الجديد فوراً
```

---

## 3. 🔌 الإضافات المخصصة — Custom addons

يحتوي مجلد **addons/** على الإضافات المخصصة. فقط أضف إضافاتك المخصصة إذا كانت لديك أي منها.

---

## 4. ⚙️ تكوين Odoo والسجل

* لتغيير تكوين Odoo، عدّل ملف: **etc/odoo.conf**.
* ملف السجل: **etc/odoo-server.log**
* كلمة مرور قاعدة البيانات الافتراضية (**admin_passwd**) تحدد عبر `vault_odoo_admin_password` في Ansible vault، حدّثها في [etc/odoo.conf](/etc/odoo.conf) أو عبر بيانات اعتماد Jenkins.

---

## 8. 🔑 كلمات مرور المشرف الافتراضية (before production)

| الإصدار | Odoo Admin Password | PostgreSQL Password | container_name |
|---------|---------------------|---------------------|----------------|
| **Odoo 19** | `odoo19` | `odoo19` | `odoo19` |

> ⚠️ **تنبيه أمني مهم**: هذه كلمات مرور افتراضية للتجربة فقط. **يجب استبدالها قبل النشر في بيئة إنتاج حقيقية** عبر Jenkins Credentials أو ملف `.env` أو Ansible Vault.

---

## 9. 💾 النسخ الاحتياطي والاستعاشة من الكوارث (Backup & Disaster Recovery)

### 9.1 نظرة عامة

يدعم النظام نسخًا احتياطية شاملة لكل مكون من مكونات النشر، مع نظام مدير النسخ الاحتياطي المركزي (Backup & Recovery Manager) يدعم أربع عمليات رئيسية: **Backup، Restore، Verify، Schedule**.

### 9.2 ما الذي نحفظه لكل نسخة Odoo

| العنصر | ما الذي نحفظه | الأداة المستخدمة |
|--------|--------------|----------------|
| **PostgreSQL** | قواعد البيانات والمستخدمون والصلplies | `pg_dump` / `backup-db.sh` |
| **Filestore** | المرفقات والصور والملفات المرفوعة | `tar.zst` / `backup.sh` |
| **Custom Addons** | الإضافات والتعديلات البرمجية المخصصة | Git / `tar.zst` |
| **Odoo Configuration** | ملفات `odoo.conf` وإعدادات الحاوية | `cp` / Ansible |
| **Docker Compose** | ملفات تشغيل الحاويات (`docker-compose.yml`) | Git |
| **Environment** | متغيرات التشغيل والأسرار المشفرة (`.env`) | `chmod 600` + GPG |
| **Traefik** | إعدادات التوجيه والشهادات (SSL/TLS) | `cp` + GPG |
| **Ansible** | Playbooks و Roles و Inventory | Git |
| **Jenkins** | إعدادات خطوط الأنابيب والملفات المهمة | Jenkins Backup Plugin |
| **Git** | رقم Commit والإصدار المستخدم في النشر | Git (tag / commit hash) |

### 9.3 أنواع النسخ الاحتياطي المدعومة

| النوع | الوظيفة |
|-------|----------|
| **Full Backup** | نسخ شامل لجميع بيانات النسخة وإعداداتها |
| **Database Backup** | نسخ قواعد البيانات فقط |
| **Filestore Backup** | نسخ المرفقات والملفات |
| **Configuration Backup** | نسخ الإعدادات وملفات التشغيل |
| **Complete Infrastructure Backup** | نسخ جميع نسخ Odoo وملفات البنية التحتية |
| **Pre-Update Backup** | نسخ تلقائي قبل تحديث Odoo أو الإضافات |

### 9.4 خيارا الاستخدام اليومي

- **Backup All**: نسخ شامل لكل نسخ Odoo 19.
- **Backup Selected**: اختيار نسخة معينة (مثل Odoo 19 Instance 1).

### 9.5 عملية النسخ الصحيحة

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

### 9.6 تنظيم مجلدات النسخ الاحتياطية

```text
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

### 9.7 أخذ نسخة احتياطية

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

---

## 7. 📦 إدارة حاوية Odoo — Odoo container management

### تشغيل Odoo:

```bash
docker-compose up -d
```

### إعادة تشغيل Odoo:

```bash
docker-compose restart
```

### إيقاف Odoo:

```bash
docker-compose down
```

---

## 8. 💬 الدردشة الحية — Live chat

تعمل الدردشة الحية على المنفذ **8072** داخليًا ويتم توجيهها عبر Traefik عبر مسار WebSocket `/websocket`.

لتكوين **nginx** لتفعيل ميزة الدردشة الحية (في الإنتاج):

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

---

## 9. 🐋 ملف docker-compose.yml

* odoo:19
* postgres:18
* PGDATA: /var/lib/postgresql/18/docker

---

## 10. 📋 ملخص نشر نسخ متعددة من Odoo 19.0 — Odoo 19.0 Multi-Instance Deployment Summary

| المكون | القيمة |
|--------|--------|
| صورة Odoo Docker | `odoo:19` |
| PostgreSQL | 18 |
| PGDATA المسار | `/var/lib/postgresql/18/docker` |
| المنفذ الداخلي Odoo | 8069 |
| المنفذ الداخلي Live Chat | 8072 |
| عدد النسخ | 2 |
| النطاقات | `${ODOO19_INSTANCE1_DOMAIN}` / `${ODOO19_INSTANCE2_DOMAIN}` |
| مجلدات البيانات | `/data/odoo19/instance1` / `/data/odoo19/instance2` |
| Traefik | مشترك (HTTPS) |

---

*تم إعداد هذا الدليل كجزء من نظام إدارة البنية التحتية لـ Odoo (Infrastructure Manager).*
