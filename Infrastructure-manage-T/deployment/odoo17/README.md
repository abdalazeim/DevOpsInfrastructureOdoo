# 📦 مستودع نشر نسخ متعددة من Odoo 17 — Odoo 17 Multi-Instance Deployment Repository

> **النظام المدعوم:** Ubuntu Server 22.04 LTS  
> **المكونات:** Odoo 17، PostgreSQL 16، Docker Compose v3.8، Ansible، Jenkins، Traefik  
> **اللغة:** 🇸🇦 العربية • 🇬🇧 English  
> **المستوى:** مشرف نظام / مسؤول بنية تحتية  
> **التاريخ:** نوفمبر 2026  
> **الإصدار:** 1.0.0

---

## 📋 جدول المحتويات

1. [نظرة عامة | Overview](#-نظرة-عامة-overview)
2. [الهندسة المعمارية | Architektur](#-الهندسة-المعمارية-architektur)
3. [هيكل الملفات | File Structure](#-هيكل-الملفات-file-structure)
4. [تكوين النسختين | Instance Configuration](#-تكوين-النسختين-instance-configuration)
5. [خطوط أنابيب Jenkins | Jenkins Pipeline Stages](#-خطوط-أنابيب-Jenkins-jenkins-pipeline-stages)
6. [متغيرات النسخ | Instance Variables](#-متغيرات-النسخ-instance-variables)
7. [ضوابط الأمان | Security Constraints](#-ضوابط-الأمان-security-constraints)
8. [تنظيم الملفات على الخادم | Server Organization](#-تنظيم-الملفات-على-الخادم-server-organization)
9. [تركيب وتشغيل | Installation & Usage](#-تركيب-وتشغيل-installation-usage)
10. [فحص الصحة | Health Check](#-فحص-الصحة-health-check)
11. [النسخ الاحتياطي | Backup](#-النسخ-الاحتياطي-backup)
12. [كلمات مرور المشرف الافتراضية (قبل الإنتاج)](#-كلمات-مرور-المشرف-الافتراضية-قبل-الإنتاج)
13. [المراجع | References](#-المراجع-references)

---

## 1. 📖 نظرة عامة | Overview

هذا المستودع يوفر نظام نشر آلي بالكامل لـ **نسختين من Odoo 17** مع **قواعد بيانات PostgreSQL مستقلة لكل نسخة**، مع دعم النشر عبر Traefik كبروكسي عكسي مع تشفير HTTPS tramite Let's Encrypt.

This repository provides a fully automated deployment system for **two Odoo 17 instances** with **independent PostgreSQL for each instance**, with support for deployment via Traefik reverse proxy with Let's Encrypt HTTPS.

---

## 2. 🏗 الهندسة المعمارية | Architektur

```text
GitHub (المستودع الخاص)
    ↓
Jenkins Pipeline (Install-Odoo17-Two-Instances)
    ↓
Ansible Playbook (نشر تلقائي للنسختين)
    ↓
Docker Compose (تشغيل الحاويات)
    ↓
Traefik (بروكسي عكسي مع HTTPS)
    ↓
Odoo 17 Instance 1 ←→ PostgreSQL 16 (مستقل)
Odoo 17 Instance 2 ←→ PostgreSQL 16 (مستقل)
```

---

## 3. 📁 هيكل الملفات | File Structure

```text
Odoo17-MultiInstance-Deployment/
├── Jenkinsfile                     # مسار تنفيذ Jenkins (8 مراحل)
├── requirements.yml                # مجموعات أنsible المطلوبة
├── README.md                       # هذا الملف
│
├── docker/
│   ├── docker-compose.yml.j2       # قالب تكوين Docker Compose
│   ├── odoo.conf.j2                # قالب تكوين Odoo
│   └── entrypoint.sh               # نقطة دخول الحاوية
│
├── ansible/
│   ├── inventory/
│   │   └── hosts.ini               # مخزون المضيفين
│   ├── playbooks/
│   │   ├── install.yml             # Playbook التثبيت
│   │   ├── validate.yml            # Playbook الفحص المسبق
│   │   └── backup.yml              # Playbook النسخ الاحتياطي
│   ├── roles/
│   │   ├── docker/                 # دور Docker
│   │   ├── odoo/                   # دور Odoo (النشر والنسخ الاحتياطي)
│   │   ├── postgresql/             # دور PostgreSQL
│   │   └── traefik/                # دور Tr
│   └── group_vars/
│       └── all.yml                 # متغيرات عامة
│
├── instances/
│   └── odoo17.yml                  # متغيرات كل نسخة
│
├── scripts/
│   ├── health-check.sh             # سكريبت فحص الصحة
│   └── backup.sh                   # سكريبت النسخ الاحتياطي
│
└── .gitignore                      # ملف استبعاد git
```

---

## 4. 🌐 تكوين النسختين | Instance Configuration

| العنصر | النسخة الأولى (Instance 1) | النسخة الثانية (Instance 2) |
|--------|---------------------------|---------------------------|
| النطاق | `${ODOO17_INSTANCE1_DOMAIN}` | `${ODOO17_INSTANCE2_DOMAIN}` |
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

## 5. ⚙️ خطوط أنابيب Jenkins | Jenkins Pipeline Stages

يحتوي `Jenkinsfile` على مسار execution واحد باسم **Install-Odoo17-Two-Instances** مع 8 مراحل:

| # | المرحلة | الوصف |
|---|---------|-------|
| 1 | Checkout GitHub | سحب آخر نسخة من المستودع الخاص |
| 2 | Pre-Deployment Validation | فحص Docker وCompose وشبكة Traefik والمساحة والذاكرة |
| 3 | Ansible Preparation | تجهيز المجلدات وإعداد مجموعات Ansible |
| 4 | Secrets Configuration | إنشاء وتشفير كلمات مرور PostgreSQL وMaster Password |
| 5 | Docker Deployment | نشر خدمتي Odoo وقاعدتي PostgreSQL عبر Ansible |
| 6 | Traefik Configuration | إضافة Labels وتوجيه النطاقين وإصدار شهادات HTTPS |
| 7 | Health Checks | اختبار قواعد البيانات وOdoo والاتصال عبر HTTPS |
| 8 | Deployment Report | عرض نتيجة النسختين مع الاحتفاظ بسجلات التنفيذ |

---

## 6. 🔧 متغيرات النسخ | Instance Variables

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
    domain: ${ODOO17_INSTANCE1_DOMAIN}
    data_path: /data/odoo17/instance1
    config_path: /opt/odoo17/instance1
    db_name: odoo17_db1
    db_user: odoo17_instance1
    container_name: odoo17-instance1
    traefik_enabled: true

  - name: instance2
    project: odoo17_instance2
    domain: ${ODOO17_INSTANCE2_DOMAIN}
    data_path: /data/odoo17/instance2
    config_path: /opt/odoo17/instance2
    db_name: odoo17_db2
    db_user: odoo17_instance2
    container_name: odoo17-instance2
    traefik_enabled: true
```

---

## 7. 🔒 ضوابط الأمان | Security Constraints

| # | الضابط | التفاصيل |
|---|---------|----------|
| 1 | كلمات مرور مستقلة | كل نسخة لها PostgreSQL وكلمة مرور responsaveل مستقلة |
| 2 | keine كلمات مرور افتراضية | لا تُستخدم كلمات المرور من المستودع الأصلي |
| 3 | keine chmod 777 | جميع الملفات بصلاحيات محدودة (0600 للأسرار، 0755 للمجلدات) |
| 4 | proxy_mode | مفعل في Odoo خلف ترافيك |
| 5 | WebSocket | توجيه `/websocket` إلى منفذ 8072 الداخلي |
| 6 | عدم كشف المنافذ | PostgreSQL وOdoo غير منشورتين مباشرة للإنترنت |
| 7 | الحفاظ على البيانات | `docker compose down` لا يُحذف مجلدات البيانات |
| 8 | النسخ الاحتياطي قبل التحديث | تنفيذ نسخة احتياطية قبل أي تغيير |
| 9 | حماية الأسرار | استخدام Ansible Vault أو Jenkins Credentials |
| 10 | فشل واحد يوقف الكل | إذا فشل اختبار نسخة واحدة، يتوقف النشر ولا يُعلن النجاح |

---

## 8. 📦 تنظيم الملفات على الخادم | Server Organization

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

## 9. 🛠 تركيب وتشغيل | Installation & Usage

### 9.1 المتطلبات الأساسية

| المتطلب | الإصدار |
|---------|---------|
| Docker Engine | 20.10+ |
| Docker Compose | v2+ |
| Ansible | 2.12+ |
| Jenkins | LTS |
| Ubuntu Server | 22.04+ |

### 9.2 خطوات النشر

```bash
# 1. نسخ المستودع
git clone https://github.com/your-org/Odoo-MultiVersion-Deployment.git
cd Odoo17-MultiInstance-Deployment

# 2. تثبيت مجموعات Ansible
ansible-galaxy collection install -r requirements.yml

# 3. إعداد ملفات الأسرار (Vault)
ansible-vault create group_vars/vault.yml

# 4. تشغيل الفحص المسبق
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/validate.yml

# 5. النشر عبر Jenkins
# قم بإنشاء وظيفة جديدة في Jenkins وحدد Jenkinsfile

# 6. أو النشر اليدوي عبر Ansible
ansible-playbook -i ansible/inventory/hosts.ini -e @instances/odoo17.yml ansible/playbooks/install.yml
```

---

## 10. 🔍 فحص الصحة | Health Check

```bash
# فحص النسخة الأولى
./scripts/health-check.sh instance1 8069 8072

# فحص النسخة الثانية
./scripts/health-check.sh instance2 8069 8072
```

---

## 11. 💾 النسخ الاحتياطي | Backup

```bash
# نسخ احتياطي للنسخة الأولى
./scripts/backup.sh instance1 /data/backups/odoo17

# نسخ احتياطي للنسخة الثانية
./scripts/backup.sh instance2 /data/backups/odoo17

# أو عبر Ansible
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/backup.yml
```

---

## 12. 🔑 كلمات مرور المشرف الافتراضية (قبل الإنتاج)

| الإصدار | Odoo Admin Password | PostgreSQL Password | container_name |
|---------|---------------------|---------------------|----------------|
| **Odoo 17** | `odoo17` | `odoo17` | `odoo17` |

> ⚠️ **تنبيه أمني مهم**: هذه كلمات مرور افتراضية للتجربة فقط. **يجب استبدالها قبل النشر في بيئة إنتاج حقيقية** عبر Jenkins Credentials أو ملف `.env` أو Ansible Vault.

---

## 13. 📚 المراجع | References

- [Odoo 17 Documentation](https://www.odoo.com/documentation/17.0/)
- [PostgreSQL 16 Documentation](https://www.postgresql.org/docs/16/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Ansible Documentation](https://docs.ansible.com/)
- [Jenkins Pipeline Documentation](https://www.jenkins.io/doc/book/pipeline/)
- [Traefik Documentation](https://doc.traefik.io/traefik/)

---

**تم التطوير بواسطة:** نظام مدير البنية التحتية (Infrastructure Manager)  
**الإصدار:** 1.0.0 • **آخر تحديث:** نوفمبر 2026

---

*تم إعداد هذا الدليل كجزء من نظام إدارة البنية التحتية لـ Odoo (Infrastructure Manager).*
