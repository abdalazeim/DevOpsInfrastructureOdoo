# Odoo 17 Multi-Instance Deployment - Unified System

> نظام نشر موحد لـ **نسختين من Odoo 17** مع **PostgreSQL 16 مستقل لكل نسخة** عبر Docker Compose وAnsible وJenkins، مع دعم ترافيك كبروكسي عكسي مع HTTPS.

<div align="center">

[![Odoo 17](https://img.shields.io/badge/Odoo-17-blue?logo=odoo)](https://www.odoo.com/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)](https://www.postgresql.org/)
[![Docker Compose](https://img.shields.io/badge/Docker%20Compose-v3.8-blue?logo=docker)](https://docs.docker.com/compose/)
[![Ansible](https://img.shields.io/badge/Ansible-Unified-green?logo=ansible)](https://www.ansible.com/)
[![Jenkins](https://img.shields.io/badge/Jenkins-Pipeline-blue?logo=jenkins)](https://www.jenkins.io/)
[![Traefik](https://img.shields.io/badge/Traefik-HTTPS-green?logo=traefik)](https://traefik.io/)

**اللغة:** 🇸🇦 العربية • 🇬🇧 English

</div>

---

## 📋 نظرة عامة | Overview

هذا النظام يوفر **طريقتين مستقلتين للتشغيل** لنشر نسختين من Odoo 17، مع استخدام **نفس ملفات التثبيت والإعدادات** في الحالتين، مما يضمن نتائج متطابقة بين Jenkins وTerminal.

This system provides **two independent execution methods** for deploying two Odoo 17 instances, using **the same installation files and settings** in both, ensuring identical results between Jenkins and Terminal.

---

## 🚀 طريقتا التشغيل | Two Execution Methods

| الطريقة | الأمر / الزر | الملف المستخدم |
|--------|-------------|---------------|
| **Jenkins** | زر `Build Now` في Pipeline `Install-Odoo17-Two-Instances` | `Jenkinsfile` → `ansible/playbooks/install.yml` |
| **Terminal** | `sudo ./scripts/install-odoo17.sh` | `scripts/install-odoo17.sh` → `ansible/playbooks/install.yml` |

### الطريقة الأولى: Jenkins | Method 1: Jenkins

1. إنشاء Pipeline باسم `Install-Odoo17-Two-Instances`
2. الضغط على زر **Build Now**
3. يبدأ تلقائياً:
   - الاتصال بمستودع GitHub الخاص
   - سحب ملفات المشروع وإعدادات التثبيت
   - تشغيل Ansible Playbook الموحد
   - فحص Ubuntu وDocker وDocker Compose
   - تثبيت المتطلبات الناقصة
   - إنشاء المجلدات والشبكات والصلاحيات
   - إنشاء قاعدتي PostgreSQL مستقلتين
   - تثبيت وتشغيل نسختي Odoo 17
   - إعداد ملفات odoo.conf وCustom Addons
   - إعداد Docker Compose لكل نسخة
   - ربط النسختين مع Traefik
   - إعداد HTTPS وشهادات SSL
   - اختبار اتصال Odoo وقواعد البيانات
   - إنشاء تقرير نهائي بنتائج التثبيت

### الطريقة الثانية: Terminal | Method 2: Terminal

```bash
cd /opt/Odoo17-MultiInstance-Deployment
sudo ./scripts/install-odoo17.sh
```

يقوم السكربت تلقائياً بـ:
- التحقق من المتطلبات
- سحب آخر نسخة معتمدة من GitHub (إذا كان المستودع مرتبطاً)
- تشغيل Ansible Playbook الموحد
- تثبيت وإعداد النسختين
- اختبار الخدمات
- عرض تقرير التنفيذ

---

## 🏗 Architektur | Architecture

```text
GitHub (المستودع الخاص)
    ↓
┌─────────────┐     ┌─────────────┐
│  Jenkins    │     │  Terminal   │
│ Build Now   │     │ install.sh  │
└─────────────┘     └─────────────┘
        ↓                 ↓
   نفس Ansible Playbook  (الموحد)
        ↓
   ansible/playbooks/install.yml
        ↓
   roles: system → docker → postgresql → odoo → traefik
        ↓
   Docker Compose → حاويات Odoo 17 × 2
        ↓
   Traefik (بروكسي عكسي مع HTTPS)
        ↓
Odoo 17 Instance 1 ←→ PostgreSQL 16 (مستقل)
Odoo 17 Instance 2 ←→ PostgreSQL 16 (مستقل)
```

---

## 📁 هيكل الملفات | File Structure

```text
Odoo17-MultiInstance-Deployment/
├── Jenkinsfile                     # مسار تنفيذ Jenkins (8 مراحل)
├── requirements.yml                # مجموعات أنsible المطلوبة
├── README.md                       # هذا الملف
├── .gitignore                      # ملف استبعاد git
│
├── ansible/
│   ├── inventory/
│   │   └── hosts.ini               # مخزون المضيفين (localhost)
│   ├── group_vars/
│   │   └── all.yml                 # متغيرات عامة (صور، شبكات، ترافيك)
│   ├── playbooks/
│   │   └── install.yml             # Playbook التثبيت الموحد (يستخدمه Jenkins و Terminal)
│   ├── roles/
│   │   ├── system/                 # فحص النظام وتثبيت المتطلبات
│   │   ├── docker/                 # التحقق من Docker Engine وCompose
│   │   ├── postgresql/             # التحقق من صورة PostgreSQL
│   │   ├── odoo/                   # نشر كل نسخة، نسخ احتياطي
│   │   └── traefik/                # التحقق من شبكة proxy وإنشائها
│   └── templates/
│       ├── docker-compose.yml.j2   # قالب Docker Compose (Jinja2)
│       ├── odoo.conf.j2            # قالب تكوين Odoo (Jinja2)
│       └── entrypoint.sh           # نقطة دخول الحاوية
│
├── instances/
│   └── odoo17.yml                  # متغيرات كل نسخة (Instance 1 و Instance 2)
│
├── scripts/
│   ├── install-odoo17.sh           # سكريبت التثبيت الموحد (Terminal)
│   ├── health-check.sh             # سكريبت فحص الصحة
│   └── backup.sh                   # سكريبت النسخ الاحتياطي
│
└── config/                         # ملفات التكوين الجاهزة
```

---

## 🌐 تكوين النسختين | Instance Configuration

| العنصر | النسخة الأولى (Instance 1) | النسخة الثانية (Instance 2) |
|--------|---------------------------|---------------------------|
| النطاق | `odoo1.devops-odoo.com` | `odoo2.devops-odoo.com` |
| إصدار Odoo | 17 | 17 |
| إصدار PostgreSQL | 16 (مستقل) | 16 (مستقل) |
| اسم الحاوية | `odoo17-instance1` | `odoo17-instance2` |
| اسم قاعدة البيانات | `odoo17_db1` | `odoo17_db2` |
| منفذ الويب الداخلي | 8069 | 8069 |
| منفذ الدردشة الداخلي | 8072 | 8072 |
| مسار البيانات | `/data/odoo17/instance1` | `/data/odoo17/instance2` |
| مسار التكوين | `/opt/odoo17/instance1` | `/opt/odoo17/instance2` |
| الشبكة الداخلية | `odoo17_instance1_internal` | `odoo17_instance2_internal` |
| ترافيك | مفعل (HTTPS) | مفعل (HTTPS) |

> **ملاحظة:** كل نسخة تعمل في شبكة Docker منفصلة، لذا لا يوجد تعارض بين المنافذ الداخلية. ترافيك يتصل بالحاويتين من خلال شبكة `proxy` المشتركة.

---

## ⚙️ متغيرات النسخ | Instance Variables

```yaml
# instances/odoo17.yml
odoo_version: "17"
postgres_version: "16"
odoo_image: "odoo:17"
postgres_image: "postgres:16"
docker_network: "proxy"
traefik_entrypoint: "websecure"
traefik_certresolver: "letsencrypt"

odoo_instances:
  - name: instance1
    project: odoo17_instance1
    domain: odoo1.devops-odoo.com
    data_path: /data/odoo17/instance1
    config_path: /opt/odoo17/instance1
    http_port: 8069
    chat_port: 8072
    db_name: odoo17_db1
    db_user: odoo17_instance1
    container_name: odoo17-instance1
    traefik_enabled: true

  - name: instance2
    project: odoo17_instance2
    domain: odoo2.devops-odoo.com
    data_path: /data/odoo17/instance2
    config_path: /opt/odoo17/instance2
    http_port: 8069
    chat_port: 8072
    db_name: odoo17_db2
    db_user: odoo17_instance2
    container_name: odoo17-instance2
    traefik_enabled: true
```

---

## 🔒 ضوابط الأمان | Security Constraints

| الضابط | التفاصيل |
|--------|---------|
| كلمات مرور مستقلة | كل نسخة لها PostgreSQL وكلمة مرور responsaveل مستقلة |
| keine كلمات مرور افتراضية | لا تُستخدم كلمات المرور من المستودع الأصلي |
| keine chmod 777 | جميع الملفات بصلاحيات محدودة (0600 للأسرار، 0755 للمجلدات) |
| proxy_mode | مفعل في Odoo خلف ترافيك |
| WebSocket | توجيه `/websocket` إلى منفذ 8072 الداخلي |
| عدم كشف المنافذ | PostgreSQL وOdoo غير منشورتين مباشرة للإنترنت |
| الحفاظ على البيانات | `docker compose down` لا يُحذف مجلدات البيانات |
| النسخ الاحتياطي قبل التحديث | تنفيذ نسخة احتياطية قبل أي تغيير |
| حماية الأسرار | استخدام Ansible Vault أو Jenkins Credentials |
| فشل واحد يتوقف الكل | إذا فشل اختبار نسخة واحدة، يتوقف النشر ولا يُعلن النجاح |
| نفس playbook للطريقتين | Jenkins و Terminal يستخدمان نفس ansible/playbooks/install.yml |

---

## 📦 تنظيم الملفات على الخادم | Server Organization

```text
/opt/
├── jenkins/
├── ansible/
├── Odoo17-MultiInstance-Deployment/
├── odoo17/
│   ├── instance1/
│   │   ├── docker-compose.yml
│   │   ├── etc/
│   │   └── addons/
│   └── instance2/
│       ├── docker-compose.yml
│       ├── etc/
│       └── addons/
└── traefik/

/data/
├── jenkins/
├── odoo17/
│   ├── instance1/
│   │   ├── postgresql/
│   │   └── filestore/
│   └── instance2/
│       ├── postgresql/
│       └── filestore/
└── backups/
    └── odoo17/
        ├── instance1/
        └── instance2/
```

---

## 🛠 تركيب وتشغيل | Installation & Usage

### المتطلبات الأساسية

| المتطلب | الإصدار |
|---------|---------|
| Docker Engine | 20.10+ |
| Docker Compose | v2+ |
| Ansible | 2.12+ |
| Jenkins | LTS |
| Ubuntu Server | 22.04+ |

### التشغيل عبر Terminal

```bash
cd /opt/Odoo17-MultiInstance-Deployment
sudo ./scripts/install-odoo17.sh
```

### التشغيل عبر Jenkins

1. إنشاء Pipeline جديد في Jenkins باسم `Install-Odoo17-Two-Instances`
2. تحديد ملف `Jenkinsfile` من المستودع
3. الضغط على زر **Build Now**

---

## 🔍 فحص الصحة | Health Check

```bash
# فحص النسخة الأولى
./scripts/health-check.sh instance1 8069 8072

# فحص النسخة الثانية
./scripts/health-check.sh instance2 8069 8072
```

---

## 💾 النسخ الاحتياطي | Backup

```bash
# نسخ احتياطي للنسخة الأولى
./scripts/backup.sh instance1 /data/backups/odoo17

# نسخ احتياطي للنسخة الثانية
./scripts/backup.sh instance2 /data/backups/odoo17
```

---

## 🔑 كلمات مرور المشرف الافتراضية (قبل الإنتاج)

| الإصدار | Odoo Admin Password | PostgreSQL Password | container_name |
|---------|---------------------|---------------------|----------------|
| **Odoo 17** | `odoo17` | `odoo17` | `odoo17` |

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

- **Backup All**: نسخ شامل لكل نسخ Odoo 17 و19.
- **Backup Selected**: اختيار نسخة معينة (مثل Odoo 17 Instance 1).

### عملية النسخ الصحيحة (ضمان التوافق بين قاعدة البيانات وFilestore)

لمنع فقدان المرفقات أو عدم التوافق بين قاعدة البيانات وFilestore، تتبع العملية الخطوات التالية:

1. التحقق من مساحة التخزين المتاحة.
2. التأكد من أن PostgreSQL يعمل ويستجيب.
3. **إيقاف خدمة Odoo مؤقتًا** لمنع التعديلات أثناء النسخ (محمية بـ `try/finally`).
4. تصدير قاعدة البيانات باستخدام `pg_dump` بصيغة Custom.
5. حفظ صلاحيات ومستخدمي PostgreSQL عند الحاجة.
6. نسخ Filestore (المرفقات والصور والملفات).
7. نسخ Custom Addons وملفات الإعداد.
8. إنشاء ملف Manifest يحتوي على معلومات النسخة.
9. إنشاء Checksums (SHA256) للتحقق من سلامة الملفات.
10. **إعادة تشغيل Odoo** (حتى في حالة فشل النسخ، عبر `finally`).
11. تسجيل نتيجة العملية في السجلات.

> ⚠️ **مهم**: لا يكفي نسخ قاعدة PostgreSQL وحدها؛ فقد تفقد المرفقات الموجودة في Filestore حتى لو استعدت قاعدة البيانات بنجاح. يجب الحفاظ على التوافق بين قاعدة البيانات وFilestore.

### تنظيم مجلدات النسخ الاحتياطية

```
/data/backups/
├── odoo17/
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
├── odoo18/
│   ├── instance1/
│   └── instance2/
│
├── odoo19/
│   ├── instance1/
│   └── instance2/
│
├── infrastructure/
│   ├── ansible/
│   ├── traefik/
│   └── docker/
│
├── jenkins/
│
└── reports/
```

### ملف معلومات النسخة الاحتياطية (Manifest)

```json
{
  "backup_id": "odoo17-instance1-20261104",
  "odoo_version": "17",
  "postgres_version": "16",
  "instance": "instance1",
  "database": "odoo17_db1",
  "backup_type": "full",
  "created_at": "2026-11-04T02:00:00+02:00",
  "database_backup": "database.dump",
  "filestore_backup": "filestore.tar.zst",
  "addons_backup": "addons.tar.zst",
  "config_backup": "config.tar.zst",
  "integrity_check": "sha256",
  "status": "completed"
}
```

### أخذ نسخة احتياطية

```bash
# نسخ احتياطي للنسخة الأولى (Odoo 17)
./scripts/backup.sh instance1 /data/backups/odoo17

# نسخ احتياطي للنسخة الثانية (Odoo 17)
./scripts/backup.sh instance2 /data/backups/odoo17

# أو عبر Ansible
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/backup.yml
```

### استعادة قاعدة بيانات (مع تدابير الأمان)

```bash
bash automation/scripts/restore-db.sh 17 /opt/odoo-infrastructure/backups/odoo17/dump_odoo17_prod_XXXX.sql.gz odoo17_prod --force
```

> ⚠️ **أمان الاستعادة**: عند تمرير `--force`، يقوم النظام تلقائياً بتوليد نسخة أمان احتياطية في مجلد `safety_pre_restore` قبل الكتابة فوق أي قاعدة بيانات قائمة، ويتطلب تأكيداً كتابياً صريحاً (`RESTORE-SNAPSHOT-<ID>`).

## 🔄 طريقة الاستعادة (Restore)

الاستعادة أهم من عملية النسخ نفسها. يجب ألا يكون زر الاستعادة مجرد فك ضغط للملفات.

### أنواع الاستعادة المدعومة

| النوع | الوصف | الاستخدام |
|-------|-------|-----------|
| **Restore to Existing Instance** | استعادة النسخة فوق نسخة موجودة بعد أخذ احتياط إضافي منها | الاستعادة العادية للإصدار الحالي |
| **Restore as New Instance** | إنشاء نسخة جديدة مستقلة للاختبار دون التأثير على النسخة الأصلية | الاختبار والتطوير |

### خطوات الاستعادة التلقائية

عند اختيار نسخة احتياطية، ينفذ النظام الخطوات التالية:

| الخطوة | الإجراء | التفاصيل |
|-------|---------|----------|
| 1 | فحص سلامة الملفات | التحقق من SHA256 و checksums لجميع ملفات النسخة |
| 2 | التحقق من الإصدارات | التأكد من توافق إصدار Odoo و PostgreSQL مع النسخة الاحتياطية |
| 3 | التحقق من المساحة | التأكد من وجود مساحة تخزين كافية للاستعادة |
| 4 | إيقاف Odoo | إيقاف الحاوية المستهدفة قبل الاستبدال |
| 5 | نسخة احتياطية للحالة الحالية | أخذ نسخة احتياطية من الحالة الحالية قبل الاستبدال (حالة الطوارئ) |
| 6 | استعادة PostgreSQL | إنشاء قاعدة البيانات واستعادة البيانات من `pg_dump` |
| 7 | استعادة Filestore | استعادة المرفقات والصور في مسارها الصحيح |
| 8 | استعادة Custom Addons | استعادة الإضافات والتعديلات البرمجية المتوافقة |
| 9 | ضبط الصلاحيات | تعيين صلاحيات الملفات والمجلدات correctamente |
| 10 | تشغيل Odoo | إعادة تشغيل الحاوية وتأكيد عملها |
| 11 | اختبارات التحقق | اختبار قاعدة البيانات والمرفقات والوصول عبر المتصفح |
| 12 | تقرير الاستعادة | تسجيل تقرير كامل بعملية الاستعادة ونتيجتها |

### ضمانات الاستعادة

> ✅ **لا تحذف قاعدة البيانات الحالية أو تستبدل ملفاتها قبل التحقق من النسخة الاحتياطية الجديدة.**
> ✅ **إذا فشلت الاستعادة، يتم العودة تلقائياً إلى الحالة السابقة.**
> ✅ **عملية الإيقاف والإعادة محمية بـ `try/finally` لضمان عدم بقاء الخدمة متوقفة.**

### أوامر الاستعادة

```bash
# استعادة إلى نسخة موجودة
bash automation/scripts/restore-db.sh 17 /opt/odoo-infrastructure/backups/odoo17/dump_odoo17_prod_XXXX.sql.gz odoo17_prod --force

# استعادة كنسخة جديدة (للاختبار)
bash automation/scripts/restore-db.sh 17 /opt/odoo-infrastructure/backups/odoo17/dump_odoo17_prod_XXXX.sql.gz odoo17_test --new-instance
```

---

## 🔧 تشغيل النسخ الاحتياطي من Jenkins وTerminal

### خطوط أنابيب Jenkins للنسخ الاحتياطي والاستعادة

يوفر النظام ثلاثة خطوط أنابيب (Pipelines) مستقلة في Jenkins:

| الحipeline | الغرض | الزر |
|-----------|--------|------|
| **Backup-Odoo** | نسخ احتياطي شامل لجميع نسخ Odoo 17 و19 أو نسخة محددة | `Build Now` |
| **Restore-Odoo** | استعادة نسخة احتياطية مع تأكيد مطلوب | `Build Now` (يتطلب تأكيد) |
| **Verify-Backups** | فحص سلامة الملفات وقواعد البيانات وتجربة الاستعادة في بيئة اختبار | `Build Now` |

#### Pipeline 1: Backup-Odoo

يؤدي نسخًا احتياطيًا شاملاً لبيانات Odoo وFilestore والإعدادات.

```groovy
// مراحل Backup-Odoo:
// 1. اختيار الإصدار والنسخة (أو all)
// 2. التحقق من مساحة التخزين
// 3. أخذ نسخة احتياطية من PostgreSQL وFilestore
// 4. إنشاء ملف Manifest و Checksums
// 5. رفع النسخة إلى موقع التخزين الآمن
```

#### Pipeline 2: Restore-Odoo

يؤدي استعادة نسخة احتياطية مع تأكيد صريح من المستخدم.

```groovy
// مراحل Restore-Odoo:
// 1. اختيار النسخة الاحتياطية للتاريخ والإصدار
// 2. تأكيد الاستعادة (مطلوب)
// 3. فحص سلامة النسخة (SHA256)
// 4. إيقاف Odoo المستهدف
// 5. أخذ نسخة احتياطية من الحالة الحالية
// 6. استعادة PostgreSQL وFilestore وAddons
// 7. تشغيل Odoo وإجراء اختبارات التحقق
// 8. تقرير الاستعادة النهائي
```

#### Pipeline 3: Verify-Backups

يؤدي فحصًا تلقائيًا لسلامة جميع النسخ الاحتياطية.

```groovy
// مراحل Verify-Backups:
// 1. فحص جميع ملفات النسخ الاحتياطية
// 2. التحقق من SHA256 و checksums
// 3. تجربة استعادة في بيئة اختبار معزولة
// 4. تقرير التحقق النهائي
```

### التشغيل عبر Terminal

```bash
# نسخ احتياطي
./scripts/backup.sh instance1 /data/backups/odoo17
./scripts/backup.sh instance2 /data/backups/odoo17

# استعادة
bash automation/scripts/restore-db.sh 17 <backup_file> <database_name> --force

# فحص صحة النسخ
./scripts/health-check.sh instance1 8069 8072
```

---

## 📚 المراجع | References

- [Odoo 17 Documentation](https://www.odoo.com/documentation/17.0/)
- [PostgreSQL 16 Documentation](https://www.postgresql.org/docs/16/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Ansible Documentation](https://docs.ansible.com/)
- [Jenkins Pipeline Documentation](https://www.jenkins.io/doc/book/pipeline/)
- [Traefik Documentation](https://doc.traefik.io/traefik/)

---

<div align="center">

**تم التطوير بواسطة:** نظام مدير البنية التحتية (Infrastructure Manager)

**الإصدار:** 1.0.0 • **آخر تحديث:** نوفمبر 2026

**الطريقتان تستخدمان نفس Ansible Playbook لضمان نتائج متطابقة**

</div>