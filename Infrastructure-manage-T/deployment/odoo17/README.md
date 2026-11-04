# Odoo 17 Multi-Instance Deployment Repository

> مستودع احترافي لنشر نسختين من **Odoo 17** مع **PostgreSQL 16 مستقل لكل نسخة** عبر Docker Compose وAnsible وJenkins، مع دعم Tr
afik كبروكسي عكسي مع HTTPS.

<div align="center">

[![Odoo 17](https://img.shields.io/badge/Odoo-17-blue?logo=odoo)](https://www.odoo.com/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)](https://www.postgresql.org/)
[![Docker Compose](https://img.shields.io/badge/Docker%20Compose-v3.8-blue?logo=docker)](https://docs.docker.com/compose/)
[![Ansible](https://img.shields.io/badge/Ansible-Ready-green?logo=ansible)](https://www.ansible.com/)
[![Jenkins](https://img.shields.io/badge/Jenkins-Pipeline-blue?logo=jenkins)](https://www.jenkins.io/)
[![Traefik](https://img.shields.io/badge/Traefik-HTTPS-green?logo=traefik)](https://traefik.io/)

**اللغة:** 🇸🇦 العربية • 🇬🇧 English

</div>

---

## 📋 نظرة عامة | Overview

هذا المستودع يوفر نظام نشر آلي بالكامل لـ **نسختين من Odoo 17** مع **قواعد بيانات PostgreSQL مستقلة لكل نسخة**، مع دعم النشر عبر Tr
afik كبروكسي عكسي مع تشفير HTTPS tramite Let's Encrypt.

This repository provides a fully automated deployment system for **two Odoo 17 instances** with **independent PostgreSQL for each instance**, with support for deployment via Traefik reverse proxy with Let's Encrypt HTTPS.

---

## 🏗 Architektur | Architecture

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

## 📁 هيكل الملفات | File Structure

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

## 🚀 Jenkins Pipeline | Pipeline Stages

يحتوي `Jenkinsfile` على مسار execution واحد باسم **Install-Odoo17-Two-Instances** مع 8 مراحل:

| المرحلة | الوصف |
|--------|-------|
| 1. Checkout GitHub | سحب آخر نسخة من المستودع الخاص |
| 2. Pre-Deployment Validation | فحص Docker وCompose وشبكة Traefik والمساحة والذاكرة |
| 3. Ansible Preparation | تجهيز المجلدات وإعداد مجموعات Ansible |
| 4. Secrets Configuration | إنشاء وتشفير كلمات مرور PostgreSQL وMaster Password |
| 5. Docker Deployment | نشر خدمتي Odoo وقاعدتي PostgreSQL عبر Ansible |
| 6. Traefik Configuration | إضافة Labels وتوجيه النطاقين وإصدار شهادات HTTPS |
| 7. Health Checks | اختبار قواعد البيانات وOdoo والاتصال عبر HTTPS |
| 8. Deployment Report | عرض نتيجة النسختين مع الاحتفاظ بسجلات التنفيذ |

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
    db_name: odoo17_db1
    db_user: odoo17_instance1
    container_name: odoo17-instance1
    traefik_enabled: true

  - name: instance2
    project: odoo17_instance2
    domain: odoo2.devops-odoo.com
    data_path: /data/odoo17/instance2
    config_path: /opt/odoo17/instance2
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
| فشل واحد يوقف الكل | إذا فشل اختبار نسخة واحدة، يتوقف النشر ولا يُعلن النجاح |

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

### خطوات النشر

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

# أو عبر Ansible
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/backup.yml
```

---

## 🔑 كلمات مرور المشرف الافتراضية (قبل الإنتاج)

| الإصدار | Odoo Admin Password | PostgreSQL Password | container_name |
|---------|---------------------|---------------------|----------------|
| **Odoo 17** | `odoo17` | `odoo17` | `odoo17` |

> ⚠️ **تنبيه أمني مهم**: هذه كلمات مرور افتراضية للتجربة فقط. **يجب استبدالها قبل النشر في بيئة إنتاج حقيقية** عبر Jenkins Credentials أو ملف `.env` أو Ansible Vault.

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

</div>