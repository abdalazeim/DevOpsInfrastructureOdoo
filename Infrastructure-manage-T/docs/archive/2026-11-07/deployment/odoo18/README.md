# 🐋 نشر Odoo 18 باستخدام Docker و Ansible و Traefik و Jenkins — Odoo 18 Multi-Instance Deployment

> **النظام المدعوم:** Ubuntu Server 22.04 LTS  
> **المكونات:** Odoo 18، PostgreSQL 17، Docker، Ansible، Traefik، Jenkins  
> **المستوى:** مشرف نظام / مسؤول بنية تحتية  
> **التاريخ:** نوفمبر 2026

---

## 📋 جدول المحتويات

1. [نظرة overview](#-نظرة-overview)
2. [هيكل الملفات](#-هيكل-الملفات)
3. [الإعدادات](#-الإعدادات)
4. [النطاقات](#-النطاقات)
5. [مجلدات البيانات](#-مجلدات-البيانات)
6. [التشغيل عبر Terminal](#-التشغيل-عبر-Terminal)
7. [التشغيل عبر Jenkins](#-التشغيل-عبر-Jenkins)
8. [كلمات مرور المشرف الافتراضية (قبل الإنتاج)](#-كلمات-مرور-المشرف-الافتراضية-قبل-الإنتاج)
9. [النسخ الاحتياطي والاستعاشة من الكوارث (Backup & Disaster Recovery)](#-النسخ-الاحتياطي والاستعاشة-من-الكوارث-Backup-Disaster-Recovery)
10. [ملاحظة تقنية importante](#-ملاحظة-تقنية-importante)

---

## 1. 📖 نظرة overview

يدعم هذا المستودع نشر نسختين مستقلتين من Odoo 18 على نفس الخادم، مع عزل كل نسخة في شبكتها الداخلية الخاصة، وربطها بشبكة Traefik المشتركة للوصول عبر HTTPS.

---

## 2. 📁 هيكل الملفات

```text
odoo18/
├── Jenkinsfile                  # Pipeline Jenkins لـ Odoo 18
├── Jenkins/
│   └── install-odoo18.Jenkinsfile
├── scripts/
│   ├── install-odoo18.sh        # سكريبت تثبيت Odoo 18 عبر Terminal
│   ├── health-check.sh          # فحص صحة الخدمات
│   └── backup.sh                # نسخ احتياطية لقواعد البيانات والملفات
├── ansible/
│   ├── inventory/
│   │   └── hosts.ini
│   ├── group_vars/
│   │   └── all.yml
│   ├── playbooks/
│   │   └── install-odoo18.yml
│   ├── roles/
│   │   ├── system/              # إعداد المجلدات والشبكات
│   │   ├── docker/              # نشر حاويات Docker Compose
│   │   ├── postgresql/          # إعداد وتحقق PostgreSQL
│   │   ├── odoo/                # إعداد وتحقق Odoo
│   │   └── traefik/             # إعداد وتحقق Traefik
│   └── templates/
├── versions/
│   └── odoo18.yml               # إعدادات نسخ Odoo 18
├── docker/
│   └── odoo18-compose.yml.j2    # قالب Docker Compose لـ Odoo 18
├── backups/
├── requirements.yml             # متطلبات مجموعات Ansible
└── README.md
```

---

## 3. ⚙️ الإعدادات

| المكون | Odoo 18 |
|--------|---------|
| صورة Odoo Docker | `odoo:18` |
| PostgreSQL | 17 |
| PGDATA المسار | `/var/lib/postgresql/data` |
| المنفذ الداخلي Odoo | 8069 |
| المنفذ الداخلي Live Chat | 8072 |
| عدد النسخ | 2 |
| Traefik | مشترك |
| بيانات PostgreSQL | مستقلة |

---

## 4. 🌐 النطاقات

| النسخة | النطاق |
|--------|--------|
| Odoo 18 - النسخة 1 | `${ODOO18_INSTANCE1_DOMAIN}` |
| Odoo 18 - النسخة 2 | `${ODOO18_INSTANCE2_DOMAIN}` |

---

## 5. 📂 مجلدات البيانات

| المكون | المسار |
|--------|--------|
| Odoo 18 - النسخة 1 | `/data/odoo18/instance1` |
| Odoo 18 - النسخة 2 | `/data/odoo18/instance2` |

---

## 6. 🖥️ التشغيل عبر Terminal

```bash
cd /opt/Odoo-MultiVersion-Deployment/odoo18
sudo ./scripts/install-odoo18.sh
```

---

## 7. 🔗 التشغيل عبر Jenkins

| الزر | الوصف |
|------|--------|
| Install Odoo 18 – Two Instances | يثبّت نسختي Odoo 18 مع PostgreSQL 17 |

---

## 8. 🔑 كلمات مرور المشرف الافتراضية (قبل الإنتاج)

| الإصدار | Odoo Admin Password | PostgreSQL Password | container_name |
|---------|---------------------|---------------------|----------------|
| **Odoo 18** | `odoo18` | `odoo18` | `odoo18` |

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

- **Backup All**: نسخ شامل لكل نسخ Odoo 18.
- **Backup Selected**: اختيار نسخة معينة (مثل Odoo 18 Instance 1).

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
├── odoo18/
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
cd /opt/Odoo-MultiVersion-Deployment/odoo18
sudo ./scripts/backup.sh instance1 /data/backups/odoo18
sudo ./scripts/backup.sh instance2 /data/backups/odoo18

# أوامر مستقلة عبر Terminal
sudo ./scripts/backup.sh --all              # نسخ شامل لجميع نسخ Odoo
sudo ./scripts/backup.sh --version 18       # نسخ Odoo 18 فقط
sudo ./scripts/backup.sh --instance odoo18-instance1  # نسخة محددة
sudo ./scripts/verify-backups.sh            # فحص النسخ الاحتياطية
sudo ./scripts/list-backups.sh              # عرض النسخ المتوفرة
sudo ./scripts/restore.sh --backup-id BACKUP_ID  # استعادة نسخة احتياطية
```

---

## 10. ⚠️ ملاحظة تقنية importante

يجب استبدال كلمات المرور الافتراضية ومراجعة استخدام `user: root` وصلاحيات الملفات قبل الإنتاج.

---

*تم إعداد هذا الدليل كجزء من نظام إدارة البنية التحتية لـ Odoo (Infrastructure Manager).*
