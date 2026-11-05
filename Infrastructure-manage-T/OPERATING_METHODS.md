# 🚀 Odoo Multi-Version Deployment - طرق التشغيل (Linux Ubuntu فقط)

> **النظام المستهدف:** Linux Ubuntu (الإصدارات 20، 22، 24 وما فوق)  
> **ملاحظة:** هذا النظام مبرمج بالكامل لـ **Linux Ubuntu** ولا يحتوي على أي مكونات خاصة بنظام Windows. المسار أعلاه هو مسار تخزين على قرص Windows لتسهيل التعديل فقط، لكن التنفيذ الفعلي يتم على خادم Linux Ubuntu.  
> **المستوى:** مشرف نظام / مسؤول بنية تحتية  
> **التاريخ:** نوفمبر 2026  
> **الإصدار:** 1.0  
> **الحالة:** Production Ready

---

## 📋 جدول المحتويات

1. [موقع المشروع](#-موقع-المشروع)
2. [متطلبات النظام (Linux Ubuntu)](#-متطلبات-النظام-Linux-Ubuntu)
3. [الطريقة الأولى: التشغيل السريع (أمر واحد)](#-الطريقة-الألية-التشغيل-السريع-أمر-واحد)
4. [الطريقة الثانية: التنفيذ خطوة بخطوة](#-الطريقة-الثانية-التنفيذ-خطوة-بخطوة)
5. [الطريقة الثالثة: التنفيذ اليدوي لكل مكون](#-الطريقة-الثالثة-التنفيذ-اليدوي-لكل-مكون)
6. [الطريقة الرابعة: عبر Jenkins](#-الطريقة-الرابعة-عبر-Jenkins)
7. [الطريقة الخامسة: عبر أنsible Playbooks مباشرة](#-الطريقة-الخامسة-عبر-Ansible-Playbooks-مباشرة)
8. [الروابط النهائية بعد التشغيل الناجح](#-الروابط-النهائية-بعد-التشغيل-الناجح)
9. [ملاحظة هامة حول الصلاحيات](#-ملاحظة-هامة-حول-الصلاحيات)
10. [ملفات السكريبت في المجلد](#-ملفات-السكريبت-في-المجلد)
11. [مسارات النظام بعد التثبيت](#-مسارات-النظام-بعد-التثبيت)
12. [الدعم](#-الدعم)

---

## 1. 📍 موقع المشروع

```
D:\Project Django Frameworks\DevOpsInfrastructureOdoo\Infrastructure-manage-T\deployment\Odoo-MultiVersion-Deployment\scripts\
```

> **تنبيه هام**: هذا النظام مبرمج بالكامل لـ **Linux Ubuntu** (الإصدارات 20، 22، 24 وما فوق). لا يحتوي على أي مكونات خاصة بنظام Windows. المسار أعلاه هو مسار تخزين على قرص Windows لتسهيل التعديل فقط، لكن التنفيذ الفعلي يتم على خادم Linux Ubuntu.

---

## 2. 🔧 متطلبات النظام (Linux Ubuntu)

| # | المكون | الحد الأدنى | الموصى به |
|---|---------|-----------|-----------|
| 1 | نظام التشغيل | Ubuntu Server 20.04 LTS | Ubuntu Server 22.04 / 24.04 LTS |
| 2 | المعالج | 2 نوى | 4 نوى أو أكثر |
| 3 | الذاكرة | 4 جيجابايت RAM | 8 جيجابايت RAM أو أكثر |
| 4 | التخزين | 100 جيجابايت SSD | 500 جيجابايت SSD أو أكثر |
| 5 | Docker Engine | 20.10+ | أحدث إصدار |
| 6 | Docker Compose | v2 | أحدث إصدار |
| 7 | Ansible | Core + collections | أحدث إصدار |
| 8 | Python3 | 3.8+ | أحدث إصدار |
| 9 | Git | 2.x | أحدث إصدار |

---

## 3. ⚡ الطريقة الأولى: التشغيل السريع (أمر واحد)

افتح المحطة على خادم Linux Ubuntu الخاص بك وشغل الأمر التالي:

```bash
# الانتقال إلى مجلد السكريبتات
cd /opt/Odoo-MultiVersion-Deployment/scripts

# تشغيل السكريبت الرئيسي بصلاحيات الجذر (يقوم بتشغيل bootstrap تلقائياً)
sudo bash launch-odoo-infra.sh
```

---

## 4. 📋 الطريقة الثانية: التنفيذ خطوة بخطوة

### الخطوة 1: تثبيت التبعيات وتجهيز البيئة

```bash
sudo bash bootstrap-odoo-infra.sh
```

### الخطوة 2: تشغيل المشروع وتثبيت Odoo 17 و 19

```bash
sudo bash launch-odoo-infra.sh
```

---

## 5. 🛠️ الطريقة الثالثة: التنفيذ اليدوي لكل مكون

### 5.1 تثبيت Odoo 17 فقط (نسختان مستقلتان)

```bash
sudo bash install-odoo17.sh
```

### 5.2 تثبيت Odoo 19 فقط (نسختان مستقلتان)

```bash
sudo bash install-odoo19.sh
```

### 5.3 فحص صحة الخدمات

```bash
sudo bash health-check.sh instance1 8069 8072
sudo bash health-check.sh instance2 8069 8072
```

### 5.4 أخذ نسخة احتياطية

```bash
sudo bash backup.sh instance1 odoo17 /data/backups/odoo17
sudo bash backup.sh instance2 odoo17 /data/backups/odoo17
sudo bash backup.sh instance1 odoo19 /data/backups/odoo19
sudo bash backup.sh instance2 odoo19 /data/backups/odoo19
```

### 5.5 استعادة نسخة احتياطية

```bash
sudo bash restore.sh odoo17-instance1-20261104 odoo17 instance1 existing
```

### 5.6 التحقق من سلامة النسخة الاحتياطية

```bash
sudo bash verify-backups.sh /data/backups
```

### 5.7 عرض جميع النسخ الاحتياطية المتاحة

```bash
sudo bash list-backups.sh /data/backups
```

### 5.8 نسخ إعدادات نظام Ubuntu

```bash
sudo bash backup-system-config.sh
```

### 5.9 استعادة إعدادات نظام Ubuntu

```bash
sudo bash restore-system-config.sh 2026-11-04_020000
```

---

## 6. 🔗 الطريقة الرابعة: عبر Jenkins

افتح لوحة تحكم Jenkins على خادم Linux الخاص بك وشغل خطوط الأنابيب التالية:

| خط الأنابيب | المسار | الغرض |
|----------|------|---------|
| تثبيت Odoo 17 | `Jenkins/install-odoo17.Jenkinsfile` | تثبيت نسختين من Odoo 17 |
| تثبيت Odoo 19 | `Jenkins/install-odoo19.Jenkinsfile` | تثبيت نسختين من Odoo 19 |
| النسخ الاحتياطي | `Jenkins/backup.Jenkinsfile` | أخذ نسخة احتياطية |
| الاستعادة | `Jenkins/restore.Jenkinsfile` | استعادة نسخة احتياطية (يتطلب تأكيد) |
| التحقق من النسخ الاحتياطية | `Jenkins/verify-backups.Jenkinsfile` | التحقق من سلامة النسخ الاحتياطية |
| نسخ إعدادات النظام | `Jenkins/system-config-backup.Jenkinsfile` | نسخ إعدادات نظام Ubuntu |

---

## 7. 🔧 الطريقة الخامسة: عبر Ansible Playbooks مباشرة

```bash
# الانتقال إلى مجلد المشروع
cd /opt/Odoo-MultiVersion-Deployment

# تثبيت Odoo 17
ansible-playbook -i ansible/inventory/hosts.ini -e @versions/odoo17.yml ansible/playbooks/install-odoo17.yml

# تثبيت Odoo 19
ansible-playbook -i ansible/inventory/hosts.ini -e @versions/odoo19.yml ansible/playbooks/install-odoo19.yml

# أخذ نسخة احتياطية
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/backup.yml

# التحقق من النسخ الاحتياطية
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/verify.yml

# نسخ إعدادات نظام التكوين
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/system-config-backup.yml
```

---

## 8. 🔗 الروابط النهائية بعد التشغيل الناجح

| الخدمة | الرابط |
|---------|------|
| Odoo 17 - النسخة 1 | https://${ODOO17_INSTANCE1_DOMAIN} |
| Odoo 17 - النسخة 2 | https://${ODOO17_INSTANCE2_DOMAIN} |
| Odoo 19 - النسخة 1 | https://${ODOO19_INSTANCE1_DOMAIN} |
| Odoo 19 - النسخة 2 | https://${ODOO19_INSTANCE2_DOMAIN} |

---

## 9. ⚠️ ملاحظة هامة حول الصلاحيات

يجب تشغيل جميع السكريبتات بصلاحيات **الجذر (sudo/root)** لأنها:

- تثبت حزم النظام (Docker، Ansible، Python3، Git)
- تنشئ شبكات Docker وصلاحياتها
- تنشئ مجلدات البيانات (`/data/`) ومجلدات الإعدادات (`/opt/`)
- تدير حاويات Docker وتشغلها

---

## 10. 📁 ملفات السكريبت في المجلد

| الملف | الغرض |
|------|---------|
| `bootstrap-odoo-infra.sh` | تثبيت التبعيات وتجهيز البيئة الأساسية (Linux فقط) |
| `launch-odoo-infra.sh` | تشغيل المشروع completo (يقوم بتشغيل bootstrap تلقائياً) |
| `install-odoo17.sh` | تثبيت Odoo 17 (نسختان مستقلتان) |
| `install-odoo19.sh` | تثبيت Odoo 19 (نسختان مستقلتان) |
| `health-check.sh` | فحص صحة الخدمة والحاوية |
| `backup.sh` | أخذ نسخة احتياطية من Odoo |
| `restore.sh` | استعادة نسخة احتياطية من Odoo |
| `verify-backups.sh` | التحقق من سلامة النسخ الاحتياطية |
| `list-backups.sh` | عرض جميع النسخ الاحتياطية المتاحة |
| `backup-system-config.sh` | نسخ إعدادات نظام Ubuntu (شبكة، SSH، Docker، إلخ) |
| `restore-system-config.sh` | استعادة إعدادات نظام Ubuntu |

---

## 11. 📂 مسارات النظام بعد التثبيت

| المكون | المسار |
|-----------|------|
| ملفات المشروع | `/opt/Odoo-MultiVersion-Deployment/` |
| بيانات Odoo 17 | `/data/odoo17/instance1, /data/odoo17/instance2` |
| بيانات Odoo 19 | `/data/odoo19/instance1, /data/odoo19/instance2` |
| إعدادات Odoo 17 | `/opt/odoo17/instance1, /opt/odoo17/instance2` |
| إعدادات Odoo 19 | `/opt/odoo19/instance1, /opt/odoo19/instance2` |
| النسخ الاحتياطية | `/data/backups/odoo17, /data/backups/odoo19` |
| سجلات bootstrap | `/var/log/odoo-bootstrap.log` |

---

## 12. 📞 الدعم

لأي مشاكل أو استفسارات، يرجى فتح Issue في مستودع المشروع على GitHub.

**الإصدار:** 1.0  
**آخر تحديث:** 2026-11-04  
**النظام المستهدف:** Linux Ubuntu 20.04 / 22.04 / 24.04 LTS  
**الحالة:** Production Ready

---

*تم إعداد هذا الدليل كجزء من نظام إدارة البنية التحتية لـ Odoo (Infrastructure Manager).*
